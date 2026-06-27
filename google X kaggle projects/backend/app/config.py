import os
from pathlib import Path
from google import genai

# Setup base paths
APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
SANDBOX_DIR = BACKEND_DIR / "logimind_sandbox"
DOCS_DIR = SANDBOX_DIR / "documents"
DB_DIR = SANDBOX_DIR / "database"

# Ensure directories exist
os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)

# File paths
CONTRACT_PATH = DOCS_DIR / "vendor_contract.txt"
RECEIPT_PATH = DOCS_DIR / "customs_receipt.png"
LEDGER_PATH = DB_DIR / "erp_ledger.csv"
EMAIL_PATH = DOCS_DIR / "dispute_email_draft.txt"

# Check if key is available in environment
SIMULATION_MODE = False
try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env")
except ImportError:
    pass

# Try fetching Kaggle Secret key if in Kaggle Environment
if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
    try:
        from kaggle_secrets import UserSecretsClient
        kaggle_key = UserSecretsClient().get_secret("GEMINI_API_KEY")
        if kaggle_key:
            os.environ["GEMINI_API_KEY"] = kaggle_key
            os.environ["GOOGLE_API_KEY"] = kaggle_key
    except Exception:
        pass

if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
    SIMULATION_MODE = True
    print("⚠️ WARNING: GEMINI_API_KEY not found in environment. Running in SIMULATION_MODE with mock API responses.")

def get_client() -> genai.Client:
    """Instantiate and return the Gemini API Client.
    Looks for the GEMINI_API_KEY environment variable.
    """
    if SIMULATION_MODE:
        # Return a dummy client or raise error if called directly
        return None
    # Instantiate client; it automatically uses GEMINI_API_KEY env var.
    return genai.Client()

