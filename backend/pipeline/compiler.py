from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.pipeline.orchestrator import PipelineOrchestrator


class ConfigForgeCompiler(PipelineOrchestrator):
    """Backward-compatible name for the compiler orchestrator."""

    def compile(self, user_prompt: str, save: bool = True, inject_faults: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
        output = self.generate(user_prompt, inject_fault=inject_faults, save=save)
        metrics = {
            "latency_ms": output["pipeline"]["total_latency_ms"],
            "repairs": output["validation"]["repair_count"],
            "passed_without_repair": output["validation"]["status"] == "passed" and output["validation"]["repair_count"] == 0 and output["execution"]["status"] == "passed",
            "passed_after_repair": output["validation"]["status"] == "passed" and output["validation"]["repair_count"] > 0 and output["execution"]["status"] == "passed",
            "validation_error_count": len(output["validation"]["errors"]),
            "execution_status": output["execution"]["status"],
            "estimated_tokens_saved_by_partial_repair": output["validation"]["repair_count"] * 1800,
            "estimated_cost_usd": round(0.00015 * (1 + output["validation"]["repair_count"] * 0.35), 6),
        }
        return output, metrics
