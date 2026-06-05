from __future__ import annotations

import re

from backend.pipeline.naming import title
from backend.schemas.intent_schema import IntentModel


DOMAIN_LIBRARY = {
    "crm": ("crm", ["contact", "company", "deal", "activity"], ["dashboard", "contacts", "deals"]),
    "e-commerce": ("ecommerce", ["product", "cart", "order", "payment"], ["storefront", "cart", "checkout"]),
    "ecommerce": ("ecommerce", ["product", "cart", "order", "payment"], ["storefront", "cart", "checkout"]),
    "hospital": ("hospital_management", ["doctor", "patient", "appointment", "prescription"], ["appointments", "patients"]),
    "school": ("school_erp", ["student", "teacher", "attendance", "exam", "fee"], ["attendance", "exams", "fees"]),
    "college": ("school_erp", ["student", "teacher", "attendance", "exam", "fee"], ["attendance", "exams", "fees"]),
    "inventory": ("inventory_management", ["product", "supplier", "purchase_order", "stock_alert"], ["inventory", "stock alerts"]),
    "food delivery": ("food_delivery", ["restaurant", "menu_item", "cart", "order", "delivery"], ["menus", "delivery tracking"]),
    "job portal": ("job_portal", ["candidate", "recruiter", "job_post", "application"], ["jobs", "applications"]),
    "booking": ("booking_system", ["customer", "booking", "resource"], ["booking calendar"]),
    "finance": ("finance_tracker", ["account", "transaction", "budget"], ["budgets", "reports"]),
    "lms": ("learning_management", ["course", "lesson", "quiz", "progress", "certificate"], ["courses", "progress"]),
    "learning": ("learning_management", ["course", "lesson", "quiz", "progress", "certificate"], ["courses", "progress"]),
    "project": ("project_management", ["team", "task", "comment", "file"], ["tasks", "deadlines"]),
    "real estate": ("real_estate", ["property", "lead", "agent", "viewing"], ["properties", "viewings"]),
    "event": ("event_management", ["venue", "ticket", "payment", "check_in"], ["tickets", "check-in"]),
    "saas": ("saas_dashboard", ["workspace", "subscription", "metric"], ["dashboard", "billing"]),
}


ROLE_KEYWORDS = ["admin", "manager", "receptionist", "doctor", "teacher", "student", "warehouse", "recruiter", "candidate", "organizer", "instructor", "seller", "agent"]


class IntentExtractor:
    def run(self, user_prompt: str) -> IntentModel:
        text = user_prompt.strip()
        lower = re.sub(r"\s+", " ", text.lower())

        app_type = "business_app"
        domain = "generic_business"
        entities: list[str] = []
        features: list[str] = []
        for keyword, (mapped_domain, mapped_entities, mapped_features) in DOMAIN_LIBRARY.items():
            if keyword in lower:
                app_type = mapped_domain
                domain = mapped_domain
                entities.extend(mapped_entities)
                features.extend(mapped_features)

        if not entities:
            entities = ["workspace", "record"]
            features.extend(["dashboard", "records"])

        roles = ["user"]
        for role in ROLE_KEYWORDS:
            if role in lower:
                roles.append(role)

        auth_required = not any(phrase in lower for phrase in ["no login", "no authentication", "remove all authentication", "without login"])
        role_requested = any(word in lower for word in ["role", "admin", "permission", "only admins", "manager", "receptionist"])
        if role_requested:
            auth_required = True

        payments_required = any(word in lower for word in ["payment", "payments", "billing", "fees", "checkout"])
        analytics_required = any(word in lower for word in ["analytics", "dashboard", "reports", "metrics"])
        premium_required = any(word in lower for word in ["premium", "subscription", "paid plan", "plan"])
        crud_required = not any(phrase in lower for phrase in ["read only", "view only"])

        ambiguities: list[str] = []
        conflicts: list[str] = []
        missing_details: list[str] = []
        assumptions: list[str] = []

        if len(lower.split()) < 5 or lower in {"build an app", "build app", "app"}:
            ambiguities.append("Prompt is vague and does not specify a domain.")
            missing_details.extend(["target users", "core entities", "access rules"])
            assumptions.append("Inferred a generic business management app with login, dashboard, records, and CRUD workflows.")
        if "only admins can edit" in lower and "all users can edit" in lower:
            conflicts.append("Edit access is conflicting: admin-only edit and all-user edit were both requested.")
            assumptions.append("Chose safer rule: destructive and edit operations require admin or manager permissions.")
        if payments_required and not auth_required:
            conflicts.append("Payments were requested while authentication was disabled.")
            assumptions.append("Enabled authentication because payments require user identity and auditability.")
            auth_required = True
        if "no database" in lower:
            conflicts.append("A software app was requested while database persistence was disabled.")
            assumptions.append("Generated a database schema anyway because runtime simulation requires executable persistence contracts.")
        if premium_required and not payments_required:
            missing_details.append("Premium plan requested without explicit billing/payment details.")
            assumptions.append("Added billing and subscription defaults for premium gating.")
            payments_required = True

        if payments_required:
            for entity in ["payment", "subscription"]:
                if entity not in entities:
                    entities.append(entity)
            features.append("payments")
        if analytics_required:
            features.append("analytics")
            if "analytics_event" not in entities:
                entities.append("analytics_event")

        return IntentModel(
            app_type=app_type,
            domain=domain,
            primary_goal=text or f"Build a {title(domain)} application.",
            features=list(dict.fromkeys(features)),
            requested_entities=list(dict.fromkeys(entities)),
            requested_roles=list(dict.fromkeys(roles)),
            auth_required=auth_required,
            payments_required=payments_required,
            analytics_required=analytics_required,
            premium_required=premium_required,
            crud_required=crud_required,
            ambiguities=ambiguities,
            conflicts=conflicts,
            missing_details=list(dict.fromkeys(missing_details)),
            assumptions=assumptions,
        )
