from sec_edgar_api import EdgarClient
import requests
import os
import time

# Types of filings to download and search
FILING_TYPES = set(["10-K", "10-Q", "20-F", "8-K", "6-K"])
# Start year for filings to download from EDGAR
START_YEAR = 2012


class EdgarAPI:
    def __init__(
        self, db_instance, user_agent, folder="sec-edgar-filings", start_year=START_YEAR
    ):
        self._edgar_client = EdgarClient(user_agent=user_agent)
        self._db = db_instance
        self._folder = folder
        self._headers = {
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov",
        }
        self.start_year = start_year

    def _get_submission_url(self, cik, accession, doc_name):
        """Returns the url for a given CIK, accession, and filing name"""
        cik_suff = cik.lstrip("0")
        acc = accession.replace("-", "")
        url = f"https://www.sec.gov/Archives/edgar/data/{cik_suff}/{acc}/{doc_name}"
        return url

    def _download_filing(self, url, filename):
        """Save the individual filing located at `url` as `filename`"""
        response = requests.get(url, self._headers)
        # Save response to file
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "wb") as f:
            f.write(response.content)

    def download_submissions_for_company(self, company, cik):
        """Downloads all the submissions for a given CIK."""
        submissions = self._edgar_client.get_submissions(cik)
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
            if year < self.start_year:
                continue
            url = self._get_submission_url(cik, accessions[i], docs[i])
            filename = f"{self._folder}/{cik}/{doc_type}/{docs[i]}"
            # Check if file exists already
            if self._db.is_filing_downloaded(filename):
                print(f"Found filing {i+1} of {len(accessions)} in database")
            elif os.path.isfile(filename):
                print(f"Found filing {i+1} of {len(accessions)} on disk")
                self._db.insert_filing_metadata(
                    company, cik, doc_type, dates[i], filename
                )
            else:
                print(f"Downloading filing {i+1} of {len(accessions)}")
                self._download_filing(url, filename)
                # Insert metadata into the SQLite database
                self._db.insert_filing_metadata(
                    company, cik, doc_type, dates[i], filename
                )
            # Must remain under 10 requests per second per https://www.sec.gov/privacy#security
            time.sleep(0.2)
