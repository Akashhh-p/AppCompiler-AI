from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from backend.schemas.execution_schema import ExecutionReport
from backend.schemas.validation_schema import ValidationIssue, ValidationReport


class AppMetadata(BaseModel):
    name: str
    slug: str
    version: str = "1.0.0"
    description: str


class EntityField(BaseModel):
    name: str
    type: Literal["string", "text", "integer", "float", "boolean", "datetime", "uuid", "email", "currency"]
    required: bool = True
    computed: bool = False


class Entity(BaseModel):
    name: str
    table: str
    fields: list[EntityField]


class Component(BaseModel):
    name: str
    type: Literal["table", "form", "chart", "metric", "nav", "detail", "button", "list"]
    entity: str | None = None


class Form(BaseModel):
    name: str
    entity: str
    fields: list[str]
    submit_endpoint: str


class Page(BaseModel):
    name: str
    route: str
    layout: str = "standard"
    components: list[Component] = Field(default_factory=list)
    forms: list[Form] = Field(default_factory=list)
    required_roles: list[str] = Field(default_factory=list)
    required_permissions: list[str] = Field(default_factory=list)
    premium_required: bool = False


class UIConfig(BaseModel):
    pages: list[Page] = Field(default_factory=list)


class APIEndpoint(BaseModel):
    name: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str
    entity: str
    table: str
    body_fields: list[str] = Field(default_factory=list)
    computed_fields: list[str] = Field(default_factory=list)
    validations: list[str] = Field(default_factory=list)
    required_roles: list[str] = Field(default_factory=list)
    required_permissions: list[str] = Field(default_factory=list)


class APIConfig(BaseModel):
    endpoints: list[APIEndpoint] = Field(default_factory=list)


class DBColumn(BaseModel):
    name: str
    type: str
    primary_key: bool = False
    nullable: bool = False


class DBTable(BaseModel):
    name: str
    entity: str
    columns: list[DBColumn]


class Relationship(BaseModel):
    from_table: str
    to_table: str
    type: Literal["one_to_one", "one_to_many", "many_to_many"]
    field: str


class DatabaseConfig(BaseModel):
    tables: list[DBTable] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)


class Role(BaseModel):
    name: str
    description: str


class Permission(BaseModel):
    name: str
    description: str
    roles: list[str]


class AuthConfig(BaseModel):
    roles: list[Role] = Field(default_factory=list)
    permissions: list[Permission] = Field(default_factory=list)


class BusinessRule(BaseModel):
    name: str
    description: str
    expression: str
    applies_to: list[str] = Field(default_factory=list)


class RepairRecord(BaseModel):
    issue_code: str
    location: str
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)
    repair: str
    strategy: str = "partial_patch"
    status: Literal["fixed", "skipped"] = "fixed"


class AppConfig(BaseModel):
    app: AppMetadata
    assumptions: list[str] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    ui: UIConfig = Field(default_factory=UIConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    business_logic: list[BusinessRule] = Field(default_factory=list)
    validation: ValidationReport = Field(default_factory=ValidationReport)
    repair_history: list[RepairRecord] = Field(default_factory=list)
    execution: ExecutionReport = Field(default_factory=ExecutionReport)

    @model_validator(mode="after")
    def ensure_required_top_level_sections(self) -> "AppConfig":
        # Pydantic enforces shape and types; semantic cross-reference validation
        # intentionally lives in the compiler validator for explainable repairs.
        return self


def model_to_jsonable(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")
