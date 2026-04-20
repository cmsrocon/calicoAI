import asyncio
from dataclasses import dataclass
from datetime import datetime

import feedparser
import httpx
from bs4 import BeautifulSoup

from app.utils.date_utils import parse_date, utcnow
from app.utils.text_utils import clean_html, truncate


@dataclass
class RawItem:
    title: str
    url: str
    body_text: str
    published_at: datetime | None
    source_id: int
    source_name: str


async def fetch_source(source_id: int, source_name: str, url: str, feed_type: str, css_selector: str | None = None) -> tuple[list[RawItem], str | None]:
    """Returns (items, error_message)."""
    try:
        if feed_type == "rss":
            return await _fetch_rss(source_id, source_name, url), None
        else:
            return await _fetch_html(source_id, source_name, url, css_selector), None
    except Exception as e:
        return [], str(e)


async def _fetch_rss(source_id: int, source_name: str, url: str) -> list[RawItem]:
    loop = asyncio.get_event_loop()
    feed = await loop.run_in_executor(None, feedparser.parse, url)
    items = []
    for entry in feed.entries[:50]:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        if not title or not link:
            continue
        body = ""
        for key in ("summary", "content", "description"):
            raw = entry.get(key, "")
            if isinstance(raw, list):
                raw = " ".join(c.get("value", "") for c in raw)
            if raw:
                body = clean_html(raw)
                break
        pub_date = None
        for key in ("published", "updated", "created"):
            val = entry.get(key)
            if val:
                pub_date = parse_date(str(val))
                if pub_date:
                    break
        items.append(RawItem(
            title=title,
            url=link,
            body_text=truncate(body, 6000),
            published_at=pub_date,
            source_id=source_id,
            source_name=source_name,
        ))
    return items


async def _fetch_html(source_id: int, source_name: str, url: str, css_selector: str | None) -> list[RawItem]:
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "GingerAI/1.0 (+https://gingerai.app)"})
        resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    items = []
    if css_selector:
        elements = soup.select(css_selector)
    else:
        elements = soup.find_all("article") or soup.find_all("li", class_=lambda c: c and "article" in c.lower())
    for el in elements[:50]:
        a_tag = el.find("a", href=True)
        if not a_tag:
            continue
        title = a_tag.get_text(strip=True)
        href = a_tag["href"]
        if href.startswith("/"):
            from urllib.parse import urlparse
            parsed = urlparse(url)
            href = f"{parsed.scheme}://{parsed.netloc}{href}"
        body = clean_html(el.get_text(separator=" "))
        items.append(RawItem(
            title=title,
            url=href,
            body_text=truncate(body, 6000),
            published_at=None,
            source_id=source_id,
            source_name=source_name,
        ))
    return items


async def test_source(url: str, feed_type: str, css_selector: str | None = None) -> tuple[int, str | None, str | None]:
    """Returns (item_count, sample_title, error)."""
    items, error = await fetch_source(0, "test", url, feed_type, css_selector)
    if error:
        return 0, None, error
    sample = items[0].title if items else None
    return len(items), sample, None
