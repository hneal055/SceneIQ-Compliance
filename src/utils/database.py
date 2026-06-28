"""
Database connection module for SceneIQ
"""
from prisma import Prisma

# Create global prisma client instance
prisma = Prisma()


async def connect_db():
    """Connect to database"""
    await prisma.connect()


async def disconnect_db():
    """Disconnect from database"""
    await prisma.disconnect()




