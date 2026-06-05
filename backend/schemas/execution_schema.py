from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ExecutionReport(BaseModel):
    status: Literal["passed", "failed", "not_run"] = "not_run"
    steps: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
