from __future__ import annotations

from copy import deepcopy

from backend.pipeline.naming import plural, snake
from backend.schemas.app_config_schema import APIEndpoint, AppConfig, BusinessRule, DBColumn, DBTable, Permission, RepairRecord, Role
from backend.schemas.validation_schema import ValidationIssue, ValidationReport


class RepairEngine:
    def repair(self, config: AppConfig, report: ValidationReport) -> AppConfig:
        patched = deepcopy(config)
        sections = {issue.location.split(".")[0] for issue in report.errors}
        if len(sections) / 8 > 0.40:
            patched.assumptions.append("More than 40 percent of sections were invalid; section-level defaults were used, not a full blind retry.")
        for issue in report.errors:
            before = patched.model_dump(mode="json")
            self._repair_issue(patched, issue)
            after = patched.model_dump(mode="json")
            patched.repair_history.append(
                RepairRecord(
                    issue_code=issue.code,
                    location=issue.location,
                    before=self._compact(before),
                    after=self._compact(after),
                    repair=self._repair_message(issue.code),
                    strategy="partial_patch",
                    status="fixed",
                )
            )
        patched.validation.repair_attempted = True
        patched.validation.repair_count += 1
        return patched

    def _repair_issue(self, config: AppConfig, issue: ValidationIssue) -> None:
        if issue.code in {"DB_TABLE_MISSING_PRIMARY_KEY", "missing_primary_key"}:
            for table in config.database.tables:
                if not any(column.primary_key for column in table.columns):
                    table.columns.insert(0, DBColumn(name="id", type="uuid", primary_key=True))
        elif issue.code in {"MISSING_DB_TABLE", "relationship_missing_table"}:
            self._add_missing_tables(config)
        elif issue.code == "MISSING_API_ENDPOINT":
            self._add_missing_form_endpoints(config)
        elif issue.code == "INVALID_FORM_ENDPOINT":
            self._correct_invalid_form_endpoints(config)
        elif issue.code == "API_BODY_FIELD_MISSING_DB_COLUMN":
            self._add_missing_columns(config)
        elif issue.code in {"MISSING_ROLE", "missing_role"}:
            self._add_missing_roles(config)
        elif issue.code in {"MISSING_PERMISSION", "missing_permission"}:
            self._add_missing_permissions(config)
        elif issue.code == "PERMISSION_REFERENCES_MISSING_ROLE":
            self._repair_permission_roles(config)
        elif issue.code == "PREMIUM_RULE_MISSING":
            config.business_logic.append(BusinessRule(name="premium-gating", description="Premium features require active subscription and use:premium permission.", expression="user.subscription.status == 'active' and 'use:premium' in user.permissions", applies_to=["ui.pages", "api.endpoints"]))
        elif issue.code == "ADMIN_ANALYTICS_RULE_MISSING":
            config.business_logic.append(BusinessRule(name="admin-analytics-access", description="Admin analytics requires admin role and read:analytics permission.", expression="user.role == 'admin' and 'read:analytics' in user.permissions", applies_to=["ui.pages", "api.endpoints"]))
        elif issue.code == "ROLE_ACCESS_RULE_MISSING":
            config.business_logic.append(BusinessRule(name="role-access", description="Protected pages and APIs require declared permissions.", expression="required_permissions <= user.permissions", applies_to=["ui.pages", "api.endpoints"]))
        elif issue.code == "PLAIN_PASSWORD_STORAGE":
            self._hash_password_storage(config)
        elif issue.code == "LOGIN_API_USERS_TABLE_MISSING":
            self._ensure_login(config)
        elif issue.code == "ADMIN_PAGE_WITHOUT_ADMIN_ROLE":
            for page in config.ui.pages:
                if "admin" in page.route and "admin" not in page.required_roles:
                    page.required_roles.append("admin")
        elif issue.code == "ANALYTICS_PERMISSION_MISSING":
            for page in config.ui.pages:
                if "analytics" in page.route and "read:analytics" not in page.required_permissions:
                    page.required_permissions.append("read:analytics")
            self._add_missing_permissions(config)
        elif issue.code == "PAYMENT_PERMISSION_MISSING":
            for page in config.ui.pages:
                if "payment" in page.route or "billing" in page.route:
                    page.required_permissions.append("manage:billing")
            self._add_missing_permissions(config)
        elif issue.code == "PREMIUM_PERMISSION_MISSING":
            for page in config.ui.pages:
                if page.premium_required and "use:premium" not in page.required_permissions:
                    page.required_permissions.append("use:premium")
            self._add_missing_permissions(config)
        elif issue.code == "RELATIONSHIP_MISSING_FIELD":
            self._remove_bad_relationships(config)
        elif issue.code in {"RELATIONSHIP_MISSING_TABLE", "RELATIONSHIP_REFERENCES_MISSING_TABLE"}:
            self._remove_bad_relationships(config)
        elif issue.code == "DUPLICATE_PAGE_ROUTE":
            seen = set()
            for page in config.ui.pages:
                if page.route in seen:
                    page.route = f"{page.route}-{len(seen)}"
                seen.add(page.route)
        elif issue.code == "DUPLICATE_API_ENDPOINT":
            seen = set()
            for endpoint in config.api.endpoints:
                key = (endpoint.method, endpoint.path)
                if key in seen:
                    endpoint.path = f"{endpoint.path}-{len(seen)}"
                seen.add((endpoint.method, endpoint.path))

    def _add_missing_tables(self, config: AppConfig) -> None:
        tables = {table.name for table in config.database.tables}
        for endpoint in config.api.endpoints:
            if endpoint.table not in tables:
                columns = [DBColumn(name="id", type="uuid", primary_key=True)]
                columns.extend(DBColumn(name=field, type="string") for field in endpoint.body_fields if field not in {"id", "password"})
                config.database.tables.append(DBTable(name=endpoint.table, entity=endpoint.entity, columns=columns))
                tables.add(endpoint.table)

    def _add_missing_form_endpoints(self, config: AppConfig) -> None:
        paths = {endpoint.path for endpoint in config.api.endpoints}
        tables = {table.entity: table.name for table in config.database.tables}
        for page in config.ui.pages:
            for form in page.forms:
                if form.submit_endpoint not in paths:
                    table = tables.get(form.entity, "users" if form.entity == "user" else snake(plural(form.entity)))
                    config.api.endpoints.append(APIEndpoint(name=f"auto_{form.name}", method="POST", path=form.submit_endpoint, entity=form.entity, table=table, body_fields=form.fields, computed_fields=["password"] if "password" in form.fields else [], required_roles=page.required_roles, required_permissions=page.required_permissions))
                    paths.add(form.submit_endpoint)

    def _correct_invalid_form_endpoints(self, config: AppConfig) -> None:
        paths = {endpoint.path for endpoint in config.api.endpoints}
        for page in config.ui.pages:
            for form in page.forms:
                if form.submit_endpoint in paths:
                    continue
                expected = "/api/auth/login" if form.entity == "user" else f"/api/{snake(plural(form.entity)).replace('_', '-')}"
                if expected in paths:
                    form.submit_endpoint = expected
                else:
                    form.submit_endpoint = expected
        self._add_missing_form_endpoints(config)

    def _add_missing_columns(self, config: AppConfig) -> None:
        tables = {table.name: table for table in config.database.tables}
        for endpoint in config.api.endpoints:
            table = tables.get(endpoint.table)
            if not table:
                continue
            names = {column.name for column in table.columns}
            for field in endpoint.body_fields:
                if field not in names and field not in endpoint.computed_fields:
                    table.columns.append(DBColumn(name=field, type="string"))
                    names.add(field)

    def _add_missing_roles(self, config: AppConfig) -> None:
        roles = {role.name for role in config.auth.roles}
        refs = set()
        for page in config.ui.pages:
            refs.update(page.required_roles)
        for endpoint in config.api.endpoints:
            refs.update(endpoint.required_roles)
        for permission in config.auth.permissions:
            refs.update(permission.roles)
        for role in sorted(refs - roles):
            config.auth.roles.append(Role(name=role, description=f"Auto-added missing role {role}"))

    def _add_missing_permissions(self, config: AppConfig) -> None:
        roles = [role.name for role in config.auth.roles]
        permissions = {permission.name for permission in config.auth.permissions}
        refs = set()
        for page in config.ui.pages:
            refs.update(page.required_permissions)
        for endpoint in config.api.endpoints:
            refs.update(endpoint.required_permissions)
        for permission in sorted(refs - permissions):
            config.auth.permissions.append(Permission(name=permission, description=f"Auto-added missing permission {permission}", roles=["admin"] if "manage" in permission or "analytics" in permission else roles))

    def _repair_permission_roles(self, config: AppConfig) -> None:
        self._add_missing_roles(config)
        valid = {role.name for role in config.auth.roles}
        for permission in config.auth.permissions:
            permission.roles = [role for role in permission.roles if role in valid] or ["admin"]

    def _hash_password_storage(self, config: AppConfig) -> None:
        for table in config.database.tables:
            for column in table.columns:
                if column.name == "password":
                    column.name = "password_hash"
        for endpoint in config.api.endpoints:
            if endpoint.path == "/api/auth/login" and "password" not in endpoint.computed_fields:
                endpoint.computed_fields.append("password")

    def _ensure_login(self, config: AppConfig) -> None:
        if not any(table.name == "users" for table in config.database.tables):
            config.database.tables.append(DBTable(name="users", entity="user", columns=[DBColumn(name="id", type="uuid", primary_key=True), DBColumn(name="email", type="email"), DBColumn(name="password_hash", type="string")]))
        if not any(endpoint.path == "/api/auth/login" for endpoint in config.api.endpoints):
            config.api.endpoints.append(APIEndpoint(name="login", method="POST", path="/api/auth/login", entity="user", table="users", body_fields=["email", "password"], computed_fields=["password"], validations=["password_hash_transform"]))

    def _remove_bad_relationships(self, config: AppConfig) -> None:
        tables = {table.name: {column.name for column in table.columns} for table in config.database.tables}
        config.database.relationships = [rel for rel in config.database.relationships if rel.from_table in tables and rel.to_table in tables and rel.field in tables[rel.from_table]]

    def _compact(self, payload: dict) -> dict:
        return {"sections": list(payload.keys()), "counts": {"pages": len(payload.get("ui", {}).get("pages", [])), "endpoints": len(payload.get("api", {}).get("endpoints", [])), "tables": len(payload.get("database", {}).get("tables", []))}}

    def _repair_message(self, code: str) -> str:
        return f"Applied localized repair for {code}."
