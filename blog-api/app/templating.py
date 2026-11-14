import html
from pathlib import Path

import markdown as md_lib
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def render_markdown(text: str) -> Markup:
    # Escape raw HTML first so user content can never inject scripts.
    return Markup(md_lib.markdown(html.escape(text or ""), extensions=["fenced_code", "nl2br"]))


def fmt_date(value) -> str:
    return value.strftime("%b %d, %Y") if value else ""


def read_time(text: str) -> int:
    return max(1, round(len((text or "").split()) / 200))


templates.env.filters["md"] = render_markdown
templates.env.filters["date"] = fmt_date
templates.env.filters["read_time"] = read_time
