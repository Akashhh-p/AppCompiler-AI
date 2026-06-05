from __future__ import annotations

from copy import deepcopy

from backend.schemas.app_config_schema import AppConfig, BusinessRule, Permission


class RefinementLayer:
    """Normalizes generated config before strict validation."""

    def run(self, config: AppConfig) -> AppConfig:
        refined = deepcopy(config)
        self._dedupe(refined)
        self._ensure_permission_definitions(refined)
        self._ensure_business_rules(refined)
        return refined

    def _dedupe(self, config: AppConfig) -> None:
        config.entities = list({entity.name: entity for entity in config.entities}.values())
        config.ui.pages = list({page.route: page for page in config.ui.pages}.values())
        config.api.endpoints = list({(endpoint.method, endpoint.path): endpoint for endpoint in config.api.endpoints}.values())
        config.database.tables = list({table.name: table for table in config.database.tables}.values())

    def _ensure_permission_definitions(self, config: AppConfig) -> None:
        roles = [role.name for role in config.auth.roles]
        permissions = {permission.name for permission in config.auth.permissions}
        referenced = set()
        for page in config.ui.pages:
            referenced.update(page.required_permissions)
        for endpoint in config.api.endpoints:
            referenced.update(endpoint.required_permissions)
        for permission in sorted(referenced - permissions):
            config.auth.permissions.append(Permission(name=permission, description=f"Auto-normalized permission {permission}", roles=["admin"] if "admin" in permission or "manage" in permission else roles))

    def _ensure_business_rules(self, config: AppConfig) -> None:
        names = {rule.name for rule in config.business_logic}
        if any(page.required_roles or page.required_permissions for page in config.ui.pages) and "role-access" not in names:
            config.business_logic.append(BusinessRule(name="role-access", description="Role access must be enforced for protected pages and APIs.", expression="required_permissions <= user.permissions", applies_to=["ui.pages", "api.endpoints"]))
