import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pandas as pd

from app.config import CONTRACT_PATH, RECEIPT_PATH, LEDGER_PATH, EMAIL_PATH
from app.utils import init_sandbox
from app.services.extractor import extract_parameters
from app.services.auditor import audit_discrepancy
from app.services.escalator import escalate_and_draft

app = FastAPI(title="LogiMind Agentic Audit API", version="1.0.0")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SandboxParams(BaseModel):
    vendor: str = "Apex Manufacturing Inc."
    invoice_amount: float = 12000.0
    contract_tariff: float = 5.0
    receipt_tariff: float = 8.0
    expected_units: int = 600

def clean_numpy_types(data: dict) -> dict:
    """Helper to convert numpy types and NaNs to standard JSON-compliant Python types."""
    cleaned = {}
    for k, v in data.items():
        if pd.isna(v):
            cleaned[k] = None
        elif hasattr(v, 'item'):
            cleaned[k] = v.item()
        else:
            cleaned[k] = v
    return cleaned

@app.get("/api/state")
def get_state():
    """Returns the current state of sandbox files and parameters."""
    ledger_state = {}
    if LEDGER_PATH.exists():
        try:
            df = pd.read_csv(LEDGER_PATH)
            if not df.empty:
                ledger_state = clean_numpy_types(df.iloc[0].to_dict())
        except Exception as e:
            ledger_state = {"error": f"Failed to read ledger: {str(e)}"}
            
    contract_text = ""
    if CONTRACT_PATH.exists():
        with open(CONTRACT_PATH, "r") as f:
            contract_text = f.read()

    email_text = ""
    if EMAIL_PATH.exists():
        with open(EMAIL_PATH, "r") as f:
            email_text = f.read()
            
    return {
        "files_initialized": CONTRACT_PATH.exists() and RECEIPT_PATH.exists() and LEDGER_PATH.exists(),
        "ledger": ledger_state,
        "contract": contract_text,
        "email_draft": email_text
    }

@app.post("/api/initialize")
def initialize_sandbox(params: SandboxParams):
    """Initializes the mock sandbox environment with custom values."""
    try:
        init_sandbox(
            vendor=params.vendor,
            invoice_amount=params.invoice_amount,
            contract_tariff=params.contract_tariff,
            receipt_tariff=params.receipt_tariff,
            expected_units=params.expected_units
        )
        return {"status": "success", "message": "Sandbox environment successfully initialized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize sandbox: {str(e)}")

@app.post("/api/run-audit")
def run_audit():
    """Runs the 4-phase compliance audit pipeline."""
    try:
        # Phase 1: Multimodal OCR Parse
        extracted = extract_parameters()
        
        # Load invoice amount and other state variables from ledger
        if not LEDGER_PATH.exists():
            raise HTTPException(status_code=400, detail="Sandbox ledger not initialized. Run initialization first.")
        df = pd.read_csv(LEDGER_PATH)
        invoice_amount = float(df.loc[0, "Invoice_Amount_USD"])
        txn_id = df.loc[0, "Transaction_ID"]
        
        # Phase 2: Discrepancy Planning
        tariff_diff = extracted.receipt_tariff_rate_pct - extracted.contract_tariff_rate_pct
        discrepancy_detected = tariff_diff > 0
        
        # Phase 3: Python Tool Execution
        audit_results = audit_discrepancy(
            txn_id=txn_id,
            invoice_amount=invoice_amount,
            contract_tariff=extracted.contract_tariff_rate_pct,
            receipt_tariff=extracted.receipt_tariff_rate_pct
        )
        
        # Phase 4: Database Update & Escalation
        escalation_results = escalate_and_draft(
            vendor=extracted.vendor_name,
            invoice_amount=invoice_amount,
            contract_tariff=extracted.contract_tariff_rate_pct,
            receipt_tariff=extracted.receipt_tariff_rate_pct,
            overcharge=audit_results["calculated_overcharge"],
            tariff_diff=audit_results["tariff_diff"]
        )
        
        return {
            "status": "success",
            "extracted_data": extracted,
            "discrepancy_detected": discrepancy_detected,
            "audit_report": audit_results["report"],
            "code_logs": audit_results["code_logs"],
            "ledger": clean_numpy_types(escalation_results["ledger_state"]),
            "email_draft": escalation_results["email_text"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit execution failed: {str(e)}")

@app.get("/api/files/receipt")
def get_receipt_image():
    """Serves the generated customs receipt image."""
    if not RECEIPT_PATH.exists():
        raise HTTPException(status_code=404, detail="Customs receipt image not found.")
    return FileResponse(RECEIPT_PATH, media_type="image/png")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
