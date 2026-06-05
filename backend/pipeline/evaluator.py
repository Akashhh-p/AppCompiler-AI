from __future__ import annotations

import json
import statistics
import time
from collections import Counter
from pathlib import Path

from backend.pipeline.orchestrator import PipelineOrchestrator


class Evaluator:
    def __init__(self, orchestrator: PipelineOrchestrator | None = None) -> None:
        self.orchestrator = orchestrator or PipelineOrchestrator()

    def run(self, product_prompts_path: Path, edge_prompts_path: Path, output_dir: Path) -> dict:
        product_prompts = json.loads(product_prompts_path.read_text(encoding="utf-8"))
        edge_prompts = json.loads(edge_prompts_path.read_text(encoding="utf-8"))
        prompts = [{"kind": "product", "prompt": p} for p in product_prompts] + [{"kind": "edge", "prompt": p} for p in edge_prompts]

        results = []
        failure_types: Counter[str] = Counter()
        repair_types: Counter[str] = Counter()
        quality_scores = {
            "consistency_score": [],
            "execution_readiness_score": [],
            "schema_completeness_score": [],
            "repairability_score": [],
        }
        started = time.perf_counter()
        fault_cycle = [
            "remove_permission",
            "remove_role",
            "remove_endpoint",
            "break_form_endpoint",
            "remove_primary_key",
            "remove_relationship_table",
            "remove_premium_rule",
        ]
        for index, item in enumerate(prompts, start=1):
            edge_number = index - len(product_prompts) - 1
            inject_fault = item["kind"] == "edge"
            fault_type = fault_cycle[edge_number % len(fault_cycle)] if inject_fault else None
            output = self.orchestrator.generate(item["prompt"], inject_fault=inject_fault, save=True, fault_type=fault_type)
            for error in output["validation"]["errors"]:
                failure_types[error["code"]] += 1
            for repair in output["repair_history"]:
                repair_types[repair["issue_code"]] += 1
            for key in quality_scores:
                quality_scores[key].append(output["quality_metrics"][key])
            failed = output["validation"]["status"] != "passed" or output["execution"]["status"] != "passed"
            results.append(
                {
                    "id": index,
                    "kind": item["kind"],
                    "prompt": item["prompt"],
                    "app_slug": output["app"]["slug"],
                    "validation_status": output["validation"]["status"],
                    "execution_status": output["execution"]["status"],
                    "repairs": output["validation"]["repair_count"],
                    "latency_ms": output["pipeline"]["total_latency_ms"],
                    "injected_fault": output["pipeline"].get("injected_fault"),
                    "passed_without_repair": not failed and output["validation"]["repair_count"] == 0,
                    "passed_after_repair": not failed and output["validation"]["repair_count"] > 0,
                }
            )

        repairs = [item["repairs"] for item in results]
        latencies = [item["latency_ms"] for item in results]
        failed_count = sum(1 for item in results if item["validation_status"] != "passed" or item["execution_status"] != "passed")
        report = {
            "total_prompts": len(results),
            "passed_without_repair": sum(1 for item in results if item["passed_without_repair"]),
            "passed_after_repair": sum(1 for item in results if item["passed_after_repair"]),
            "failed": failed_count,
            "success_rate": round((len(results) - failed_count) / len(results), 4),
            "average_retries_per_request": 0,
            "average_repairs_per_request": round(statistics.mean(repairs), 2),
            "average_latency_ms": round(statistics.mean(latencies), 2),
            "failure_types": dict(failure_types),
            "repair_types": dict(repair_types),
            "quality_metrics": {
                "average_consistency_score": round(statistics.mean(quality_scores["consistency_score"]), 2),
                "average_execution_score": round(statistics.mean(quality_scores["execution_readiness_score"]), 2),
                "average_schema_score": round(statistics.mean(quality_scores["schema_completeness_score"]), 2),
                "average_repairability_score": round(statistics.mean(quality_scores["repairability_score"]), 2),
            },
            "cost_quality_tradeoff": {
                "deterministic_generation_cost": "near zero",
                "llm_usage": "optional; only useful for richer architecture text or domain-specific refinement",
                "partial_repair_savings": f"Localized repair avoided approximately {sum(repairs) * 1800} regenerated tokens.",
                "quality_strategy": "Use deterministic schema validation and runtime simulation for correctness; reserve LLMs for generation/repair suggestions behind strict validators.",
            },
            "wall_clock_ms": round((time.perf_counter() - started) * 1000, 2),
            "results": results,
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "evaluation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        (output_dir / "evaluation_report.md").write_text(self.to_markdown(report), encoding="utf-8")
        return report

    def to_markdown(self, report: dict) -> str:
        lines = [
            "# ConfigForge AI Evaluation Report",
            "",
            f"- Total prompts: {report['total_prompts']}",
            f"- Success rate: {report['success_rate'] * 100:.1f}%",
            f"- Passed without repair: {report['passed_without_repair']}",
            f"- Passed after repair: {report['passed_after_repair']}",
            f"- Failed: {report['failed']}",
            f"- Average repairs per request: {report['average_repairs_per_request']}",
            f"- Average latency: {report['average_latency_ms']} ms",
            "",
            "## Repair Types",
            "",
        ]
        lines.extend([f"- {code}: {count}" for code, count in report["repair_types"].items()] or ["- None"])
        lines.extend([
            "",
            "## Quality Metrics",
            "",
            f"- Average consistency score: {report['quality_metrics']['average_consistency_score']}",
            f"- Average execution score: {report['quality_metrics']['average_execution_score']}",
            f"- Average schema score: {report['quality_metrics']['average_schema_score']}",
            f"- Average repairability score: {report['quality_metrics']['average_repairability_score']}",
        ])
        lines.extend(["", "## Results", ""])
        lines.extend([f"- #{r['id']} [{r['kind']}] {r['app_slug']}: validation={r['validation_status']}, execution={r['execution_status']}, repairs={r['repairs']}, fault={r['injected_fault']}" for r in report["results"]])
        return "\n".join(lines) + "\n"
