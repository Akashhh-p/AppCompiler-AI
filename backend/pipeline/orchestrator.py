from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from backend.pipeline.intent_extractor import IntentExtractor
from backend.pipeline.refinement_layer import RefinementLayer
from backend.pipeline.repair_engine import RepairEngine
from backend.pipeline.runtime_simulator import RuntimeSimulator
from backend.pipeline.schema_generator import SchemaGenerator
from backend.pipeline.system_designer import SystemDesigner
from backend.pipeline.validator import ConfigValidator
from backend.schemas.app_config_schema import AppConfig, Relationship, model_to_jsonable


class PipelineOrchestrator:
    FAULT_TYPES = [
        "remove_permission",
        "remove_role",
        "remove_endpoint",
        "break_form_endpoint",
        "remove_primary_key",
        "remove_relationship_table",
        "remove_premium_rule",
    ]

    def __init__(self, output_dir: str | Path | None = None) -> None:
        self.intent_extractor = IntentExtractor()
        self.system_designer = SystemDesigner()
        self.schema_generator = SchemaGenerator()
        self.refinement_layer = RefinementLayer()
        self.validator = ConfigValidator()
        self.repair_engine = RepairEngine()
        self.runtime = RuntimeSimulator()
        self.output_dir = Path(output_dir or os.getenv("CONFIGFORGE_OUTPUT_DIR", "outputs/generated_configs"))

    def generate(self, prompt: str, inject_fault: bool = False, save: bool = True, fault_type: str | None = None) -> dict[str, Any]:
        pipeline_id = str(uuid.uuid5(uuid.NAMESPACE_URL, prompt.strip().lower()))
        started = time.perf_counter()
        stage_status: list[dict[str, Any]] = []

        intent = self._stage(stage_status, "intent_extraction", lambda: self.intent_extractor.run(prompt), "Extracted structured intent.")
        design = self._stage(stage_status, "system_design", lambda: self.system_designer.run(intent), "Designed config-driven architecture.")
        config = self._stage(stage_status, "schema_generation", lambda: self.schema_generator.run(design), "Generated strict app_config schema.")
        config = self._stage(stage_status, "refinement", lambda: self.refinement_layer.run(config), "Normalized permissions, deduped surfaces, and completed business rules.")
        injected_fault = self._inject_fault(config, pipeline_id, fault_type) if inject_fault else None

        validation_started = time.perf_counter()
        report = self.validator.validate(config)
        stage_status.append({"stage": "validation", "status": report.status, "latency_ms": self._elapsed(validation_started), "summary": f"{len(report.errors)} errors, {len(report.warnings)} warnings."})

        repair_started = time.perf_counter()
        repairs = 0
        while report.status == "failed" and repairs < 3:
            repairs += 1
            config.validation = report
            config = self.repair_engine.repair(config, report)
            report = self.validator.validate(config)
        report.repair_attempted = repairs > 0
        report.repair_count = repairs
        config.validation = report
        stage_status.append({"stage": "repair", "status": "skipped" if repairs == 0 else report.status, "latency_ms": self._elapsed(repair_started), "summary": "No repair needed." if repairs == 0 else f"Applied {repairs} localized repair pass(es)."})

        execution = self._stage(stage_status, "execution_simulation", lambda: self.runtime.run(config), "Simulated routes, UI, API, DB, auth, permissions, and business rules.")
        config.execution = execution

        total_latency = round((time.perf_counter() - started) * 1000, 2)
        output = self._response(pipeline_id, prompt, stage_status, total_latency, intent, design, config, injected_fault)
        if save:
            self.save(output)
        return output

    def save(self, output: dict[str, Any]) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / f"{output['app']['slug']}.json"
        path.write_text(json.dumps(output, indent=2), encoding="utf-8")
        return path

    def _stage(self, status: list[dict[str, Any]], name: str, fn: Callable[[], Any], summary: str) -> Any:
        started = time.perf_counter()
        result = fn()
        result_status = getattr(result, "status", "passed")
        status.append({"stage": name, "status": result_status if result_status != "not_run" else "passed", "latency_ms": self._elapsed(started), "summary": summary})
        return result

    def _elapsed(self, started: float) -> float:
        return round((time.perf_counter() - started) * 1000, 2)

    def _inject_fault(self, config: AppConfig, pipeline_id: str, fault_type: str | None = None) -> str:
        selected = fault_type if fault_type in self.FAULT_TYPES else self.FAULT_TYPES[int(pipeline_id[0:2], 16) % len(self.FAULT_TYPES)]
        if selected == "remove_permission" and config.auth.permissions:
            referenced = {permission for page in config.ui.pages for permission in page.required_permissions}
            target = next((permission for permission in config.auth.permissions if permission.name in referenced), config.auth.permissions[0])
            config.auth.permissions = [permission for permission in config.auth.permissions if permission.name != target.name]
            return selected
        if selected == "remove_role" and config.auth.roles:
            referenced = {role for page in config.ui.pages for role in page.required_roles}
            target_name = next(iter(referenced), config.auth.roles[0].name)
            config.auth.roles = [role for role in config.auth.roles if role.name != target_name]
            return selected
        if selected == "remove_endpoint":
            form_paths = [form.submit_endpoint for page in config.ui.pages for form in page.forms]
            target_path = next((path for path in form_paths if path != "/api/auth/login"), form_paths[0] if form_paths else "")
            config.api.endpoints = [endpoint for endpoint in config.api.endpoints if endpoint.path != target_path]
            return selected
        if selected == "break_form_endpoint":
            for page in config.ui.pages:
                if page.forms:
                    page.forms[0].submit_endpoint = "/api/invalid-controlled-fault"
                    return selected
        if selected == "remove_primary_key" and config.database.tables:
            config.database.tables[0].columns = [column for column in config.database.tables[0].columns if not column.primary_key]
            return selected
        if selected == "remove_relationship_table":
            if not config.database.relationships and len(config.database.tables) >= 2:
                config.database.relationships.append(Relationship(from_table=config.database.tables[0].name, to_table="missing_fault_table", type="one_to_many", field=config.database.tables[0].columns[0].name))
            elif config.database.relationships:
                config.database.relationships[0].to_table = "missing_fault_table"
            return selected
        if selected == "remove_premium_rule":
            for page in config.ui.pages:
                if page.required_permissions:
                    page.premium_required = True
                    if "use:premium" not in page.required_permissions:
                        page.required_permissions.append("use:premium")
                    break
            config.business_logic = [rule for rule in config.business_logic if "premium" not in rule.name and "use:premium" not in rule.expression]
            return selected
        return "remove_primary_key"

    def _response(self, pipeline_id: str, prompt: str, stage_status: list[dict[str, Any]], total_latency: float, intent, design, config: AppConfig, injected_fault: str | None) -> dict[str, Any]:
        app = model_to_jsonable(config)
        quality = self._quality(config)
        return {
            "pipeline": {
                "id": pipeline_id,
                "input_prompt": prompt,
                "stage_status": stage_status,
                "total_latency_ms": total_latency,
                "deterministic_mode": True,
                "injected_fault": injected_fault,
            },
            "app": app["app"],
            "assumptions": app["assumptions"],
            "intent": intent.model_dump(mode="json"),
            "design": design.model_dump(mode="json"),
            "entities": app["entities"],
            "ui": app["ui"],
            "api": app["api"],
            "database": app["database"],
            "auth": app["auth"],
            "business_logic": app["business_logic"],
            "validation": app["validation"],
            "repair_history": app["repair_history"],
            "execution": app["execution"],
            "quality_metrics": quality,
        }

    def _quality(self, config: AppConfig) -> dict[str, int]:
        validation_ok = config.validation.status == "passed"
        execution_ok = config.execution.status == "passed"
        required_sections = all([config.entities, config.ui.pages, config.api.endpoints, config.database.tables, config.auth.roles, config.auth.permissions, config.business_logic])
        return {
            "consistency_score": 95 if validation_ok else 60,
            "execution_readiness_score": 96 if execution_ok else 55,
            "schema_completeness_score": 94 if required_sections else 65,
            "repairability_score": 92 if config.repair_history or validation_ok else 70,
        }
