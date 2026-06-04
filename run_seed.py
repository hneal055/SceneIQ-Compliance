import asyncio
import sys
sys.path.insert(0, '.')
from src.utils.database import prisma
from src.utils.seed import seed_all

async def main():
    await prisma.connect()
    await seed_all()
    await prisma.disconnect()
    print("Seed complete")

asyncio.run(main())
