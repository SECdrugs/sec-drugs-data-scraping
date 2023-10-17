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
                    filing_analyzed BOOLEAN DEFAULT 0
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
                    name TEXT NOT NULL,
                    filing_id INTEGER,
                    compound_analyzed BOOLEAN DEFAULT 0,
                    reason_for_discontinuation TEXT DEFAULT NONE,
                    FOREIGN KEY (filing_id) REFERENCES filings(id)
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
                "SELECT id, filename FROM filings WHERE filing_analyzed = 0"
            )
            return [(res[0], res[1]) for res in cursor.fetchall()]

    def is_filing_downloaded(self, filename):
        """Check if a filing exists in the database given its filename."""
        with self.conn:
            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM filings WHERE filename = ?", (filename,)
            )
            return cursor.fetchone()[0] > 0

    def set_filing_analyzed(self, id):
        """Mark a filing as analyzed but with no findings."""
        with self.conn:
            self.conn.execute(
                """
                UPDATE filings
                SET filing_analyzed = 1
                WHERE id = ?
                """,
                (id,),
            )

    ###
    # Compounds
    ###

    def does_compound_exist(self, compound_name):
        """Check if a compound with a given name exists in the database."""
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

    def insert_compound(self, compound_name, filing_id, reason_for_discontinuation=None):
        """Insert compound data into the database."""
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO compound_names (name, filing_id, reason_for_discontinuation) 
                VALUES (?, ?, ?)
                """,
                (compound_name, filing_id, reason_for_discontinuation),
            )

    def set_compound_analyzed(self, id):
        """Sets the compound_analyzed field to True for a given filing."""
        with self.conn:
            self.conn.execute(
                """
                UPDATE compound_names
                SET compound_analyzed = 1
                WHERE id = ?
                """,
                (id,),
            )

    def get_unanalyzed_compound_names(self):
        """Retrieve a list of filenames and their associated compound names from filings
        where compound_analyzed is False."""
        with self.conn:
            cursor = self.conn.execute(
                """
                SELECT id, name 
                FROM compound_names 
                WHERE compound_analyzed = 0
                """
            )
            return [(res[0], res[1]) for res in cursor.fetchall()]

    ###
    # Shutdown
    ###

    def close_connection(self):
        """Close the database connection."""
        self.conn.close()

    def __del__(self):
        self.close_connection()
