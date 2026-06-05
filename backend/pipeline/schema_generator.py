from __future__ import annotations

from backend.pipeline.naming import plural, slugify, snake, title
from backend.schemas.app_config_schema import (
    APIConfig,
    APIEndpoint,
    AppConfig,
    AppMetadata,
    AuthConfig,
    BusinessRule,
    Component,
    DatabaseConfig,
    DBColumn,
    DBTable,
    Entity,
    EntityField,
    Form,
    Page,
    Permission,
    Relationship,
    Role,
    UIConfig,
)
from backend.schemas.design_schema import SystemDesign


FIELD_TYPES = {
    "id": "uuid",
    "email": "email",
    "price": "currency",
    "amount": "currency",
    "total_amount": "currency",
    "stock": "integer",
    "threshold": "integer",
    "active": "boolean",
    "created_at": "datetime",
    "scheduled_at": "datetime",
    "recorded_at": "datetime",
    "renewal_at": "datetime",
}


class SchemaGenerator:
    def run(self, design: SystemDesign) -> AppConfig:
        entities = [self._entity(entity.name, entity.fields) for entity in design.entities]
        tables = [self._table(entity) for entity in entities]

        endpoints: list[APIEndpoint] = [self._login_endpoint()]
        pages: list[Page] = [self._login_page(), self._dashboard_page(design)]

        for entity in entities:
            read_perm = f"read:{entity.name}"
            write_perm = f"write:{entity.name}"
            manage_perm = "manage:billing" if entity.name in {"payment", "subscription"} else f"manage:{entity.name}"
            endpoints.append(self._endpoint("GET", entity, [], [read_perm]))
            if entity.name != "analytics_event":
                body_fields = [field.name for field in entity.fields if field.name not in {"id", "created_at", "recorded_at"} and not field.computed]
                endpoints.append(self._endpoint("POST", entity, body_fields, [write_perm]))
            if entity.name != "analytics_event":
                pages.append(self._entity_page(entity, design, [read_perm], [write_perm, manage_perm] if entity.name in {"payment", "subscription"} else [write_perm]))

        if design.analytics_required:
            endpoints.append(
                APIEndpoint(
                    name="read_analytics",
                    method="GET",
                    path="/api/admin/analytics",
                    entity="analytics_event",
                    table="analytics_events",
                    required_roles=["admin"],
                    required_permissions=["read:analytics"],
                    validations=["admin_role_required"],
                )
            )
            pages.append(
                Page(
                    name="Admin Analytics",
                    route="/admin/analytics",
                    layout="analytics",
                    components=[Component(name="Analytics Metrics", type="metric", entity="analytics_event"), Component(name="Funnel Chart", type="chart", entity="analytics_event")],
                    required_roles=["admin"],
                    required_permissions=["read:analytics"] + (["use:premium"] if design.premium_required else []),
                    premium_required=design.premium_required,
                )
            )

        tables.append(
            DBTable(
                name="users",
                entity="user",
                columns=[
                    DBColumn(name="id", type="uuid", primary_key=True),
                    DBColumn(name="email", type="email"),
                    DBColumn(name="password_hash", type="string"),
                    DBColumn(name="role", type="string"),
                ],
            )
        )

        auth = self._auth(design, entities)
        business_logic = self._business_rules(design)

        return AppConfig(
            app=AppMetadata(name=design.app_name, slug=slugify(design.app_name), description=design.summary),
            assumptions=list(design.risk_notes),
            entities=entities,
            ui=UIConfig(pages=pages),
            api=APIConfig(endpoints=endpoints),
            database=DatabaseConfig(tables=tables, relationships=self._relationships(tables)),
            auth=auth,
            business_logic=business_logic,
        )

    def _entity(self, name: str, fields: list[str]) -> Entity:
        return Entity(
            name=name,
            table=snake(plural(name)),
            fields=[
                EntityField(
                    name=field,
                    type=FIELD_TYPES.get(field, "string"),
                    required=field not in {"description", "notes", "domain"},
                    computed=field in {"total_amount"},
                )
                for field in fields
            ],
        )

    def _table(self, entity: Entity) -> DBTable:
        return DBTable(
            name=entity.table,
            entity=entity.name,
            columns=[
                DBColumn(name=field.name, type=field.type, primary_key=field.name == "id", nullable=not field.required)
                for field in entity.fields
                if not field.computed
            ],
        )

    def _login_page(self) -> Page:
        return Page(
            name="Login",
            route="/login",
            layout="auth",
            components=[Component(name="Login Form", type="form", entity="user")],
            forms=[Form(name="login_form", entity="user", fields=["email", "password"], submit_endpoint="/api/auth/login")],
        )

    def _dashboard_page(self, design: SystemDesign) -> Page:
        first_entity = design.entities[0].name if design.entities else "record"
        return Page(
            name="Dashboard",
            route="/dashboard",
            layout="dashboard",
            components=[Component(name="Navigation", type="nav"), Component(name="Summary Metrics", type="metric", entity=first_entity)],
            required_roles=["user"],
            required_permissions=[f"read:{first_entity}"],
        )

    def _entity_page(self, entity: Entity, design: SystemDesign, read_permissions: list[str], form_permissions: list[str]) -> Page:
        permissions = read_permissions + (["manage:billing"] if entity.name in {"payment", "subscription"} else [])
        if design.premium_required and entity.name in {"subscription", "payment"}:
            permissions.append("use:premium")
        return Page(
            name=f"{title(plural(entity.name))}",
            route=f"/{slugify(plural(entity.name))}",
            layout="crud",
            components=[Component(name=f"{title(entity.name)} Table", type="table", entity=entity.name), Component(name=f"{title(entity.name)} Form", type="form", entity=entity.name)],
            forms=[Form(name=f"{snake(entity.name)}_form", entity=entity.name, fields=[field.name for field in entity.fields if field.name not in {"id", "created_at"} and not field.computed], submit_endpoint=f"/api/{slugify(plural(entity.name))}")],
            required_roles=["user"],
            required_permissions=list(dict.fromkeys(permissions + form_permissions)),
            premium_required=design.premium_required and entity.name in {"subscription", "payment"},
        )

    def _endpoint(self, method: str, entity: Entity, body_fields: list[str], permissions: list[str]) -> APIEndpoint:
        return APIEndpoint(
            name=f"{method.lower()}_{snake(plural(entity.name))}",
            method=method,
            path=f"/api/{slugify(plural(entity.name))}",
            entity=entity.name,
            table=entity.table,
            body_fields=body_fields,
            computed_fields=[field.name for field in entity.fields if field.computed],
            validations=["body_schema_matches_table"] if body_fields else [],
            required_roles=["user"],
            required_permissions=permissions,
        )

    def _login_endpoint(self) -> APIEndpoint:
        return APIEndpoint(
            name="login",
            method="POST",
            path="/api/auth/login",
            entity="user",
            table="users",
            body_fields=["email", "password"],
            computed_fields=["password"],
            validations=["password_hash_transform"],
        )

    def _auth(self, design: SystemDesign, entities: list[Entity]) -> AuthConfig:
        roles = [Role(name=role, description=f"{title(role)} role") for role in sorted(set(design.roles + ["user"]))]
        permissions: dict[str, list[str]] = {}
        for entity in entities:
            permissions[f"read:{entity.name}"] = [role.name for role in roles]
            permissions[f"write:{entity.name}"] = ["admin", "manager"] if "admin" in [role.name for role in roles] and design.risk_notes else [role.name for role in roles]
            permissions[f"delete:{entity.name}"] = ["admin"]
            permissions[f"manage:{entity.name}"] = ["admin", "manager"]
        if design.analytics_required:
            permissions["read:analytics"] = ["admin"]
        if design.payments_required:
            permissions["manage:billing"] = ["admin"]
        if design.premium_required:
            permissions["use:premium"] = [role.name for role in roles]
        permissions["manage:users"] = ["admin"]
        return AuthConfig(
            roles=roles,
            permissions=[Permission(name=name, description=f"Allows {name}", roles=[role for role in role_names if role in {r.name for r in roles}]) for name, role_names in sorted(permissions.items())],
        )

    def _business_rules(self, design: SystemDesign) -> list[BusinessRule]:
        rules = [
            BusinessRule(name="role-access", description="Protected pages and APIs require declared roles and permissions.", expression="all(required_permissions in user.permissions)", applies_to=["ui.pages", "api.endpoints"]),
            BusinessRule(name="ownership-restriction", description="Users may update only records they own unless they have manage permission.", expression="record.owner_id == user.id or user.has_manage_permission", applies_to=["api.endpoints"]),
        ]
        if design.premium_required:
            rules.append(BusinessRule(name="premium-gating", description="Premium features require active subscription and use:premium permission.", expression="user.subscription.status == 'active' and 'use:premium' in user.permissions", applies_to=["ui.pages", "api.endpoints"]))
        if design.analytics_required:
            rules.append(BusinessRule(name="admin-analytics-access", description="Admin analytics requires admin role and read:analytics permission.", expression="user.role == 'admin' and 'read:analytics' in user.permissions", applies_to=["ui.pages", "api.endpoints"]))
        if design.payments_required:
            rules.append(BusinessRule(name="payment-access", description="Billing operations require manage:billing permission.", expression="'manage:billing' in user.permissions", applies_to=["api.endpoints"]))
        return rules

    def _relationships(self, tables: list[DBTable]) -> list[Relationship]:
        names = {table.name for table in tables}
        relationships: list[Relationship] = []
        for table in tables:
            fields = {column.name for column in table.columns}
            for column in table.columns:
                if column.name.endswith("_id") and not column.primary_key:
                    target = snake(plural(column.name[:-3]))
                    if target in names and column.name in fields:
                        relationships.append(Relationship(from_table=table.name, to_table=target, type="one_to_many", field=column.name))
        return relationships
