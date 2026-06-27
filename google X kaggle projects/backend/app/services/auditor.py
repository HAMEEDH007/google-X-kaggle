from google.genai import types
from app.config import get_client, SIMULATION_MODE

def audit_discrepancy(
    txn_id: str,
    invoice_amount: float,
    contract_tariff: float,
    receipt_tariff: float
) -> dict:
    """Invokes Gemini 2.5 Flash with the Python Code Execution tool enabled

    to calculate the financial leakage and return detailed logs.
    """
    diff = receipt_tariff - contract_tariff
    overcharge = invoice_amount * (diff / 100.0) if diff > 0 else 0.0

    if SIMULATION_MODE:
        code_logs = [
            {
                "type": "code",
                "content": f"invoice_amount = {invoice_amount}\ncontract_tariff = {contract_tariff}\nreceipt_tariff = {receipt_tariff}\ndiff = receipt_tariff - contract_tariff\novercharge = invoice_amount * (diff / 100.0)\nprint(f'Calculated Overcharge: {{overcharge}}')"
            },
            {
                "type": "output",
                "content": f"Calculated Overcharge: {overcharge:.2f}\n"
            }
        ]
        
        report = f"""=== LogiMind Compliance Audit Report ===
Transaction Reference: {txn_id}
Vendor: (Under Verification)
Invoice Total: ${invoice_amount:,.2f}

ANALYSIS AND FINDINGS:
1. Applied Custom tariff rate on receipt: {receipt_tariff:.1f}%
2. Agreed Legal contract rate locked: {contract_tariff:.1f}%
3. Detected Rate Discrepancy: {diff:.1f}% (Overcharge margin)

VERIFICATION STEPS:
To ensure math compliance, Python tool execution was activated in the sandbox:
- Calculated Overcharge = ${invoice_amount:,.2f} * ({receipt_tariff:.1f} - {contract_tariff:.1f}) / 100
- Overcharge total calculated: ${overcharge:,.2f}

EXECUTIVE DISPOSITION:
Payment holds MUST be registered for Transaction {txn_id}. Billing discrepancy exceeds tolerance thresholds. Dispute email escalation triggered.
"""
        return {
            "report": report,
            "code_logs": code_logs,
            "calculated_overcharge": overcharge,
            "tariff_diff": diff
        }

    client = get_client()
    
    verification_prompt = f"""
You are the auditing brain of LogiMind. 
We have detected a discrepancy for transaction {txn_id} containing an invoice total of ${invoice_amount:,.2f}.
- The contract specifies a tariff rate of {contract_tariff}%.
- The physical customs receipt charged a rate of {receipt_tariff}%.

You MUST calculate the exact financial leakage (overcharge) in USD.
To avoid math hallucinations, you must use the Python Code Execution tool provided to you.
Write a script to perform the following calculation:
Overcharge = Invoice_Amount * ((Receipt_Tariff_Pct - Contract_Tariff_Pct) / 100)

Run the script, capture the output, and present:
1. The exact overcharge calculation steps.
2. A brief analysis of how this happened.
3. Your executive decision on whether this requires holding payment.
"""

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=verification_prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(code_execution=types.ToolCodeExecution())],
            temperature=0.0
        )
    )
    
    # Extract code execution steps and outputs if present
    code_logs = []
    try:
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'executable_code') and part.executable_code:
                    code_logs.append({
                        "type": "code",
                        "content": part.executable_code.code
                    })
                if hasattr(part, 'code_execution_result') and part.code_execution_result:
                    code_logs.append({
                        "type": "output",
                        "content": part.code_execution_result.output
                    })
    except Exception as e:
        code_logs.append({
            "type": "error",
            "content": f"Failed to parse code execution details: {str(e)}"
        })

    # Calculate fallback values in python to return along
    diff = receipt_tariff - contract_tariff
    overcharge = invoice_amount * (diff / 100.0) if diff > 0 else 0.0

    return {
        "report": response.text,
        "code_logs": code_logs,
        "calculated_overcharge": overcharge,
        "tariff_diff": diff
    }
