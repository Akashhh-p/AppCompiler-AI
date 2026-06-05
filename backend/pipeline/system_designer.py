from __future__ import annotations

from backend.pipeline.naming import plural, title
from backend.schemas.design_schema import DesignEntity, SystemDesign
from backend.schemas.intent_schema import IntentModel


DEFAULT_FIELDS = {
    "contact": ["id", "name", "email", "company_id", "owner_id", "created_at"],
    "company": ["id", "name", "domain", "created_at"],
    "deal": ["id", "title", "amount", "stage", "contact_id", "owner_id", "created_at"],
    "doctor": ["id", "name", "specialty", "email", "created_at"],
    "patient": ["id", "name", "email", "phone", "created_at"],
    "appointment": ["id", "doctor_id", "patient_id", "scheduled_at", "status", "created_at"],
    "prescription": ["id", "appointment_id", "notes", "created_at"],
    "student": ["id", "name", "email", "grade", "created_at"],
    "teacher": ["id", "name", "email", "subject", "created_at"],
    "attendance": ["id", "student_id", "status", "recorded_at"],
    "exam": ["id", "name", "scheduled_at", "created_at"],
    "fee": ["id", "student_id", "amount", "status", "created_at"],
    "product": ["id", "name", "sku", "price", "stock", "created_at"],
    "supplier": ["id", "name", "email", "created_at"],
    "purchase_order": ["id", "supplier_id", "status", "total_amount", "created_at"],
    "stock_alert": ["id", "product_id", "threshold", "active", "created_at"],
    "payment": ["id", "subscription_id", "amount", "status", "created_at"],
    "subscription": ["id", "user_id", "plan", "status", "renewal_at"],
    "analytics_event": ["id", "event_name", "actor_id", "created_at"],
}


class SystemDesigner:
    def run(self, intent: IntentModel) -> SystemDesign:
        entities = [
            DesignEntity(
                name=entity,
                description=f"{title(entity)} records used by the {intent.domain} app.",
                fields=DEFAULT_FIELDS.get(entity, ["id", "name", "description", "owner_id", "created_at"]),
            )
            for entity in intent.requested_entities
        ]
        roles = list(dict.fromkeys(intent.requested_roles + (["admin"] if intent.analytics_required else [])))
        modules = ["ui", "api", "database", "auth", "validation", "runtime_simulation"]
        if intent.payments_required:
            modules.append("billing")
        if intent.analytics_required:
            modules.append("analytics")

        access_model = {
            "default_read_roles": roles,
            "write_roles": ["admin", "manager"] if intent.conflicts else roles,
            "admin_only": ["analytics", "user_management"],
            "premium_requires": "active subscription" if intent.premium_required else None,
        }
        flows = ["login", "dashboard"]
        flows.extend([f"manage {plural(entity.name)}" for entity in entities if entity.name not in {"analytics_event"}])
        if intent.payments_required:
            flows.append("billing and payment management")
        if intent.analytics_required:
            flows.append("admin analytics review")

        business_summary = "Role access, ownership checks, CRUD permissions, and audit-safe persistence."
        if intent.premium_required:
            business_summary += " Premium features require active subscription and use:premium permission."

        return SystemDesign(
            modules=list(dict.fromkeys(modules)),
            entities=entities,
            roles=roles,
            user_flows=flows,
            access_model=access_model,
            data_model_summary=f"{len(entities)} domain entities compiled into relational tables with inferred relationships.",
            business_rules_summary=business_summary,
            risk_notes=intent.conflicts + intent.ambiguities + intent.missing_details,
            app_name=self._app_name(intent),
            summary=intent.primary_goal,
            premium_required=intent.premium_required,
            analytics_required=intent.analytics_required,
            payments_required=intent.payments_required,
        )

    def _app_name(self, intent: IntentModel) -> str:
        if intent.domain == "crm":
            return "CRM Workspace"
        return f"{title(intent.domain)} Builder"
