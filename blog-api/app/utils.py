import re
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException


def now():
    return datetime.now(timezone.utc)


def slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[\s_-]+", "-", s) or "post"


def to_oid(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    return ObjectId(value)


def serialize(doc):
    """Convert a MongoDB document into a JSON-friendly dict."""
    if not doc:
        return doc
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    doc.pop("password", None)
    return doc


def clean_tags(tags):
    return sorted({t.strip().lower() for t in (tags or []) if t and t.strip()})


def split_tags(raw: str):
    return clean_tags((raw or "").split(","))
