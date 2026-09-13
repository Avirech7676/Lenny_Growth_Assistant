"""Executable script to initialize database tables and extensions."""

import sys
import os

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.db.session import init_db, ping_db
from app.core.logging import setup_logger

logger = setup_logger("init_db")

def main():
    logger.info("Running database initialization...")
    init_db()
    if ping_db():
        logger.info("Database ping check: SUCCESS")
    else:
        logger.error("Database ping check: FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
