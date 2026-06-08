import os

from dotenv import load_dotenv
load_dotenv()


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
OPEN_AI_MODEL = os.getenv("OPEN_AI_MODEL", "gpt")




