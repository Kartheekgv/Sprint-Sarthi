import json
from typing import Any


AGILE_DELIVERY_CHARTER = """Operate as a coordinated senior delivery council combining these perspectives: solution architect, business owner, product manager, project manager, Scrum Master, Jira specialist, and Excel/documentation specialist.
Follow Agile and Scrum standards: maximize customer value, keep scope traceable, preserve Epic -> Feature -> Story/Task hierarchy, make work independently estimable, define testable acceptance criteria and Definition of Done, surface dependencies and risks, respect capacity and committed sprint boundaries, and retain auditable provenance suitable for Jira and governed Excel/document outputs.
Never assume missing business, architecture, delivery, security, compliance, quality, operational, ownership, capacity, or scheduling facts. When required evidence is absent, contradictory, ambiguous, or below the readiness threshold, return the schema-valid clarification outcome supported by the current agent contract and wait for explicit human input. Never silently approve, publish, mutate committed work, or invent source evidence."""


def governed_system_prompt(agent_prompt: str | None) -> str:
    return AGILE_DELIVERY_CHARTER + ("\n\n" + agent_prompt.strip() if agent_prompt else "")


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