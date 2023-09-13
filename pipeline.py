from data.filing_db import FilingMetadataDB
from analysis.sec_parsing import FilingAnalyzer
from download.edgar_api import EdgarAPI

COMPANY_CIKS = [
    ("Novartis", "1114448"),
    ("Sanofi", "1121404"),
    ("AstraZeneca", "901832"),
    ("Eli Lilly", "59478"),
    ("Mast Therapeutics", "1160308"),
    ("Novo Nordisk", "353278"),
    ("Regulus Therapeutics", "1505512"),
]


class SECPipeline:
    def __init__(self, db_path, openai_api_key, edgar_user_agent, download=True):
        # Initialize DB
        self.filing_db = FilingMetadataDB(db_path)
        # Initialize clients
        self.analyzer = FilingAnalyzer(self.filing_db, openai_api_key)
        if download:
            self.edgar = EdgarAPI(self.filing_db, edgar_user_agent)
        else:
            self.edgar = None

    def download_filings(self):
        if not self.edgar:
            print(
                "No SEC EDGAR client. Use --download or -D to enable EDGAR filing download."
            )
            exit(1)
        for company, cik in COMPANY_CIKS:
            self.edgar.download_submissions_for_company(company, cik)

    def find_potential_discontinuations(self):
        self.analyzer.find_potential_drug_names_in_unprocessed_filings()

    def run_pipeline(self):
        if self.edgar:
            self.download_filings()
        self.find_potential_discontinuations()
