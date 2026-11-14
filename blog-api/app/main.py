from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routers import auth, blogs, categories, pages, admin

DESCRIPTION = """
A blogging platform with a JSON API and an admin panel.

* **Authentication** - register, log in (JWT) and view your profile
* **Blogs** - full CRUD, plus search by `title`, `tag` and `category`
* **Categories** - manage categories (admin only for changes)

**How to try protected endpoints:** register at `/api/auth/register`, click **Authorize**
at the top right, and log in with your email as the username. The first account created becomes an admin.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Quillnote Blogging API",
    description=DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.exception_handler(admin.RedirectToLogin)
async def redirect_to_login(request, exc):
    return RedirectResponse("/admin/login", status_code=303)


app.include_router(auth.router)
app.include_router(blogs.router)
app.include_router(categories.router)
app.include_router(pages.router)
app.include_router(admin.router)
