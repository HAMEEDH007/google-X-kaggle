from pydantic import BaseModel, Field
from PIL import Image
from google.genai import types
from app.config import CONTRACT_PATH, RECEIPT_PATH, get_client

from app.config import CONTRACT_PATH, RECEIPT_PATH, get_client, SIMULATION_MODE, SANDBOX_DIR
import json

class ExtractionSchema(BaseModel):
    vendor_name: str = Field(description="Name of the vendor found across documents")
    contract_tariff_rate_pct: float = Field(description="The legal tariff rate specified in the text contract as a percentage (e.g. 5.0)")
    receipt_tariff_rate_pct: float = Field(description="The tariff rate actually applied on the visual customs receipt as a percentage (e.g. 8.0)")
    expected_units: int = Field(description="The expected units per pallet container mentioned in the contract")

def extract_parameters() -> ExtractionSchema:
    """Loads contract and receipt image, and performs Gemini multimodal extraction."""
    if SIMULATION_MODE:
        config_path = SANDBOX_DIR / "sandbox_config.json"
        if config_path.exists():
            with open(config_path, "r") as f:
                cfg = json.load(f)
            return ExtractionSchema(
                vendor_name=cfg["vendor"],
                contract_tariff_rate_pct=cfg["contract_tariff"],
                receipt_tariff_rate_pct=cfg["receipt_tariff"],
                expected_units=cfg["expected_units"]
            )
        return ExtractionSchema(
            vendor_name="Apex Manufacturing Inc.",
            contract_tariff_rate_pct=5.0,
            receipt_tariff_rate_pct=8.0,
            expected_units=600
        )

    client = get_client()
    
    # Check that paths exist
    if not CONTRACT_PATH.exists() or not RECEIPT_PATH.exists():
        raise FileNotFoundError("Sandbox documents not found. Initialize sandbox first.")
        
    with open(CONTRACT_PATH, "r") as f:
        contract_text = f.read()
        
    receipt_image = Image.open(RECEIPT_PATH)
    
    extraction_prompt = """
    You are the intake pipeline for LogiMind. Analyze the provided legal text contract 
    and the digital image of the customs receipt. Extract the required parameters 
    exactly as stated in the documents. Do not assume or cross-extrapolate values.
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            extraction_prompt,
            f"CONTRACT TEXT:\n{contract_text}",
            receipt_image
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ExtractionSchema,
            temperature=0.0
        ),
    )
    
    return response.parsed
