import sqlite3


class FilingMetadataDB:
    def __init__(self, DB_PATH="filings_metadata.db"):
        self.conn = sqlite3.connect(DB_PATH)
        self._create_table()

    def _create_table(self):
        """Initialize the database table if it doesn't exist."""
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS filings (
                    id INTEGER PRIMARY KEY,
                    company TEXT,
                    cik TEXT,
                    filing_type TEXT,
                    report_date TEXT,
                    filename TEXT,
                    status TEXT DEFAULT 'not_checked',
                    analyzed BOOLEAN DEFAULT 0, 
                    discontinued BOOLEAN DEFAULT 0,
                    drug_names TEXT,
                    reason_for_discontinuation TEXT
                )
                """
            )

    def insert_filing_metadata(self, company, cik, filing_type, report_date, filename):
        """Insert filing metadata into the database."""
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO filings (company, cik, filing_type, report_date, filename) 
                VALUES (?, ?, ?, ?, ?)
                """,
                (company, cik, filing_type, report_date, filename),
            )

    def update_filing_status(self, filename, status):
        """Update the status of a specific filing."""
        with self.conn:
            self.conn.execute(
                "UPDATE filings SET status = ? WHERE filename = ?", (status, filename)
            )

    def update_filing_analysis(
        self, filename, analyzed, discontinued, drug_names, reason_for_discontinuation
    ):
        """Update the analysis results for a specific filing."""
        with self.conn:
            self.conn.execute(
                """
                UPDATE filings 
                SET analyzed = ?, discontinued = ?, drug_names = ?, reason_for_discontinuation = ? 
                WHERE filename = ?
                """,
                (
                    analyzed,
                    discontinued,
                    ",".join(drug_names) if drug_names else None,
                    reason_for_discontinuation,
                    filename,
                ),
            )

    def update_filing_analysis_no_findings(self, filename):
        """Mark a filing as analyzed but with no findings."""
        with self.conn:
            self.conn.execute(
                """
                UPDATE filings 
                SET analyzed = 1, discontinued = 0
                WHERE filename = ?
                """,
                (filename,),
            )

    def get_unprocessed_filings(self):
        """Retrieve a list of unprocessed filings."""
        with self.conn:
            cursor = self.conn.execute(
                "SELECT filename FROM filings WHERE status = 'not_checked'"
            )
            return [res[0] for res in cursor.fetchall()]

    def is_filing_downloaded(self, filename):
        """Check if a filing exists in the database given its filename."""
        with self.conn:
            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM filings WHERE filename = ?", (filename,)
            )
            return cursor.fetchone()[0] > 0

    ###
    ### Shutdown
    ###

    def close_connection(self):
        """Close the database connection."""
        self.conn.close()

    def __del__(self):
        self.close_connection()
