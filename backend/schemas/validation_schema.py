from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    code: str
    message: str
    location: str = ""
    severity: Literal["error", "warning"] = "error"
    repairable: bool = True


class ValidationReport(BaseModel):
    status: Literal["passed", "failed", "not_run"] = "not_run"
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)
    repair_attempted: bool = False
    repair_count: int = 0
