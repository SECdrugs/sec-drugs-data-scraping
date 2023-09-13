import sqlite3
import datetime


class FilingMetadataDB:
    def __init__(self, DB_PATH="filings_metadata.db"):
        self.conn = sqlite3.connect(DB_PATH)
        self._create_filings_table()
        self._create_compounds_table()

    def _create_filings_table(self):
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
                    filing_analyzed BOOLEAN DEFAULT 0, 
                    discontinued BOOLEAN DEFAULT 0,
                    compound_analyzed BOOLEAN DEFAULT 0,
                    drug_names TEXT,
                    reason_for_discontinuation TEXT
                )
                """
            )

    def _create_compounds_table(self):
        """Initialize the compounds table if it doesn't exist."""
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS compound_names (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    analyzed_date TEXT
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

    def get_unprocessed_filings(self):
        """Retrieve a list of unprocessed filings."""
        with self.conn:
            cursor = self.conn.execute(
                "SELECT filename FROM filings WHERE filing_analyzed = 0"
            )
            return [res[0] for res in cursor.fetchall()]

    def is_filing_downloaded(self, filename):
        """Check if a filing exists in the database given its filename."""
        with self.conn:
            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM filings WHERE filename = ?", (filename,)
            )
            return cursor.fetchone()[0] > 0

    def update_filing_analysis(
        self, filename, discontinued, drug_names, reason_for_discontinuation
    ):
        """Update the analysis results for a specific filing."""
        with self.conn:
            self.conn.execute(
                """
                UPDATE filings
                SET filing_analyzed = 1, discontinued = ?, drug_names = ?, reason_for_discontinuation = ?
                WHERE filename = ?
                """,
                (
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
                SET filing_analyzed = 1, discontinued = 0
                WHERE filename = ?
                """,
                (filename,),
            )

    def set_compound_analyzed(self, filename):
        """Sets the compound_analyzed field to True for a given filing."""
        with self.conn:
            self.conn.execute(
                """
                UPDATE filings 
                SET compound_analyzed = 1
                WHERE filename = ?
                """,
                (filename,),
            )

    def get_unanalyzed_compound_names(self):
        """Retrieve a list of filenames and their associated compound names from filings
        where compound_analyzed is False."""
        with self.conn:
            cursor = self.conn.execute(
                """
                SELECT filename, drug_names 
                FROM filings 
                WHERE compound_analyzed = 0 AND drug_names IS NOT NULL
                """
            )
            # Return as a list of tuples where each tuple is (filename, [list of drug names])
            return [(res[0], res[1].split(",")) for res in cursor.fetchall() if res[1]]

    def mark_compound_name_as_analyzed(self, compound_name):
        """Inserts a compound name and its analyzed date into the compounds table."""
        # Use current date if no date is provided
        analyzed_date = datetime.now().strftime("%Y-%m-%d")
        with self.conn:
            self.conn.execute(
                """
                INSERT OR IGNORE INTO compound_names (name, analyzed_date) 
                VALUES (?, ?)
                """,
                (compound_name, analyzed_date),
            )

    def is_compound_name_analyzed(self, compound_name):
        """Check if a compound name exists in the compounds table (case insensitive)."""
        with self.conn:
            cursor = self.conn.execute(
                """
                SELECT COUNT(*) 
                FROM compound_names
                WHERE LOWER(name) = LOWER(?)
                """,
                (compound_name,),
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
