import os
from dotenv import load_dotenv

def get_GPT_token():
    """

    """

    load_dotenv()
    return os.getenv("OPENAI_API_KEY")