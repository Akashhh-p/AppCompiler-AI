from __future__ import annotations

import json
from collections import Counter
from typing import Any

from pydantic import ValidationError

from backend.schemas.app_config_schema import AppConfig
from backend.schemas.validation_schema import ValidationIssue, ValidationReport


class ConfigValidator:
    def parse(self, raw: str | dict[str, Any] | AppConfig) -> tuple[AppConfig | None, ValidationReport]:
        if isinstance(raw, AppConfig):
            return raw, ValidationReport(status="passed")
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError as exc:
            return None, ValidationReport(status="failed", errors=[self.issue("INVALID_JSON", str(exc), "json")])
        try:
            return AppConfig.model_validate(payload), ValidationReport(status="passed")
        except ValidationError as exc:
            return None, ValidationReport(
                status="failed",
                errors=[self.issue("SCHEMA_VALIDATION_ERROR", error["msg"], ".".join(str(p) for p in error["loc"])) for error in exc.errors()],
            )

    def validate(self, config: AppConfig) -> ValidationReport:
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        endpoints = {(e.method, e.path): e for e in config.api.endpoints}
        endpoints_by_path = {e.path: e for e in config.api.endpoints}
        tables = {t.name: t for t in config.database.tables}
        entities = {e.name: e for e in config.entities}
        roles = {r.name for r in config.auth.roles}
        permissions = {p.name: p for p in config.auth.permissions}

        for section in ["app", "assumptions", "entities", "ui", "api", "database", "auth", "business_logic", "validation", "execution"]:
            if not hasattr(config, section):
                errors.append(self.issue("MISSING_TOP_LEVEL_SECTION", f"Missing top-level section {section}.", section))

        route_counts = Counter(page.route for page in config.ui.pages)
        for route, count in route_counts.items():
            if count > 1:
                errors.append(self.issue("DUPLICATE_PAGE_ROUTE", f"Duplicate page route {route}.", f"ui.pages.{route}"))

        endpoint_counts = Counter((endpoint.method, endpoint.path) for endpoint in config.api.endpoints)
        for (method, path), count in endpoint_counts.items():
            if count > 1:
                errors.append(self.issue("DUPLICATE_API_ENDPOINT", f"Duplicate endpoint {method} {path}.", f"api.endpoints.{path}"))

        table_counts = Counter(table.name for table in config.database.tables)
        for table, count in table_counts.items():
            if count > 1:
                errors.append(self.issue("DUPLICATE_DB_TABLE", f"Duplicate table {table}.", f"database.tables.{table}"))

        for table in config.database.tables:
            if not any(column.primary_key for column in table.columns):
                errors.append(self.issue("DB_TABLE_MISSING_PRIMARY_KEY", f"Table {table.name} has no primary key.", f"database.tables.{table.name}"))
            if any(column.name == "password" for column in table.columns):
                errors.append(self.issue("PLAIN_PASSWORD_STORAGE", f"Table {table.name} stores plain password.", f"database.tables.{table.name}.password"))

        for relationship in config.database.relationships:
            if relationship.from_table not in tables or relationship.to_table not in tables:
                errors.append(self.issue("RELATIONSHIP_REFERENCES_MISSING_TABLE", f"Relationship {relationship.from_table}->{relationship.to_table} references missing table.", "database.relationships"))
                continue
            if relationship.field not in {column.name for column in tables[relationship.from_table].columns}:
                errors.append(self.issue("RELATIONSHIP_MISSING_FIELD", f"Relationship field {relationship.field} missing from {relationship.from_table}.", "database.relationships"))

        for page in config.ui.pages:
            for role in page.required_roles:
                if role not in roles:
                    errors.append(self.issue("MISSING_ROLE", f"Page {page.route} references missing role {role}.", f"ui.pages.{page.route}"))
            for permission in page.required_permissions:
                if permission not in permissions:
                    errors.append(self.issue("MISSING_PERMISSION", f"Page {page.route} references missing permission {permission}.", f"ui.pages.{page.route}"))
            if "admin" in page.route and "admin" not in page.required_roles:
                errors.append(self.issue("ADMIN_PAGE_WITHOUT_ADMIN_ROLE", f"Admin page {page.route} must require admin role.", f"ui.pages.{page.route}"))
            if "analytics" in page.route and "read:analytics" not in page.required_permissions:
                errors.append(self.issue("ANALYTICS_PERMISSION_MISSING", f"Analytics page {page.route} must require read:analytics.", f"ui.pages.{page.route}"))
            if ("payment" in page.route or "billing" in page.route) and not ({"manage:billing", "read:payment"} & set(page.required_permissions)):
                errors.append(self.issue("PAYMENT_PERMISSION_MISSING", f"Payment page {page.route} needs billing/payment permission.", f"ui.pages.{page.route}"))
            if page.premium_required and "use:premium" not in page.required_permissions:
                errors.append(self.issue("PREMIUM_PERMISSION_MISSING", f"Premium page {page.route} must require use:premium.", f"ui.pages.{page.route}"))
            for component in page.components:
                if component.entity and component.entity not in entities and component.entity != "user":
                    errors.append(self.issue("UI_COMPONENT_ENTITY_MISSING", f"Component {component.name} references missing entity {component.entity}.", f"ui.pages.{page.route}"))
            for form in page.forms:
                if form.entity not in entities and form.entity != "user":
                    errors.append(self.issue("UI_FORM_ENTITY_MISSING", f"Form {form.name} references missing entity {form.entity}.", f"ui.pages.{page.route}"))
                if form.submit_endpoint not in endpoints_by_path:
                    expected_path = f"/api/{form.entity.replace('_', '-') + 's'}" if form.entity != "user" else "/api/auth/login"
                    code = "INVALID_FORM_ENDPOINT" if "invalid" in form.submit_endpoint or form.submit_endpoint != expected_path else "MISSING_API_ENDPOINT"
                    errors.append(self.issue(code, f"Form {form.name} submits to missing endpoint {form.submit_endpoint}.", f"ui.pages.{page.route}.forms.{form.name}"))

        for endpoint in config.api.endpoints:
            if endpoint.entity not in entities and endpoint.entity != "user":
                errors.append(self.issue("API_ENTITY_MISSING", f"Endpoint {endpoint.path} references missing entity {endpoint.entity}.", f"api.endpoints.{endpoint.path}"))
            if endpoint.table not in tables:
                errors.append(self.issue("MISSING_DB_TABLE", f"Endpoint {endpoint.path} references missing table {endpoint.table}.", f"api.endpoints.{endpoint.path}"))
                continue
            table_columns = {column.name for column in tables[endpoint.table].columns}
            for field in endpoint.body_fields:
                if field not in table_columns and field not in endpoint.computed_fields:
                    errors.append(self.issue("API_BODY_FIELD_MISSING_DB_COLUMN", f"Endpoint {endpoint.path} body field {field} missing from table {endpoint.table}.", f"api.endpoints.{endpoint.path}.{field}"))
            for field in endpoint.computed_fields:
                entity = entities.get(endpoint.entity)
                if entity and field not in {f.name for f in entity.fields} and not (endpoint.name == "login" and field == "password"):
                    errors.append(self.issue("API_COMPUTED_FIELD_INVALID", f"Computed field {field} is not declared for entity {endpoint.entity}.", f"api.endpoints.{endpoint.path}.{field}"))
            for role in endpoint.required_roles:
                if role not in roles:
                    errors.append(self.issue("MISSING_ROLE", f"Endpoint {endpoint.path} references missing role {role}.", f"api.endpoints.{endpoint.path}"))
            for permission in endpoint.required_permissions:
                if permission not in permissions:
                    errors.append(self.issue("MISSING_PERMISSION", f"Endpoint {endpoint.path} references missing permission {permission}.", f"api.endpoints.{endpoint.path}"))

        for permission in config.auth.permissions:
            for role in permission.roles:
                if role not in roles:
                    errors.append(self.issue("PERMISSION_REFERENCES_MISSING_ROLE", f"Permission {permission.name} references missing role {role}.", f"auth.permissions.{permission.name}"))

        if any(page.premium_required for page in config.ui.pages) and not any("premium" in rule.name or "use:premium" in rule.expression for rule in config.business_logic):
            errors.append(self.issue("PREMIUM_RULE_MISSING", "Premium pages require premium gating business rule.", "business_logic"))
        if any("analytics" in page.route for page in config.ui.pages) and not any("analytics" in rule.name for rule in config.business_logic):
            errors.append(self.issue("ADMIN_ANALYTICS_RULE_MISSING", "Analytics pages require admin analytics business rule.", "business_logic"))
        if any(page.required_roles or page.required_permissions for page in config.ui.pages) and not any("role" in rule.name for rule in config.business_logic):
            errors.append(self.issue("ROLE_ACCESS_RULE_MISSING", "Role-protected pages require role access business logic.", "business_logic"))
        if not any(endpoint.path == "/api/auth/login" and endpoint.table == "users" for endpoint in config.api.endpoints) or "users" not in tables:
            errors.append(self.issue("LOGIN_API_USERS_TABLE_MISSING", "Login API and users table are required.", "api.auth"))

        referenced_entities = set()
        for page in config.ui.pages:
            referenced_entities.update(c.entity for c in page.components if c.entity)
            referenced_entities.update(f.entity for f in page.forms)
        referenced_entities.update(e.entity for e in config.api.endpoints)
        referenced_entities.update(t.entity for t in config.database.tables)
        for entity in entities:
            if entity not in referenced_entities:
                warnings.append(ValidationIssue(code="ORPHAN_ENTITY", message=f"Entity {entity} is not connected to runtime surfaces.", location=f"entities.{entity}", severity="warning", repairable=True))

        return ValidationReport(status="failed" if errors else "passed", errors=errors, warnings=warnings)

    def issue(self, code: str, message: str, location: str) -> ValidationIssue:
        return ValidationIssue(code=code, message=message, location=location, severity="error", repairable=True)
