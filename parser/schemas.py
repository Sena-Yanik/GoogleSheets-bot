# parser/schemas.py
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class FilterItem(BaseModel):
    """Tek bir filtre koşulu."""
    field: str
    operator: str
    value: str | bool | int | float


class AggregationItem(BaseModel):
    """Aggregation bilgisi (sum, avg, count, ratio)."""
    type: str
    field: str


class SortItem(BaseModel):
    """Sıralama bilgisi."""
    field: str
    order: str = "asc"


class ParsedQuery(BaseModel):
    """LLM'den gelen ve valide edilmiş sorgu yapısı."""
    intent: str
    filters: list[FilterItem] = Field(default_factory=list)
    aggregation: Optional[AggregationItem] = None
    fields: list[str] = Field(default_factory=list)
    report_type: Optional[str] = None
    sort: Optional[SortItem] = None
    limit: int = 100
    offset: int = 0
    clarification_question: Optional[str] = None
