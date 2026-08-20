import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load API key from .env
load_dotenv()

# Configure Gemini
genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

print("\nAVAILABLE MODELS:\n")

try:
    for model in genai.list_models():
        print(model.name)

except Exception as e:
    print("ERROR:")
    print(e)