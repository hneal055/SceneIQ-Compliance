import asyncio, sys
sys.path.insert(0, ".")
from src.utils.database import prisma
from src.utils.auth_utils import hash_password

async def main():
    await prisma.connect()
    existing = await prisma.user.find_first(where={"email": "admin@pilotforge.com"})
    if not existing:
        await prisma.user.create(data={"email": "admin@pilotforge.com", "passwordHash": hash_password("pilotforge2024"), "role": "admin", "isActive": True})
        print("Admin user created")
    else:
        print("Admin user already exists")
    await prisma.disconnect()

asyncio.run(main())
