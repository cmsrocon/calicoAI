from collections import defaultdict
from itertools import combinations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.news_item import NewsItem, NewsItemVendor, NewsItemVertical
from app.models.vendor import Vendor
from app.models.vertical import Vertical
from app.schemas.graph import GraphLinkResponse, GraphNetworkResponse, GraphNodeResponse
from app.services.topic_service import get_topic

router = APIRouter(prefix="/graph", tags=["graph"])


def _node_key(entity_type: str, entity_id: int) -> str:
    return f"{entity_type}:{entity_id}"


def _article_weight(item: NewsItem) -> float:
    importance = max(item.importance_rank or 4, 1)
    relevance = item.ai_relevance_score if item.ai_relevance_score is not None else 0.6
    return float(importance) * (0.65 + max(0.0, min(relevance, 1.0)) * 0.7)


def _link_description(source: dict, target: dict, article_count: int) -> str:
    if source["entity_type"] == "vendor" and target["entity_type"] == "vendor":
        return f"{source['name']} and {target['name']} are co-mentioned in {article_count} tracked articles."
    if source["entity_type"] == "vertical" and target["entity_type"] == "vertical":
        return f"{source['name']} and {target['name']} appear together as themes in {article_count} tracked articles."

    entity = source if source["entity_type"] == "vendor" else target
    theme = target if source["entity_type"] == "vendor" else source
    return f"{entity['name']} appears in {article_count} tracked articles that are also tagged with the theme {theme['name']}."


@router.get("/network", response_model=GraphNetworkResponse)
async def get_graph_network(
    topic_id: int | None = None,
    node_limit: int = Query(24, ge=6, le=60),
    edge_limit: int = Query(60, ge=10, le=180),
    db: AsyncSession = Depends(get_db),
):
    topic = None
    if topic_id is not None:
        topic = await get_topic(db, topic_id)
        if topic is None:
            raise HTTPException(status_code=404, detail="Topic not found")

    item_query = select(NewsItem).where(NewsItem.is_processed == True)
    if topic_id is not None:
        item_query = item_query.where(NewsItem.topic_id == topic_id)
    items = (await db.execute(
        item_query.order_by(NewsItem.importance_rank.desc().nullslast(), NewsItem.ingested_at.desc())
    )).scalars().all()

    if not items:
        return GraphNetworkResponse(
            topic_id=topic_id,
            scope_label=topic.name if topic else "All topics",
            node_count=0,
            link_count=0,
            nodes=[],
            links=[],
        )

    item_ids = [item.id for item in items]
    item_by_id = {item.id: item for item in items}

    vendor_rows = (await db.execute(
        select(NewsItemVendor.news_item_id, NewsItemVendor.vendor_id, NewsItemVendor.confidence, Vendor.name)
        .join(Vendor, Vendor.id == NewsItemVendor.vendor_id)
        .where(NewsItemVendor.news_item_id.in_(item_ids))
    )).all()
    vertical_rows = (await db.execute(
        select(NewsItemVertical.news_item_id, NewsItemVertical.vertical_id, NewsItemVertical.confidence, Vertical.name)
        .join(Vertical, Vertical.id == NewsItemVertical.vertical_id)
        .where(NewsItemVertical.news_item_id.in_(item_ids))
    )).all()

    item_entities: dict[int, list[dict]] = defaultdict(list)
    node_stats: dict[str, dict] = {}
    edge_stats: dict[tuple[str, str], dict] = {}

    for news_item_id, vendor_id, confidence, name in vendor_rows:
        node_id = _node_key("vendor", vendor_id)
        item_entities[news_item_id].append({
            "id": node_id,
            "entity_id": vendor_id,
            "entity_type": "vendor",
            "name": name,
            "confidence": float(confidence or 1.0),
        })

    for news_item_id, vertical_id, confidence, name in vertical_rows:
        node_id = _node_key("vertical", vertical_id)
        item_entities[news_item_id].append({
            "id": node_id,
            "entity_id": vertical_id,
            "entity_type": "vertical",
            "name": name,
            "confidence": float(confidence or 1.0),
        })

    for news_item_id, entities in item_entities.items():
        news_item = item_by_id.get(news_item_id)
        if news_item is None or not entities:
            continue

        article_weight = _article_weight(news_item)
        unique_entities: dict[str, dict] = {}
        for entity in entities:
            existing = unique_entities.get(entity["id"])
            if existing is None or entity["confidence"] > existing["confidence"]:
                unique_entities[entity["id"]] = entity

        entities_for_item = list(unique_entities.values())
        for entity in entities_for_item:
            node = node_stats.setdefault(entity["id"], {
                "id": entity["id"],
                "entity_id": entity["entity_id"],
                "entity_type": entity["entity_type"],
                "name": entity["name"],
                "article_count": 0,
                "importance_score": 0.0,
            })
            node["article_count"] += 1
            node["importance_score"] += article_weight * entity["confidence"]

        for source, target in combinations(
            sorted(entities_for_item, key=lambda entity: (entity["entity_type"], entity["name"].lower())),
            2,
        ):
            edge_key = tuple(sorted((source["id"], target["id"])))
            edge = edge_stats.setdefault(edge_key, {
                "source": edge_key[0],
                "target": edge_key[1],
                "article_count": 0,
                "strength_score": 0.0,
                "sample_headlines": [],
            })
            edge["article_count"] += 1
            edge["strength_score"] += article_weight * min(source["confidence"], target["confidence"])
            if news_item.headline and news_item.headline not in edge["sample_headlines"] and len(edge["sample_headlines"]) < 3:
                edge["sample_headlines"].append(news_item.headline)

    top_nodes = sorted(
        node_stats.values(),
        key=lambda node: (node["importance_score"], node["article_count"], node["name"].lower()),
        reverse=True,
    )[:node_limit]
    retained_node_ids = {node["id"] for node in top_nodes}

    top_links = [
        edge for edge in sorted(
            edge_stats.values(),
            key=lambda edge: (edge["strength_score"], edge["article_count"]),
            reverse=True,
        )
        if edge["source"] in retained_node_ids and edge["target"] in retained_node_ids
    ][:edge_limit]

    connected_node_ids = {edge["source"] for edge in top_links} | {edge["target"] for edge in top_links}
    if connected_node_ids:
        top_nodes = [node for node in top_nodes if node["id"] in connected_node_ids]
    retained_nodes = {node["id"]: node for node in top_nodes}

    links = []
    for edge in top_links:
        source = retained_nodes.get(edge["source"])
        target = retained_nodes.get(edge["target"])
        if source is None or target is None:
            continue
        links.append(GraphLinkResponse(
            source=edge["source"],
            target=edge["target"],
            article_count=edge["article_count"],
            strength_score=round(edge["strength_score"], 3),
            description=_link_description(source, target, edge["article_count"]),
            sample_headlines=edge["sample_headlines"],
        ))

    nodes = [
        GraphNodeResponse(
            id=node["id"],
            entity_id=node["entity_id"],
            entity_type=node["entity_type"],
            name=node["name"],
            article_count=node["article_count"],
            importance_score=round(node["importance_score"], 3),
        )
        for node in sorted(
            retained_nodes.values(),
            key=lambda node: (node["importance_score"], node["article_count"]),
            reverse=True,
        )
    ]

    return GraphNetworkResponse(
        topic_id=topic_id,
        scope_label=topic.name if topic else "All topics",
        node_count=len(nodes),
        link_count=len(links),
        nodes=nodes,
        links=links,
    )
