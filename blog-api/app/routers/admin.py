"""Admin panel (cookie-based login, Jinja2 pages)."""
from typing import Optional
from urllib.parse import urlencode, quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..database import users, blogs, categories
from ..security import verify_password, create_access_token, user_from_token
from ..services import (
    build_query, search_blogs, create_blog, update_blog, _ci,
)
from ..templating import templates
from ..utils import now, serialize, split_tags, to_oid

router = APIRouter(prefix="/admin", include_in_schema=False)


class RedirectToLogin(Exception):
    pass


async def admin_user(request: Request):
    user = await user_from_token(request.cookies.get("access_token"))
    if not user or user.get("role") != "admin":
        raise RedirectToLogin()
    return user


def back(path: str, msg: str, kind: str = "success"):
    return RedirectResponse(f"{path}{'&' if '?' in path else '?'}msg={quote(msg)}&kind={kind}", status_code=303)


# ---------- Login / logout ----------
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = await user_from_token(request.cookies.get("access_token"))
    if user and user.get("role") == "admin":
        return RedirectResponse("/admin", status_code=302)
    return templates.TemplateResponse(request, "admin/login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    user = await users.find_one({"email": email.lower().strip()})
    error = None
    if not user or not verify_password(password, user["password"]):
        error = "Incorrect email or password."
    elif user.get("role") != "admin":
        error = "This account is not an admin. Only admins can open the panel."
    if error:
        return templates.TemplateResponse(
            request, "admin/login.html", {"request": request, "error": error}, status_code=401
        )
    resp = RedirectResponse("/admin", status_code=303)
    resp.set_cookie(
        "access_token", create_access_token(str(user["_id"])),
        httponly=True, samesite="lax", max_age=60 * 60 * 24,
    )
    return resp


@router.get("/logout")
async def logout():
    resp = RedirectResponse("/admin/login?msg=You have been logged out.", status_code=303)
    resp.delete_cookie("access_token")
    return resp


# ---------- Dashboard ----------
@router.get("", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    title: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    admin=Depends(admin_user),
):
    q = build_query(title=title, category=category, published_only=False)
    if status == "published":
        q["published"] = True
    elif status == "draft":
        q["published"] = False
    items, total, pages = await search_blogs(q, max(page, 1), 10)
    stats = {
        "total": await blogs.count_documents({}),
        "published": await blogs.count_documents({"published": True}),
        "drafts": await blogs.count_documents({"published": False}),
        "categories": await categories.count_documents({}),
        "users": await users.count_documents({}),
    }
    cats = [serialize(c) async for c in categories.find().sort("name", 1)]
    base_qs = urlencode({k: v for k, v in {"title": title, "category": category, "status": status}.items() if v})
    return templates.TemplateResponse(
        request, "admin/dashboard.html",
        {
            "request": request, "admin": admin, "items": items, "total": total,
            "page": max(page, 1), "pages": pages, "stats": stats, "categories": cats,
            "title_q": title or "", "category_q": category or "", "status_q": status or "",
            "base_qs": base_qs, "active": "blogs",
        },
    )


# ---------- Blog create / edit / delete ----------
async def _form_ctx(request, admin, blog=None, error=None):
    cats = [serialize(c) async for c in categories.find().sort("name", 1)]
    return {"request": request, "admin": admin, "blog": blog, "categories": cats, "error": error, "active": "new"}


@router.get("/blogs/new", response_class=HTMLResponse)
async def new_blog_page(request: Request, admin=Depends(admin_user)):
    return templates.TemplateResponse(request, "admin/blog_form.html", await _form_ctx(request, admin))


@router.post("/blogs/new")
async def new_blog_submit(
    request: Request,
    title: str = Form(...), content: str = Form(...), excerpt: str = Form(""),
    category: str = Form(""), tags: str = Form(""), published: bool = Form(False),
    admin=Depends(admin_user),
):
    if len(title.strip()) < 3 or len(content.strip()) < 10:
        draft = {"title": title, "content": content, "excerpt": excerpt, "category": category,
                 "tags": split_tags(tags), "published": published}
        ctx = await _form_ctx(request, admin, draft, "Title needs 3+ characters and content needs 10+ characters.")
        return templates.TemplateResponse(request, "admin/blog_form.html", ctx, status_code=400)
    await create_blog(
        {"title": title, "content": content, "excerpt": excerpt, "category": category or None,
         "tags": split_tags(tags), "published": published},
        admin,
    )
    return back("/admin", "Blog created.")


@router.get("/blogs/{blog_id}/edit", response_class=HTMLResponse)
async def edit_blog_page(request: Request, blog_id: str, admin=Depends(admin_user)):
    blog = await blogs.find_one({"_id": to_oid(blog_id)})
    if not blog:
        raise HTTPException(404, "Blog not found")
    return templates.TemplateResponse(request, "admin/blog_form.html", await _form_ctx(request, admin, serialize(blog)))


@router.post("/blogs/{blog_id}/edit")
async def edit_blog_submit(
    request: Request, blog_id: str,
    title: str = Form(...), content: str = Form(...), excerpt: str = Form(""),
    category: str = Form(""), tags: str = Form(""), published: bool = Form(False),
    admin=Depends(admin_user),
):
    blog = await blogs.find_one({"_id": to_oid(blog_id)})
    if not blog:
        raise HTTPException(404, "Blog not found")
    await update_blog(
        blog,
        {"title": title, "content": content, "excerpt": excerpt or blog.get("excerpt", ""),
         "category": category or None, "tags": split_tags(tags), "published": published},
    )
    return back("/admin", "Blog updated.")


@router.post("/blogs/{blog_id}/delete")
async def delete_blog(blog_id: str, admin=Depends(admin_user)):
    await blogs.delete_one({"_id": to_oid(blog_id)})
    return back("/admin", "Blog deleted.")


@router.post("/blogs/{blog_id}/toggle")
async def toggle_publish(blog_id: str, admin=Depends(admin_user)):
    blog = await blogs.find_one({"_id": to_oid(blog_id)})
    if blog:
        await blogs.update_one({"_id": blog["_id"]}, {"$set": {"published": not blog.get("published"), "updated_at": now()}})
    return back("/admin", "Blog status changed.")


# ---------- Categories ----------
@router.get("/categories", response_class=HTMLResponse)
async def categories_page(request: Request, admin=Depends(admin_user)):
    cats = []
    async for c in categories.find().sort("name", 1):
        c = serialize(c)
        c["count"] = await blogs.count_documents({"category": c["name"]})
        cats.append(c)
    return templates.TemplateResponse(
        request, "admin/categories.html",
        {"request": request, "admin": admin, "categories": cats, "active": "categories"},
    )


@router.post("/categories")
async def add_category(name: str = Form(...), description: str = Form(""), admin=Depends(admin_user)):
    name = name.strip()
    if len(name) < 2:
        return back("/admin/categories", "Category name needs at least 2 characters.", "error")
    if await categories.find_one({"name": _ci(name)}):
        return back("/admin/categories", "That category already exists.", "error")
    await categories.insert_one({"name": name, "description": description.strip(), "created_at": now()})
    return back("/admin/categories", "Category added.")


@router.post("/categories/{cat_id}/edit")
async def edit_category(cat_id: str, name: str = Form(...), description: str = Form(""), admin=Depends(admin_user)):
    oid = to_oid(cat_id)
    cat = await categories.find_one({"_id": oid})
    name = name.strip()
    if not cat or len(name) < 2:
        return back("/admin/categories", "Could not update category.", "error")
    if await categories.find_one({"name": _ci(name), "_id": {"$ne": oid}}):
        return back("/admin/categories", "Another category already uses that name.", "error")
    await categories.update_one({"_id": oid}, {"$set": {"name": name, "description": description.strip()}})
    if name != cat["name"]:
        await blogs.update_many({"category": cat["name"]}, {"$set": {"category": name}})
    return back("/admin/categories", "Category updated.")


@router.post("/categories/{cat_id}/delete")
async def delete_category(cat_id: str, admin=Depends(admin_user)):
    oid = to_oid(cat_id)
    cat = await categories.find_one({"_id": oid})
    if cat:
        await categories.delete_one({"_id": oid})
        await blogs.update_many({"category": cat["name"]}, {"$set": {"category": None}})
    return back("/admin/categories", "Category deleted.")
