#!/usr/bin/env python3
"""
Database initialization script for sntry.ai
"""

import asyncio
from prisma import Prisma
from shared.config import get_settings
from shared.auth import get_password_hash

settings = get_settings()


async def init_database():
    """Initialize database with default data"""
    db = Prisma()
    await db.connect()
    
    try:
        print("Initializing database...")
        
        # Create default admin user
        admin_user = await db.user.find_unique(where={"email": "admin@sntry.ai"})
        if not admin_user:
            await db.user.create(
                data={
                    "email": "admin@sntry.ai",
                    "username": "admin",
                    "hashedPassword": get_password_hash("admin123"),
                    "isActive": True,
                    "isAdmin": True,
                    "metadata": {"created_by": "init_script"}
                }
            )
            print("✓ Created admin user (admin@sntry.ai / admin123)")
        else:
            print("✓ Admin user already exists")
        
        # Create system configuration entries
        config_entries = [
            {"key": "api_version", "value": {"version": "1.0.0"}},
            {"key": "max_agents_per_user", "value": {"limit": 100}},
            {"key": "default_model", "value": {"model_id": "gemini-pro"}},
        ]
        
        for entry in config_entries:
            existing = await db.systemconfig.find_unique(where={"key": entry["key"]})
            if not existing:
                await db.systemconfig.create(data=entry)
                print(f"✓ Created system config: {entry['key']}")
        
        print("Database initialization completed successfully!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(init_database())