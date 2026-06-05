from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DesignEntity(BaseModel):
    name: str
    description: str
    fields: list[str] = Field(default_factory=list)


class SystemDesign(BaseModel):
    architecture: str = "config-driven full-stack application"
    modules: list[str] = Field(default_factory=list)
    entities: list[DesignEntity] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    user_flows: list[str] = Field(default_factory=list)
    access_model: dict[str, Any] = Field(default_factory=dict)
    data_model_summary: str = ""
    business_rules_summary: str = ""
    risk_notes: list[str] = Field(default_factory=list)
    app_name: str = "Generated App"
    summary: str = ""
    premium_required: bool = False
    analytics_required: bool = False
    payments_required: bool = False
