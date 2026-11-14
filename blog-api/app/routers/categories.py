from fastapi import APIRouter, Depends, HTTPException

from ..database import categories, blogs
from ..schemas import CategoryCreate, CategoryUpdate, CategoryOut
from ..security import require_admin
from ..services import _ci
from ..utils import now, serialize, to_oid

router = APIRouter(prefix="/api/categories", tags=["Categories"])


@router.get("", response_model=list[CategoryOut])
async def list_categories():
    return [serialize(c) async for c in categories.find().sort("name", 1)]


@router.get("/{category_id}", response_model=CategoryOut)
async def get_category(category_id: str):
    cat = await categories.find_one({"_id": to_oid(category_id)})
    if not cat:
        raise HTTPException(404, "Category not found")
    return serialize(cat)


@router.post("", response_model=CategoryOut, status_code=201, dependencies=[Depends(require_admin)])
async def create_category(payload: CategoryCreate):
    if await categories.find_one({"name": _ci(payload.name)}):
        raise HTTPException(400, "Category already exists")
    doc = {"name": payload.name.strip(), "description": payload.description, "created_at": now()}
    res = await categories.insert_one(doc)
    doc["_id"] = res.inserted_id
    return serialize(doc)


@router.put("/{category_id}", response_model=CategoryOut, dependencies=[Depends(require_admin)])
async def update_category(category_id: str, payload: CategoryUpdate):
    oid = to_oid(category_id)
    cat = await categories.find_one({"_id": oid})
    if not cat:
        raise HTTPException(404, "Category not found")
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "name" in data:
        data["name"] = data["name"].strip()
        clash = await categories.find_one({"name": _ci(data["name"]), "_id": {"$ne": oid}})
        if clash:
            raise HTTPException(400, "Another category already uses that name")
    if data:
        await categories.update_one({"_id": oid}, {"$set": data})
        if "name" in data and data["name"] != cat["name"]:
            await blogs.update_many({"category": cat["name"]}, {"$set": {"category": data["name"]}})
    return serialize(await categories.find_one({"_id": oid}))


@router.delete("/{category_id}", dependencies=[Depends(require_admin)])
async def delete_category(category_id: str):
    oid = to_oid(category_id)
    cat = await categories.find_one({"_id": oid})
    if not cat:
        raise HTTPException(404, "Category not found")
    await categories.delete_one({"_id": oid})
    await blogs.update_many({"category": cat["name"]}, {"$set": {"category": None}})
    return {"message": "Category deleted"}
