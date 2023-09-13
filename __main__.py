import os
from dotenv import load_dotenv
import argparse

from pipeline import SECPipeline

# Load .env file with OpenAI API key
load_dotenv()

DB_PATH = os.getenv("DB_PATH")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# User agent to use in EDGAR requests. For format, see https://www.sec.gov/os/accessing-edgar-data
EDGAR_USER_AGENT = os.getenv("EDGAR_USER_AGENT")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-D", "--download_filings", help="Download SEC filings", action="store_true"
    )
    args = parser.parse_args()
    download_filings = args.download_filings == True
    pipeline = SECPipeline(DB_PATH, OPENAI_API_KEY, EDGAR_USER_AGENT, download_filings)
    pipeline.run_pipeline()
