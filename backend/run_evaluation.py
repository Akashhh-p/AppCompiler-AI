from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.pipeline.evaluator import Evaluator
from backend.pipeline.orchestrator import PipelineOrchestrator


if __name__ == "__main__":
    evaluator = Evaluator(PipelineOrchestrator(output_dir=ROOT / "outputs" / "generated_configs"))
    report = evaluator.run(ROOT / "backend" / "tests" / "product_prompts.json", ROOT / "backend" / "tests" / "edge_case_prompts.json", ROOT / "outputs")
    print(json.dumps({key: report[key] for key in ["total_prompts", "success_rate", "passed_without_repair", "passed_after_repair", "failed", "average_latency_ms"]}, indent=2))
