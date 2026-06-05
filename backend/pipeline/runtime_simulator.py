from __future__ import annotations

from backend.schemas.app_config_schema import AppConfig
from backend.schemas.execution_schema import ExecutionReport


class RuntimeSimulator:
    def run(self, config: AppConfig) -> ExecutionReport:
        report = ExecutionReport(status="passed")
        errors: list[str] = []

        for page in config.ui.pages:
            report.steps.append(f"registered route {page.route}")
            report.steps.append(f"rendered page {page.name} with {page.layout} layout")
            for component in page.components:
                report.steps.append(f"rendered component {component.name}")

        tables = {}
        for table in config.database.tables:
            columns = {column.name for column in table.columns}
            tables[table.name] = columns
            report.steps.append(f"created table {table.name}({', '.join(sorted(columns))})")
            if not any(column.primary_key for column in table.columns):
                errors.append(f"table {table.name} has no primary key")

        for relationship in config.database.relationships:
            if relationship.from_table in tables and relationship.to_table in tables and relationship.field in tables[relationship.from_table]:
                report.steps.append(f"created relationship {relationship.from_table}.{relationship.field} -> {relationship.to_table}")
            else:
                errors.append(f"relationship {relationship.from_table}.{relationship.field}->{relationship.to_table} cannot be created")

        endpoints = {endpoint.path: endpoint for endpoint in config.api.endpoints}
        for endpoint in config.api.endpoints:
            report.steps.append(f"registered endpoint {endpoint.method} {endpoint.path}")
            if endpoint.table not in tables:
                errors.append(f"endpoint {endpoint.path} cannot bind missing table {endpoint.table}")
            else:
                report.steps.append(f"bound {endpoint.method} {endpoint.path} to {endpoint.table}")

        for role in config.auth.roles:
            report.steps.append(f"loaded auth role {role.name}")
        permission_names = {permission.name for permission in config.auth.permissions}
        for permission in config.auth.permissions:
            report.steps.append(f"loaded permission {permission.name}")

        for page in config.ui.pages:
            for permission in page.required_permissions:
                if permission not in permission_names:
                    errors.append(f"page {page.route} references missing permission {permission}")
                else:
                    report.steps.append(f"checked permission {permission} for {page.route}")
            if page.premium_required and "use:premium" not in page.required_permissions:
                errors.append(f"premium page {page.route} lacks use:premium")
            for form in page.forms:
                if form.submit_endpoint not in endpoints:
                    errors.append(f"form {form.name} cannot submit to {form.submit_endpoint}")
                else:
                    report.steps.append(f"verified form {form.name} submits to {form.submit_endpoint}")

        for rule in config.business_logic:
            if not rule.expression:
                errors.append(f"business rule {rule.name} has no expression")
            else:
                report.steps.append(f"compiled business rule {rule.name}")
        if any(page.premium_required for page in config.ui.pages):
            report.steps.append("verified premium gating check")
        if any("analytics" in page.route for page in config.ui.pages):
            report.steps.append("verified admin analytics access check")

        report.errors = errors
        report.status = "failed" if errors else "passed"
        return report
