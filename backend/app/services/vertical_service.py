from slugify import slugify
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vertical import Vertical

DEFAULT_VERTICALS = [
    ("Healthcare", "health"),
    ("Finance", "dollar-sign"),
    ("Legal", "scale"),
    ("Education", "book-open"),
    ("Manufacturing", "factory"),
    ("Retail", "shopping-cart"),
    ("Media", "tv"),
    ("Government", "landmark"),
    ("Defence", "shield"),
    ("Transport", "truck"),
    ("Cybersecurity", "lock"),
    ("Energy", "zap"),
    ("Life Sciences", "flask-conical"),
    ("Research", "microscope"),
    ("Telecoms", "radio"),
]


async def seed_verticals(db: AsyncSession) -> None:
    for name, icon in DEFAULT_VERTICALS:
        existing = (await db.execute(select(Vertical).where(Vertical.name == name))).scalar_one_or_none()
        if not existing:
            db.add(Vertical(name=name, slug=slugify(name), icon_name=icon))
    await db.commit()


async def get_or_create_vertical(db: AsyncSession, name: str) -> Vertical | None:
    result = await db.execute(select(Vertical).where(Vertical.name.ilike(name)))
    v = result.scalar_one_or_none()
    return v


async def list_verticals(db: AsyncSession, search: str = "") -> list[Vertical]:
    query = select(Vertical)
    if search:
        query = query.where(Vertical.name.ilike(f"%{search}%"))
    query = query.order_by(Vertical.name)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_vertical(db: AsyncSession, vertical_id: int) -> Vertical | None:
    return (await db.execute(select(Vertical).where(Vertical.id == vertical_id))).scalar_one_or_none()
