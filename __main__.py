import os
from dotenv import load_dotenv

from pipeline import SECPipeline

# Load .env file with OpenAI API key
load_dotenv()

DB_PATH = os.getenv("DB_PATH")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# User agent to use in EDGAR requests. For format, see https://www.sec.gov/os/accessing-edgar-data
EDGAR_USER_AGENT = os.getenv("EDGAR_USER_AGENT")

if __name__ == "__main__":
    pipeline = SECPipeline(DB_PATH, OPENAI_API_KEY, EDGAR_USER_AGENT)
    pipeline.run_pipeline()
