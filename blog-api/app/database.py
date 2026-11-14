import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from .config import MONGODB_URI, DB_NAME

client = AsyncIOMotorClient(MONGODB_URI, tlsCAFile=certifi.where())
db = client[DB_NAME]

users = db["users"]
blogs = db["blogs"]
categories = db["categories"]


async def init_db():
    """Create indexes and seed a few default categories."""
    await users.create_index("email", unique=True)
    await blogs.create_index("slug", unique=True)
    await blogs.create_index("tags")
    await blogs.create_index("category")
    await blogs.create_index([("title", "text")])
    await categories.create_index("name", unique=True)

    if await categories.count_documents({}) == 0:
        from .utils import now
        await categories.insert_many(
            [
                {"name": n, "description": d, "created_at": now()}
                for n, d in [
                    ("Technology", "Software, gadgets and the web"),
                    ("Lifestyle", "Everyday life, habits and wellbeing"),
                    ("Travel", "Places, routes and stories from the road"),
                ]
            ]
        )
