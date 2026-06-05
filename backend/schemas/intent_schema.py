from __future__ import annotations

from pydantic import BaseModel, Field


class IntentModel(BaseModel):
    app_type: str = "business_app"
    domain: str = "generic_business"
    primary_goal: str = ""
    features: list[str] = Field(default_factory=list)
    requested_entities: list[str] = Field(default_factory=list)
    requested_roles: list[str] = Field(default_factory=list)
    auth_required: bool = True
    payments_required: bool = False
    analytics_required: bool = False
    premium_required: bool = False
    crud_required: bool = True
    ambiguities: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    missing_details: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
