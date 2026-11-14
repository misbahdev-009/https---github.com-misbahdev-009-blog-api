from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import blogs
from ..schemas import BlogCreate, BlogUpdate, BlogOut, BlogList
from ..security import get_current_user
from ..services import build_query, search_blogs, create_blog, update_blog
from ..utils import serialize

router = APIRouter(prefix="/api/blogs", tags=["Blogs"])


async def _find(ident: str):
    doc = None
    if ObjectId.is_valid(ident):
        doc = await blogs.find_one({"_id": ObjectId(ident)})
    if not doc:
        doc = await blogs.find_one({"slug": ident})
    if not doc:
        raise HTTPException(404, "Blog not found")
    return doc


def _can_edit(user, blog) -> bool:
    return user.get("role") == "admin" or str(user["_id"]) == blog["author_id"]


@router.get("", response_model=BlogList)
async def list_blogs(
    title: Optional[str] = Query(None, description="Search by title (partial, case-insensitive)"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    category: Optional[str] = Query(None, description="Filter by category name"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    """List published blogs. Combine `title`, `tag` and `category` to search."""
    items, total, pages = await search_blogs(build_query(title, tag, category), page, limit)
    return {"items": items, "total": total, "page": page, "pages": pages}


@router.get("/mine", response_model=BlogList)
async def my_blogs(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    user=Depends(get_current_user),
):
    """List every blog (including drafts) written by the logged-in user."""
    q = {"author_id": str(user["_id"])}
    items, total, pages = await search_blogs(q, page, limit)
    return {"items": items, "total": total, "page": page, "pages": pages}


@router.get("/{id_or_slug}", response_model=BlogOut)
async def get_blog(id_or_slug: str):
    doc = await _find(id_or_slug)
    if not doc.get("published"):
        raise HTTPException(404, "Blog not found")
    await blogs.update_one({"_id": doc["_id"]}, {"$inc": {"views": 1}})
    doc["views"] = doc.get("views", 0) + 1
    return serialize(doc)


@router.post("", response_model=BlogOut, status_code=201)
async def create(payload: BlogCreate, user=Depends(get_current_user)):
    return await create_blog(payload.model_dump(), user)


@router.put("/{blog_id}", response_model=BlogOut)
async def update(blog_id: str, payload: BlogUpdate, user=Depends(get_current_user)):
    blog = await _find(blog_id)
    if not _can_edit(user, blog):
        raise HTTPException(403, "You can only edit your own blogs")
    return await update_blog(blog, payload.model_dump(exclude_unset=True))


@router.delete("/{blog_id}")
async def delete(blog_id: str, user=Depends(get_current_user)):
    blog = await _find(blog_id)
    if not _can_edit(user, blog):
        raise HTTPException(403, "You can only delete your own blogs")
    await blogs.delete_one({"_id": blog["_id"]})
    return {"message": "Blog deleted"}
