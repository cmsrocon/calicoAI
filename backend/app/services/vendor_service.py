import json

from slugify import slugify
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vendor import Vendor


async def get_or_create_vendor(db: AsyncSession, name: str, description: str = "", aliases: list[str] | None = None) -> Vendor:
    result = await db.execute(select(Vendor).where(Vendor.name == name))
    vendor = result.scalar_one_or_none()
    if vendor:
        return vendor
    # Check aliases
    all_vendors = (await db.execute(select(Vendor))).scalars().all()
    name_lower = name.lower()
    for v in all_vendors:
        v_aliases = json.loads(v.aliases or "[]")
        if any(a.lower() == name_lower for a in v_aliases) or v.name.lower() == name_lower:
            return v
    slug = slugify(name)
    existing_slug = (await db.execute(select(Vendor).where(Vendor.slug == slug))).scalar_one_or_none()
    if existing_slug:
        slug = f"{slug}-{abs(hash(name)) % 1000}"
    vendor = Vendor(
        name=name,
        slug=slug,
        description=description,
        aliases=json.dumps(aliases or []),
    )
    db.add(vendor)
    await db.flush()
    return vendor


async def list_vendors(db: AsyncSession, search: str = "", page: int = 1, page_size: int = 50) -> tuple[list[Vendor], int]:
    query = select(Vendor).where(Vendor.is_active == True)
    if search:
        query = query.where(Vendor.name.ilike(f"%{search}%"))
    query = query.order_by(Vendor.name)
    result = await db.execute(query)
    all_items = result.scalars().all()
    total = len(all_items)
    offset = (page - 1) * page_size
    return list(all_items[offset:offset + page_size]), total


async def get_vendor(db: AsyncSession, vendor_id: int) -> Vendor | None:
    return (await db.execute(select(Vendor).where(Vendor.id == vendor_id))).scalar_one_or_none()
