import os
from pathlib import Path
from google.oauth2 import service_account

def get_gcp_credentials():
    """Tập trung logic lấy credentials vào một chỗ duy nhất."""
    # Ưu tiên biến môi trường do Docker Compose cung cấp
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/app/credentials.json")
    
    if not os.path.exists(credentials_path):
        # Fallback to local path relative to this file
        credentials_path = Path(__file__).parent / "credentials.json"
    
    if os.path.exists(credentials_path):
        try:
            return service_account.Credentials.from_service_account_file(str(credentials_path))
        except Exception as e:
            print(f"[AI Utils] Error loading credentials: {e}")
    return None
