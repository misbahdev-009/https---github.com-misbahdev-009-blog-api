# Quillnote - Blogging API with Admin Panel

FastAPI + MongoDB Atlas + Jinja2.

## Setup
1. `python -m venv venv` then activate it
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and paste your MongoDB Atlas connection string.
4. `uvicorn app.main:app --reload`

## URLs
- Website:        http://127.0.0.1:8000/
- API docs:       http://127.0.0.1:8000/docs  (Swagger)  |  /redoc
- Register:       http://127.0.0.1:8000/register  (first account becomes admin)
- Admin panel:    http://127.0.0.1:8000/admin

## API summary
| Method | Endpoint | Auth |
|---|---|---|
| POST | /api/auth/register | - |
| POST | /api/auth/login | - |
| GET | /api/auth/me | user |
| GET | /api/blogs?title=&tag=&category=&page=&limit= | - |
| GET | /api/blogs/mine | user |
| GET | /api/blogs/{id or slug} | - |
| POST | /api/blogs | user |
| PUT | /api/blogs/{id} | owner/admin |
| DELETE | /api/blogs/{id} | owner/admin |
| GET | /api/categories | - |
| POST/PUT/DELETE | /api/categories[/{id}] | admin |
