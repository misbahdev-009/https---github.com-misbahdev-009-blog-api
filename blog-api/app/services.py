"""Shared business logic used by both the JSON API and the admin panel."""
import re
from fastapi import HTTPException

from .database import users, blogs, categories
from .security import hash_password
from .utils import now, slugify, serialize, clean_tags


# ---------- Users ----------
async def create_user(name: str, email: str, password: str):
    email = email.lower().strip()
    if await users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email is already registered")
    # The very first account becomes the admin so you can log in to the panel.
    role = "admin" if await users.count_documents({}) == 0 else "user"
    doc = {
        "name": name.strip(),
        "email": email,
        "password": hash_password(password),
        "role": role,
        "created_at": now(),
    }
    res = await users.insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


# ---------- Categories ----------
def _ci(value: str):
    return {"$regex": f"^{re.escape(value.strip())}$", "$options": "i"}


async def resolve_category(name):
    if not name:
        return None
    cat = await categories.find_one({"name": _ci(name)})
    if not cat:
        raise HTTPException(
            status_code=400, detail=f"Category '{name}' does not exist. Create it first."
        )
    return cat["name"]


# ---------- Blogs ----------
async def unique_slug(title: str, exclude_id=None) -> str:
    base = slugify(title)
    slug, i = base, 2
    while True:
        q = {"slug": slug}
        if exclude_id:
            q["_id"] = {"$ne": exclude_id}
        if not await blogs.find_one(q, {"_id": 1}):
            return slug
        slug = f"{base}-{i}"
        i += 1


def build_query(title=None, tag=None, category=None, published_only=True):
    q = {}
    if published_only:
        q["published"] = True
    if title:
        q["title"] = {"$regex": re.escape(title.strip()), "$options": "i"}
    if tag:
        q["tags"] = tag.strip().lower()
    if category:
        q["category"] = _ci(category)
    return q


async def search_blogs(query: dict, page: int = 1, limit: int = 10):
    total = await blogs.count_documents(query)
    cursor = (
        blogs.find(query).sort("created_at", -1).skip((page - 1) * limit).limit(limit)
    )
    items = [serialize(d) async for d in cursor]
    pages = max(1, -(-total // limit))
    return items, total, pages


async def create_blog(data: dict, author: dict):
    content = data["content"].strip()
    doc = {
        "title": data["title"].strip(),
        "slug": await unique_slug(data["title"]),
        "content": content,
        "excerpt": (data.get("excerpt") or content[:160]).strip(),
        "category": await resolve_category(data.get("category")),
        "tags": clean_tags(data.get("tags")),
        "published": data.get("published", True),
        "author_id": str(author["_id"]),
        "author_name": author["name"],
        "views": 0,
        "created_at": now(),
        "updated_at": now(),
    }
    res = await blogs.insert_one(doc)
    doc["_id"] = res.inserted_id
    return serialize(doc)


async def update_blog(blog: dict, data: dict):
    upd = {}
    if data.get("title") and data["title"].strip() != blog["title"]:
        upd["title"] = data["title"].strip()
        upd["slug"] = await unique_slug(upd["title"], blog["_id"])
    if data.get("content") is not None:
        upd["content"] = data["content"].strip()
    if data.get("excerpt") is not None:
        upd["excerpt"] = data["excerpt"].strip()
    if "category" in data:
        upd["category"] = await resolve_category(data["category"])
    if data.get("tags") is not None:
        upd["tags"] = clean_tags(data["tags"])
    if data.get("published") is not None:
        upd["published"] = data["published"]
    upd["updated_at"] = now()
    await blogs.update_one({"_id": blog["_id"]}, {"$set": upd})
    return serialize(await blogs.find_one({"_id": blog["_id"]}))
