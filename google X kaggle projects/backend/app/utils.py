import os
import pandas as pd
from PIL import Image, ImageDraw
from app.config import CONTRACT_PATH, RECEIPT_PATH, LEDGER_PATH

def init_sandbox(
    vendor: str = "Apex Manufacturing Inc.",
    invoice_amount: float = 12000.0,
    contract_tariff: float = 5.0,
    receipt_tariff: float = 8.0,
    expected_units: int = 600
):
    """Generates the mock sandbox documents and ERP ledger with user variables."""
    
    # 1. Create the Vendor Contract Text
    contract_content = f"""GLOBAL PROCUREMENT & SUPPLY AGREEMENT
Vendor: {vendor}
Buyer: LogiMind Operations Global

SECTION 4: PRICING & LOGISTICS COMPLIANCE
4.1 The standard order volume for SKU-99X is strictly {expected_units} units per shipping pallet container.
4.2 The agreed tariff rate application for customs processing is locked at a flat {contract_tariff:.1f}% fee.
4.3 Any discrepancies between shipping bills, customs documents, and visual warehouse verification 
    must hold payments immediately and trigger an automated audit dispute log.
"""
    
    with open(CONTRACT_PATH, "w") as f:
        f.write(contract_content.strip())
        
    # 2. Create the Visual Customs Receipt Image
    img = Image.new('RGB', (600, 250), color = (255, 255, 255))
    d = ImageDraw.Draw(img)
    
    # Draw simple design borders for a polished mock document look
    d.rectangle([(10, 10), (590, 240)], outline=(148, 163, 184), width=2)
    d.rectangle([(15, 15), (585, 235)], outline=(226, 232, 240), width=1)
    
    # Render receipt texts
    d.text((30, 30), "OFFICIAL CUSTOMS RECEIPT & DUTY CLEARANCE", fill=(15, 23, 42))
    d.line([(30, 48), (570, 48)], fill=(203, 213, 225), width=1)
    
    d.text((30, 65), f"Vendor Reference: {vendor}", fill=(71, 85, 105))
    d.text((30, 95), "Item: SKU-99X Industrial Components", fill=(71, 85, 105))
    d.text((30, 125), f"Declared Quantity: {expected_units} Units", fill=(71, 85, 105))
    
    # The anomaly tariff text
    d.text((30, 155), f"Applied Tariff Rate Assessment: {receipt_tariff:.1f}%", fill=(220, 38, 38) if contract_tariff != receipt_tariff else (22, 163, 74))
    
    d.text((30, 195), "Status: STAMPED & PROCESSED", fill=(220, 38, 38))
    img.save(RECEIPT_PATH)
    
    # 3. Create the ERP Ledger
    ledger_data = {
        "Transaction_ID": ["TXN-2026-001"],
        "Vendor": [vendor],
        "Expected_Units": [expected_units],
        "Invoice_Amount_USD": [invoice_amount],
        "Audit_Status": ["Pending Verification"],
        "Flagged_Issues": ["None"]
    }
    df = pd.DataFrame(ledger_data)
    df.to_csv(LEDGER_PATH, index=False)

    # 4. Save parameters to json for simulation mode fallback
    import json
    from app.config import SANDBOX_DIR
    config_path = SANDBOX_DIR / "sandbox_config.json"
    with open(config_path, "w") as f:
        json.dump({
            "vendor": vendor,
            "invoice_amount": invoice_amount,
            "contract_tariff": contract_tariff,
            "receipt_tariff": receipt_tariff,
            "expected_units": expected_units
        }, f)

