"""
Create database tables. Run once: python init_db.py
"""
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.database import init_tables

if __name__ == "__main__":
    init_tables()
    print("OK: Tables created.")
