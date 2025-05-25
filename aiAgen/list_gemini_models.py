import os
from dotenv import load_dotenv

load_dotenv()
print(f"Google API Key loaded: {os.getenv('GOOGLE_API_KEY') is not None}")
# (디버깅 목적으로만 사용하고, 실제 서비스에서는 사용하지 마세요)
print(f"Google API Key value: {os.getenv('GOOGLE_API_KEY')}")
