import json
from typing import Any


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def json_repair_prompt(
    prior_output: str,
    errors: str,
    shape: object,
    constraints: str,
) -> str:
    return (
        "Repair the prior JSON response. Preserve supported content, correct only the listed errors, "
        "and return JSON only. Do not introduce new facts.\n\n"
        "EXPECTED SHAPE:\n" + compact_json(shape)
        + "\n\nCONSTRAINTS:\n" + constraints
        + "\n\nERRORS:\n" + errors
        + "\n\nPRIOR OUTPUT:\n" + prior_output
    )