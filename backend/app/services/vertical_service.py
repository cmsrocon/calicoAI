from slugify import slugify
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vertical import Vertical


async def get_or_create_vertical(db: AsyncSession, name: str) -> Vertical | None:
    result = await db.execute(select(Vertical).where(Vertical.name.ilike(name)))
    vertical = result.scalar_one_or_none()
    if vertical:
        return vertical
    slug = slugify(name) or "theme"
    existing_slug = (await db.execute(select(Vertical).where(Vertical.slug == slug))).scalar_one_or_none()
    if existing_slug:
        slug = f"{slug}-{abs(hash(name)) % 1000}"
    vertical = Vertical(name=name, slug=slug, icon_name=None)
    db.add(vertical)
    await db.flush()
    return vertical


async def list_verticals(db: AsyncSession, search: str = "") -> list[Vertical]:
    query = select(Vertical)
    if search:
        query = query.where(Vertical.name.ilike(f"%{search}%"))
    query = query.order_by(Vertical.name)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_vertical(db: AsyncSession, vertical_id: int) -> Vertical | None:
    return (await db.execute(select(Vertical).where(Vertical.id == vertical_id))).scalar_one_or_none()
