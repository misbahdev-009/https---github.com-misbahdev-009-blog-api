"""Public website pages rendered with Jinja2."""
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..database import blogs, categories
from ..security import user_from_token
from ..services import build_query, search_blogs, create_user
from ..templating import templates
from ..utils import serialize

router = APIRouter(include_in_schema=False)


async def _ctx(request: Request, **extra):
    user = await user_from_token(request.cookies.get("access_token"))
    return {"request": request, "current_user": user, **extra}


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    title: Optional[str] = None,
    tag: Optional[str] = None,
    category: Optional[str] = None,
    page: int = 1,
):
    page = max(page, 1)
    items, total, pages = await search_blogs(build_query(title, tag, category), page, 9)
    cats = [serialize(c) async for c in categories.find().sort("name", 1)]
    tag_rows = blogs.aggregate(
        [
            {"$match": {"published": True}},
            {"$unwind": "$tags"},
            {"$group": {"_id": "$tags", "n": {"$sum": 1}}},
            {"$sort": {"n": -1}},
            {"$limit": 12},
        ]
    )
    top_tags = [r["_id"] async for r in tag_rows]
    base_qs = urlencode({k: v for k, v in {"title": title, "tag": tag, "category": category}.items() if v})
    return templates.TemplateResponse(
        request,
        "index.html",
        await _ctx(
            request, items=items, total=total, page=page, pages=pages,
            categories=cats, top_tags=top_tags, title_q=title or "",
            tag_q=tag or "", category_q=category or "", base_qs=base_qs,
        ),
    )


@router.get("/blog/{slug}", response_class=HTMLResponse)
async def post(request: Request, slug: str):
    doc = await blogs.find_one({"slug": slug, "published": True})
    if not doc:
        raise HTTPException(404, "Post not found")
    await blogs.update_one({"_id": doc["_id"]}, {"$inc": {"views": 1}})
    doc["views"] = doc.get("views", 0) + 1
    related = []
    if doc.get("category"):
        cursor = blogs.find(
            {"published": True, "category": doc["category"], "_id": {"$ne": doc["_id"]}}
        ).sort("created_at", -1).limit(3)
        related = [serialize(d) async for d in cursor]
    return templates.TemplateResponse(
        request, "post.html", await _ctx(request, post=serialize(doc), related=related)
    )


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", await _ctx(request, error=None))


@router.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...)
):
    if len(password) < 6 or len(name.strip()) < 2 or "@" not in email:
        error = "Enter your name, a valid email and a password of at least 6 characters."
    else:
        try:
            await create_user(name, email, password)
            return RedirectResponse("/admin/login?msg=Account created. Log in to continue.", status_code=303)
        except HTTPException as e:
            error = e.detail
    return templates.TemplateResponse(request, "register.html", await _ctx(request, error=error), status_code=400)


@router.get("/login")
async def login_redirect():
    return RedirectResponse("/admin/login", status_code=302)
