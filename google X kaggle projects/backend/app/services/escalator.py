import pandas as pd
from google.genai import types
from app.config import LEDGER_PATH, EMAIL_PATH, get_client, SIMULATION_MODE

def escalate_and_draft(
    vendor: str,
    invoice_amount: float,
    contract_tariff: float,
    receipt_tariff: float,
    overcharge: float,
    tariff_diff: float
) -> dict:
    """Updates the ERP CSV ledger database and drafts a formal vendor dispute email

    using Gemini 2.5 Flash.
    """
    # 1. Update the database ledger CSV
    ledger_updated = False
    if LEDGER_PATH.exists():
        df = pd.read_csv(LEDGER_PATH)
        if len(df) > 0:
            if tariff_diff > 0:
                df.at[0, "Audit_Status"] = "HOLD - PAYMENT DISPUTED"
                df.at[0, "Flagged_Issues"] = f"{tariff_diff:.1f}% Tariff Overcharge Detected (${overcharge:,.2f})"
            else:
                df.at[0, "Audit_Status"] = "PASSED"
                df.at[0, "Flagged_Issues"] = "Compliance Passed"
            df.to_csv(LEDGER_PATH, index=False)
            ledger_updated = True
    
    # 2. Call Gemini or simulate to generate the dispute email if there is an overcharge
    if tariff_diff > 0:
        if SIMULATION_MODE:
            email_text = f"""Subject: Billing Discrepancy Notification - Invoice TXN-2026-001

Dear {vendor} Billing Department,

This notice serves to alert you that our compliance audit systems have identified a core pricing mismatch on transaction TXN-2026-001 (Audited Value: ${invoice_amount:,.2f}).

Pursuant to Section 4.2 of our agreement, the tariff rate is capped at flat {contract_tariff:.1f}%. However, the visual processing customs document shows an assessment of {receipt_tariff:.1f}%.

Verification math completed in our sandbox environment:
- Contract Tariff: ${invoice_amount * (contract_tariff / 100.0):,.2f}
- Charged Tariff: ${invoice_amount * (receipt_tariff / 100.0):,.2f}
- Overcharge Total: ${overcharge:,.2f}

As a result, transaction payment is currently flagged on HOLD. Please issue a corrected invoice to restore processing status.

Regards,
LogiMind Operations Global"""
        else:
            email_generation_prompt = f"""
You are the automated supplier communication interface for LogiMind.
Write a formal, highly professional email addressed to {vendor} regarding a billing dispute.

Use these specific details discovered during the audit:
- Transaction ID: TXN-2026-001
- Invoice total audited: ${invoice_amount:,.2f}
- Violation discovered: Applied tariff on customs receipt is {receipt_tariff:.1f}%, but Section 4.2 of the signed Vendor Contract strictly mandates a {contract_tariff:.1f}% flat fee.
- Math verified: This {tariff_diff:.1f}% discrepancy has resulted in an overcharge of exactly ${overcharge:,.2f}.
- Current Status: Payment is on hold until a corrected invoice is issued.

Ensure the tone is firm, professional, and clearly cites the contract clause breach to encourage rapid resolution.
"""
        
            client = get_client()
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=email_generation_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2
                )
            )
            email_text = response.text
    else:
        email_text = "No compliance issue found. No dispute email required."

    # Write email draft to file
    with open(EMAIL_PATH, "w") as f:
        f.write(email_text.strip())

    # Read the updated ledger back as a dictionary
    ledger_state = {}
    if LEDGER_PATH.exists():
        df = pd.read_csv(LEDGER_PATH)
        ledger_state = df.iloc[0].to_dict()

    return {
        "ledger_updated": ledger_updated,
        "ledger_state": ledger_state,
        "email_text": email_text
    }
