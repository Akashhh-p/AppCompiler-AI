from __future__ import annotations

import re


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-") or "generated-app"


def snake(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return re.sub(r"_+", "_", value).strip("_") or "item"


def title(value: str) -> str:
    return " ".join(part.capitalize() for part in re.split(r"[_\-\s]+", value) if part)


def plural(value: str) -> str:
    if value.endswith("y"):
        return f"{value[:-1]}ies"
    if value.endswith("s"):
        return value
    return f"{value}s"
