from __future__ import annotations

import json
import re

from pydantic import ValidationError

from app.schemas.models import AgentAnswer
from app.tools.crm_tools import load_customers


class AgentOutputError(ValueError):
    pass


EVIDENCE_MARKERS = (
    "Ticket ",
    "Order ",
    "CRM note ",
    "Policy ",
    "policy ",
    "company_policy.md",
    "onboarding_playbook.md",
)


def parse_and_validate_agent_answer(raw_output: str) -> AgentAnswer:
    errors: list[str] = []
    for candidate in (_extract_json(raw_output), _repair_json_once(raw_output)):
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
            answer = AgentAnswer.model_validate(payload)
            validate_grounding(answer)
            return answer
        except (json.JSONDecodeError, ValidationError, AgentOutputError) as exc:
            errors.append(str(exc))
    raise AgentOutputError("; ".join(errors) or "No JSON object found in model output.")


def validate_grounding(answer: AgentAnswer) -> None:
    customers = load_customers()
    valid_names = set(customers["customer_name"].astype(str))
    customer_ids_by_name = {
        str(row["customer_name"]): str(row["customer_id"])
        for _, row in customers.iterrows()
    }

    for action in answer.actions:
        if action.customer_name not in valid_names:
            raise AgentOutputError(f"Unknown customer_name: {action.customer_name}")
        expected_id = customer_ids_by_name[action.customer_name]
        if action.customer_id != expected_id:
            raise AgentOutputError(
                f"Customer id/name mismatch for {action.customer_name}: {action.customer_id}"
            )
        if not action.evidence:
            raise AgentOutputError(f"Missing evidence for {action.customer_name}")
        if not any(_is_supported_evidence(item) for item in action.evidence):
            raise AgentOutputError(f"Unsupported evidence for {action.customer_name}")
        if action.recommended_action != "no_action" and not action.draft_message:
            raise AgentOutputError(f"Missing draft_message for {action.customer_name}")


def _is_supported_evidence(value: str) -> bool:
    return any(marker in value for marker in EVIDENCE_MARKERS)


def _extract_json(raw_output: str) -> str:
    text = raw_output.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return ""
    return text[start : end + 1]


def _repair_json_once(raw_output: str) -> str:
    candidate = _extract_json(raw_output)
    if not candidate:
        return ""
    repaired = candidate.strip()
    repaired = repaired.replace("\u201c", '"').replace("\u201d", '"')
    repaired = repaired.replace("\u2018", "'").replace("\u2019", "'")
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    return repaired
