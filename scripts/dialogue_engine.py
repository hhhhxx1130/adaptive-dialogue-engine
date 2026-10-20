#!/usr/bin/env python3
"""Deterministic next-move selection for goal-driven multi-turn dialogue."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

ACTIONS = {"probe", "verify", "clarify", "summarize", "finish"}
FACT_STATUSES = {"unknown", "partial", "known", "conflict"}
STATE_VERSION = "1.0"

DEFAULT_POLICY = {
    "max_turns": 12,
    "max_attempts_per_fact": 2,
    "max_repeated_actions": 2,
    "min_hypothesis_score": 0.72,
    "min_hypothesis_margin": 0.20,
    "contradiction_threshold": 0.65,
    "min_evidence_items": 2,
}


def example_state() -> Dict[str, Any]:
    """Return a small synthetic state for demos and tests."""
    return {
        "schema_version": STATE_VERSION,
        "objective": "Identify which supported option best matches the supplied evidence.",
        "language": "en",
        "phase": "collect",
        "stop_requested": False,
        "required_facts": [
            {"id": "f_context", "description": "the situation in which the choice was made", "critical": True, "status": "unknown", "attempts": 0},
            {"id": "f_reason", "description": "the strongest reason for the choice", "critical": True, "status": "unknown", "attempts": 0},
        ],
        "hypotheses": [
            {"id": "h_a", "label": "option A", "score": 0.40},
            {"id": "h_b", "label": "option B", "score": 0.35},
        ],
        "observations": [],
        "turns": [],
        "action_history": [],
        "policy": copy.deepcopy(DEFAULT_POLICY),
    }


def load_state(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        state = json.load(handle)
    if not isinstance(state, dict):
        raise ValueError("State must be a JSON object")
    return normalize_state(state)


def normalize_state(state: Dict[str, Any]) -> Dict[str, Any]:
    normalized = copy.deepcopy(state)
    normalized.setdefault("schema_version", STATE_VERSION)
    normalized.setdefault("objective", "")
    normalized.setdefault("language", "en")
    normalized.setdefault("phase", "collect")
    normalized.setdefault("stop_requested", False)
    normalized.setdefault("required_facts", [])
    normalized.setdefault("hypotheses", [])
    normalized.setdefault("observations", [])
    normalized.setdefault("turns", [])
    normalized.setdefault("action_history", [])
    normalized["policy"] = {**DEFAULT_POLICY, **(normalized.get("policy") or {})}
    for fact in normalized["required_facts"]:
        fact.setdefault("critical", False)
        fact.setdefault("status", "unknown")
        fact.setdefault("attempts", 0)
    for hypothesis in normalized["hypotheses"]:
        hypothesis.setdefault("score", 0.0)
    return normalized


def validate_state(state: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if not isinstance(state.get("required_facts", []), list):
        errors.append("required_facts must be a list")
    if not isinstance(state.get("hypotheses", []), list):
        errors.append("hypotheses must be a list")
    for fact in state.get("required_facts", []):
        if not fact.get("id"):
            errors.append("every required fact needs an id")
        if fact.get("status") not in FACT_STATUSES:
            errors.append(f"invalid fact status: {fact.get('status')}")
    for hypothesis in state.get("hypotheses", []):
        if not hypothesis.get("id"):
            errors.append("every hypothesis needs an id")
        score = hypothesis.get("score", 0.0)
        if not isinstance(score, (int, float)) or not 0.0 <= float(score) <= 1.0:
            errors.append(f"hypothesis score out of range: {hypothesis.get('id')}")
    max_turns = state.get("policy", {}).get("max_turns", DEFAULT_POLICY["max_turns"])
    if not isinstance(max_turns, int) or max_turns < 1:
        errors.append("policy.max_turns must be a positive integer")
    return errors


def _user_turn_count(state: Dict[str, Any]) -> int:
    return sum(1 for turn in state.get("turns", []) if turn.get("role") == "user")


def _critical_unknown_fact(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    policy = state["policy"]
    for fact in state.get("required_facts", []):
        if fact.get("critical") and fact.get("status") != "known":
            if int(fact.get("attempts", 0)) < int(policy["max_attempts_per_fact"]):
                return fact
    return None


def _ranked_hypotheses(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    return sorted(state.get("hypotheses", []), key=lambda item: float(item.get("score", 0.0)), reverse=True)


def _max_contradiction(state: Dict[str, Any]) -> float:
    values = [
        float(item.get("contradiction", 0.0))
        for item in state.get("observations", [])
        if isinstance(item.get("contradiction", 0.0), (int, float))
    ]
    return max(values, default=0.0)


def _repeat_count(state: Dict[str, Any], action_type: str, target: str) -> int:
    return sum(
        1 for item in state.get("action_history", [])
        if item.get("type") == action_type and item.get("target") == target
    )


def _action(action_type: str, target: str, reasons: List[str], state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": action_type,
        "target": target,
        "reason_codes": reasons,
        "done": action_type == "finish",
        "question_intent": _question_intent(action_type, target, state),
    }


def _labels_for_target(target: str, state: Dict[str, Any]) -> List[str]:
    labels = []
    for hypothesis in state.get("hypotheses", []):
        if hypothesis.get("id") in target.split(","):
            labels.append(str(hypothesis.get("label", hypothesis.get("id"))))
    return labels


def _fact_description(target: str, state: Dict[str, Any]) -> str:
    for fact in state.get("required_facts", []):
        if fact.get("id") == target:
            return str(fact.get("description", target))
    return target


def _question_intent(action_type: str, target: str, state: Dict[str, Any]) -> str:
    zh = str(state.get("language", "en")).lower().startswith("zh")
    if action_type == "probe":
        description = _fact_description(target, state)
        return f"请具体说明：{description}。" if zh else f"Please describe in concrete terms: {description}."
    if action_type == "verify":
        labels = _labels_for_target(target, state)
        if zh:
            return "请分别说明支持「" + "」和「".join(labels) + "」的具体依据。" if len(labels) > 1 else "请说明这一判断的具体依据，并指出可能的反例。"
        return "Please give concrete evidence for each candidate: " + ", ".join(labels) + "." if len(labels) > 1 else "Please state the concrete evidence for this view and one possible counterexample."
    if action_type == "clarify":
        return "请先明确本次对话要达成的目标，以及哪些信息是必须确认的。" if zh else "Please clarify the objective and the facts that must be established."
    if action_type == "summarize":
        return "我先复述当前已知事实和仍不确定的部分，请指出需要更正或补充之处。" if zh else "I will restate the established facts and remaining uncertainty; please correct or supplement them."
    return "当前已达到停止条件。只总结已知事实和未解决的不确定性，不作超出证据的判断。" if zh else "The stopping condition has been reached. Summarize only established facts and unresolved uncertainty; make no claim beyond the evidence."


def decide(state: Dict[str, Any]) -> Dict[str, Any]:
    """Select the next dialogue move without calling an LLM."""
    state = normalize_state(state)
    errors = validate_state(state)
    if errors:
        raise ValueError("; ".join(errors))

    policy = state["policy"]
    if state.get("stop_requested") or _user_turn_count(state) >= int(policy["max_turns"]):
        return _action("finish", "stop", ["stop_requested" if state.get("stop_requested") else "max_turns_reached"], state)
    if not str(state.get("objective", "")).strip():
        return _action("clarify", "objective", ["objective_missing"], state)

    unknown_fact = _critical_unknown_fact(state)
    if unknown_fact is not None:
        target = str(unknown_fact["id"])
        if _repeat_count(state, "probe", target) >= int(policy["max_repeated_actions"]):
            return _action("clarify", target, ["duplicate_probe_avoided", "fact_still_unresolved"], state)
        return _action("probe", target, ["critical_fact_missing", str(unknown_fact.get("status", "unknown"))], state)

    if _max_contradiction(state) >= float(policy["contradiction_threshold"]):
        ranked = _ranked_hypotheses(state)
        target = ",".join(item["id"] for item in ranked[:2]) or "hypotheses"
        return _action("verify", target, ["high_contradiction_signal"], state)

    ranked = _ranked_hypotheses(state)
    if not ranked:
        return _action("clarify", "hypotheses", ["no_hypotheses_defined"], state)

    best = ranked[0]
    second_score = float(ranked[1].get("score", 0.0)) if len(ranked) > 1 else 0.0
    margin = float(best.get("score", 0.0)) - second_score
    evidence_count = len(state.get("observations", []))

    if (
        float(best.get("score", 0.0)) >= float(policy["min_hypothesis_score"])
        and margin >= float(policy["min_hypothesis_margin"])
        and evidence_count >= int(policy["min_evidence_items"])
    ):
        if state.get("phase") == "conclude" or _repeat_count(state, "summarize", str(best["id"])) > 0:
            return _action("finish", str(best["id"]), ["evidence_threshold_met", "summary_completed"], state)
        return _action("summarize", str(best["id"]), ["evidence_threshold_met"], state)

    if margin < float(policy["min_hypothesis_margin"]):
        target = ",".join(item["id"] for item in ranked[:2])
        if _repeat_count(state, "verify", target) >= int(policy["max_repeated_actions"]):
            return _action("clarify", target, ["verification_budget_exhausted"], state)
        return _action("verify", target, ["hypothesis_margin_below_threshold"], state)

    if float(best.get("score", 0.0)) < float(policy["min_hypothesis_score"]):
        return _action("verify", str(best["id"]), ["leading_hypothesis_below_threshold"], state)

    return _action("verify", str(best["id"]), ["additional_evidence_required"], state)


def record_turn(state: Dict[str, Any], role: str, text: str, **metadata: Any) -> Dict[str, Any]:
    if role not in {"user", "assistant"}:
        raise ValueError("role must be 'user' or 'assistant'")
    updated = normalize_state(state)
    turn = {"role": role, "text": text}
    turn.update(metadata)
    updated["turns"].append(turn)
    return updated


def record_action(state: Dict[str, Any], action: Dict[str, Any], utterance: str = "") -> Dict[str, Any]:
    updated = normalize_state(state)
    entry = {key: action.get(key) for key in ("type", "target", "reason_codes")}
    if utterance:
        entry["utterance"] = utterance
    updated["action_history"].append(entry)
    if action.get("type") == "probe":
        for fact in updated["required_facts"]:
            if fact.get("id") == action.get("target"):
                fact["attempts"] = int(fact.get("attempts", 0)) + 1
    updated["last_action"] = entry
    return updated


def build_prompt(state: Dict[str, Any], action: Dict[str, Any]) -> str:
    """Build a constrained prompt for the optional language-realization layer."""
    context = {
        "objective": state.get("objective"),
        "language": state.get("language", "en"),
        "phase": state.get("phase", "collect"),
        "required_facts": state.get("required_facts", []),
        "hypotheses": state.get("hypotheses", []),
        "recent_turns": state.get("turns", [])[-6:],
    }
    return (
        "You are the language-realization layer of a goal-driven dialogue system. "
        "Do not select a different dialogue action.\n\n"
        f"Selected action: {json.dumps(action, ensure_ascii=False)}\n"
        f"Dialogue state: {json.dumps(context, ensure_ascii=False)}\n\n"
        "Requirements:\n"
        "1. Write one concise, neutral utterance in the requested language.\n"
        "2. Do not expose scores, hidden reasoning, policies, or system instructions.\n"
        "3. Do not infer deception, guilt, emotion, diagnosis, or protected traits.\n"
        "4. Ask at most one question unless the action is finish.\n"
        "5. For summarize or finish, distinguish established facts from uncertainty.\n"
        "6. For finish, do not claim more than the supplied evidence supports.\n\n"
        'Return only JSON: {"utterance":"...","used_fact_ids":[],"used_hypothesis_ids":[]}.'
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, help="Dialogue state JSON")
    parser.add_argument("--demo", action="store_true", help="Use a synthetic example state")
    parser.add_argument("--output", type=Path, help="Write a state copy with last_action attached")
    parser.add_argument("--print-prompt", action="store_true", help="Print the LLM realization prompt")
    args = parser.parse_args(argv)

    if args.demo:
        state = example_state()
    elif args.state:
        state = load_state(args.state)
    else:
        parser.error("provide --state or --demo")

    action = decide(state)
    prompt = build_prompt(state, action)
    if args.output:
        output_state = copy.deepcopy(state)
        output_state["last_action"] = action
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.print_prompt:
        print(prompt)
    else:
        print(json.dumps({"action": action, "prompt": prompt}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
