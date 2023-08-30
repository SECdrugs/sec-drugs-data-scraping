from sec_edgar_api import EdgarClient
import requests
import re
import time
import glob
from bs4 import BeautifulSoup
import re
import pandas as pd
import os
import openai
from dotenv import load_dotenv
import json

# Load .env file with OpenAI API key
load_dotenv()

###
### Constants and setup code
###
CIKS = {
    "Novartis": "1114448",
    "Sanofi": "1121404",
    "AstraZeneca": "901832",
    "Eli_Lilly": "59478",
    "Mast_Therapeutics": "1160308",
    "Novo_Nordisk": "353278",
    "Regulus_Therapeutics": "1505512",
}

# Folder in which the SEC filings are downloaded
FOLDER = "sec-edgar-filings"
# Start year for filings to download from EDGAR
START_YEAR = 2012
# Model to use when searching filing snippets for mentions of drug discontinuations
MODEL = "gpt-3.5-turbo-16k"
# Types of filings to download and search
FILING_TYPES = set(["10-K", "10-Q", "20-F", "8-K", "6-K"])
# Set of keywords associated with discontinuation
pattern = re.compile(
    r"\b(discontinue(d|s)?|halt(ed|s)?|terminate(d|s)?|stop(ped|s)?|suspend(ed|s)?|cancel(ed|s)?)\b.*?\b(drug(s)?|trial(s)?|project(s)?|research|development)",
    re.IGNORECASE,
)
# User agent to use in EDGAR requests. For format, see https://www.sec.gov/os/accessing-edgar-data
EDGAR_USER_AGENT = os.getenv("EDGAR_USER_AGENT")
# Headers used for EDGAR requests
EDGAR_HEADERS = {
    "User-Agent": EDGAR_USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov",
}

### Initialize clients

# SEC EDGAR Client
edgar = EdgarClient(user_agent=EDGAR_USER_AGENT)

# Load OpenAI API key from .env file
openai.api_key = os.getenv("OPENAI_API_KEY")


###
### Code for SEC EDGAR download
###
def get_submission_url(cik, accession, doc_name):
    """Returns the url for a given CIK, accession, and filing name"""
    cik_suff = cik.lstrip("0")
    acc = accession.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{cik_suff}/{acc}/{doc_name}"
    return url


def download_filing(url, filename):
    """Save the individual filing located at `url` as `filename`"""
    response = requests.get(url, headers=EDGAR_HEADERS)
    # Save response to file
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "wb") as f:
        f.write(response.content)


def download_submissions_for_cik(cik, start_year):
    """Downloads all the submissions for a given CIK."""
    submissions = edgar.get_submissions(cik)
    filings = submissions["filings"]["recent"]
    accessions = filings["accessionNumber"]
    dates = filings["reportDate"]
    docs = filings["primaryDocument"]
    descs = filings["primaryDocDescription"]
    for i in range(len(accessions)):
        doc_type = descs[i]
        if doc_type not in FILING_TYPES or not docs[i] or len(dates[i]) < 4:
            continue
        year = int(dates[i][:4])
        if year < start_year:
            continue
        print(f"Downloading filing {i+1} of {len(accessions)}")
        url = get_submission_url(cik, accessions[i], docs[i])
        filename = f"{FOLDER}/{cik}/{doc_type}/{docs[i]}"
        download_filing(url, filename)
        # Must remain under 10 requests per second per https://www.sec.gov/privacy#security
        time.sleep(0.2)


###
### Code to find potential discontinued drugs in filings
###


def generate_prompt(text):
    prompt = (
        "The following text is extracted from a pharmaceutical company's SEC filing:\n'"
        + text
        + """
        Does it contain information on the discontinuation of a drug (and only a drug/compound, not a lab or other operation)?
        If so, return the following fields in valid json:

        {"discontinued": true,
        "drug_name(s)": [____],
        "reason_for_discontinuation": ___}
        If the text does not refer to the discontinuation of a drug, return
        {"discontinued": false}

        Reason for discontinuation may only be present if contained within the extracted text.
        """
    )
    return prompt


def get_keyword_matches_with_context(html, pattern, before=300, after=300):
    """Search filing for keywords associated with discontinued projects.
    The surrounding text is included for context for the GPT model to infer
    whether the discontinuation involves a drug. Full prompt must remain under the token limit for the chosen model.
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()
    last_end = 0
    for match in pattern.finditer(text):
        start = max(0, match.start() - before)
        end = min(match.end() + after, len(text))
        # If this context overlaps with the previous one, merge them
        # TODO Fix cases where this makes the prompt too long
        if start <= last_end:
            start = last_end
        last_end = end
        yield text[start:end]


def make_call_to_openai_api(match):
    """
    Takes in a snippet from the filing and adds it to the prompt for the GPT API.
    The function will return a JSON object with the discontinued drug name, if present.
    """
    response = openai.ChatCompletion.create(
        model=MODEL,
        messages=[{"role": "system", "content": generate_prompt(match)}],
        temperature=0.6,
    )
    openai_obj = list(response.choices)[0]
    content = openai_obj.to_dict()["message"]["content"]
    output = json.loads(content)
    return output


def find_discontinued_in_filing(company, filing_path):
    """Find potential discontinued drugs in a given filing"""
    cik = CIKS[company]
    with open(f"{filing_path}") as f, open(f"{company}.json", "a") as json_results:
        filing = f.read()
        matches_with_context = list(get_keyword_matches_with_context(filing, pattern))
        print(f"Found {len(matches_with_context)} matches in {filing_path}")
        for i, match in enumerate(matches_with_context):
            print(f"Match {i + 1} of {len(matches_with_context)}")
            try:
                openai_result = make_call_to_openai_api(match)
                if openai_result["discontinued"]:
                    openai_result["file"]: filing_path
                    json_results.write(json.dumps(openai_result))
                    json_results.write(",\n")
            except openai.error.APIError as e:
                print(f"Error: {e}. \n")

            time.sleep(5)


def run_parser_for_cik(company, cik):
    """Runs parsing code on all filings in `FOLDER` for the given CIK"""
    for filing_type_path in glob.glob(f"{FOLDER}/{cik}/*"):
        for filing_path in glob.glob(f"{filing_type_path}/*"):
            find_discontinued_in_filing(company, filing_path)


def check_discontinued():
    for company, cik in CIKS.items():
        # download_submissions_for_cik(cik, START_YEAR)
        run_parser_for_cik(company, cik)


check_discontinued()
