"""
Database migration to add translation support.

Adds:
1. preferred_language column to users table
2. original_language and translations columns to messages table
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """Add translation columns to database."""
    conn = sqlite3.connect("whatsapp.db")
    cursor = conn.cursor()

    try:
        # Add preferred_language to users table
        logger.info("Adding preferred_language column to users table...")
        cursor.execute(
            """
            ALTER TABLE users 
            ADD COLUMN preferred_language VARCHAR(10) DEFAULT 'en'
        """
        )
        logger.info("✓ Added preferred_language to users")

    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            logger.info("✓ preferred_language column already exists in users")
        else:
            raise

    try:
        # Add original_language to messages table
        logger.info("Adding original_language column to messages table...")
        cursor.execute(
            """
            ALTER TABLE messages 
            ADD COLUMN original_language VARCHAR(10)
        """
        )
        logger.info("✓ Added original_language to messages")

    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            logger.info("✓ original_language column already exists in messages")
        else:
            raise

    try:
        # Add translations to messages table
        logger.info("Adding translations column to messages table...")
        cursor.execute(
            """
            ALTER TABLE messages 
            ADD COLUMN translations TEXT
        """
        )
        logger.info("✓ Added translations to messages")

    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            logger.info("✓ translations column already exists in messages")
        else:
            raise

    conn.commit()
    conn.close()

    logger.info("✅ Migration completed successfully!")


if __name__ == "__main__":
    migrate()
