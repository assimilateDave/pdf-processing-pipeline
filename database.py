import sqlite3
import os

DB_NAME = "documents.db"

def init_db():
    create_table = not os.path.exists(DB_NAME)
    conn = sqlite3.connect(DB_NAME)
    if create_table:
        with conn:
            conn.execute(
                """
                CREATE TABLE documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name TEXT NOT NULL,
                    document_type TEXT,
                    extracted_text TEXT,
                    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
    return conn

def insert_document(file_name, document_type, extracted_text):
    conn = sqlite3.connect(DB_NAME)
    with conn:
        conn.execute(
            "INSERT INTO documents (file_name, document_type, extracted_text) VALUES (?, ?, ?)",
            (file_name, document_type, extracted_text)
        )