from pydantic import BaseModel


class GraphNodeResponse(BaseModel):
    id: str
    entity_id: int
    entity_type: str
    name: str
    article_count: int
    importance_score: float


class GraphLinkResponse(BaseModel):
    source: str
    target: str
    article_count: int
    strength_score: float
    description: str
    sample_headlines: list[str] = []


class GraphNetworkResponse(BaseModel):
    topic_id: int | None = None
    scope_label: str
    node_count: int
    link_count: int
    nodes: list[GraphNodeResponse]
    links: list[GraphLinkResponse]
