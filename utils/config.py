import os
from dotenv import load_dotenv

def get_GPT_token():
    """
    Here we will load the APIKEY since the .env file
    """

    load_dotenv()
    return os.getenv("")
