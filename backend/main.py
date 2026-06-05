from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from backend.pipeline.evaluator import Evaluator
from backend.pipeline.orchestrator import PipelineOrchestrator


ROOT = Path(__file__).resolve().parents[1]
orchestrator = PipelineOrchestrator(output_dir=ROOT / "outputs" / "generated_configs")
app = FastAPI(title="ConfigForge AI", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class GenerateRequest(BaseModel):
    prompt: str


@app.get("/")
def web_app() -> FileResponse:
    return FileResponse(ROOT / "frontend" / "index.html")


@app.get("/favicon.ico")
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ConfigForge AI", "mode": "deterministic"}


@app.post("/generate")
def generate(request: GenerateRequest, inject_fault: bool = Query(default=False)) -> dict:
    return orchestrator.generate(request.prompt, inject_fault=inject_fault, save=True)


@app.post("/evaluate")
def evaluate() -> dict:
    evaluator = Evaluator(orchestrator)
    return evaluator.run(ROOT / "backend" / "tests" / "product_prompts.json", ROOT / "backend" / "tests" / "edge_case_prompts.json", ROOT / "outputs")


@app.get("/sample-prompts")
def sample_prompts() -> dict:
    return {
        "product": json.loads((ROOT / "backend" / "tests" / "product_prompts.json").read_text(encoding="utf-8")),
        "edge_cases": json.loads((ROOT / "backend" / "tests" / "edge_case_prompts.json").read_text(encoding="utf-8")),
    }


@app.get("/sample")
def sample() -> dict:
    prompt = "Build a CRM with login, contacts, deals, dashboard, role-based access, premium plan with payments. Admins can see analytics."
    return orchestrator.generate(prompt, save=True)
