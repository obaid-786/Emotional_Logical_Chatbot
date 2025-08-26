from dotenv import load_dotenv
from langchain_groq import ChatGroq
import os
import sys


def verify_groq_api_key():
    load_dotenv()

    groq_api_key = os.getenv("GROQ_API_KEY")

    if not groq_api_key:
        print("❌ GROQ_API_KEY not found in .env file")
        return False

    print(f"✅ Found GROQ_API_KEY: {groq_api_key[:10]}...")

    try:
        # Test with a simple request
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0.1,
            groq_api_key=groq_api_key
        )

        response = llm.invoke("Hello")
        print("✅ API key is valid and working!")
        print(f"✅ Model response: {response.content[:50]}...")
        return True

    except Exception as e:
        print(f"❌ API key verification failed: {e}")
        return False


if __name__ == "__main__":
    verify_groq_api_key()