#!/usr/bin/env python3
"""
Database migration script for sntry.ai
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.database import run_migrations, seed_database, connect_database, disconnect_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Main migration function"""
    try:
        logger.info("Starting database migration...")
        
        # Connect to database
        await connect_database()
        
        # Run migrations
        migration_success = await run_migrations()
        if not migration_success:
            logger.error("Migration failed")
            return False
        
        # Seed database
        seed_success = await seed_database()
        if not seed_success:
            logger.error("Database seeding failed")
            return False
        
        logger.info("Database migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Migration error: {e}")
        return False
    
    finally:
        await disconnect_database()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)