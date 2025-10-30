"""
Initialize database - Create all tables
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import init_db
from config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Initialize database"""
    logger.info(f"Initializing database at: {settings.database_url}")
    
    try:
        init_db()
        logger.info("✅ Database initialized successfully!")
        logger.info("All tables created.")
    
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
