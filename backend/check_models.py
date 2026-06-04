import os
import httpx
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('API_KEY_GEMINI') or os.getenv('APIKEYGEMINI')

if not api_key:
    print("No API Key found")
else:
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    resp = httpx.get(url)
    if resp.status_code == 200:
        models = resp.json().get('models', [])
        for m in models:
            print(f"- {m['name']}")
    else:
        print(f"Error {resp.status_code}: {resp.text}")
