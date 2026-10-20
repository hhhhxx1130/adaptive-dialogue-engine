from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dialogue_engine import (  # noqa: E402
    build_prompt,
    decide,
    example_state,
    normalize_state,
    record_action,
)
from evaluate_dialogue import evaluate, load_jsonl  # noqa: E402


class DialoguePolicyTests(unittest.TestCase):
    def test_missing_critical_fact_triggers_probe(self):
        action = decide(example_state())
        self.assertEqual(action["type"], "probe")
        self.assertEqual(action["target"], "f_context")

    def test_repeated_probe_is_replaced_by_clarification(self):
        state = example_state()
        state["action_history"] = [
            {"type": "probe", "target": "f_context"},
            {"type": "probe", "target": "f_context"},
        ]
        self.assertEqual(decide(state)["type"], "clarify")

    def test_margin_rule_requests_verification(self):
        state = example_state()
        for fact in state["required_facts"]:
            fact["status"] = "known"
        action = decide(state)
        self.assertEqual(action["type"], "verify")
        self.assertEqual(action["target"], "h_a,h_b")

    def test_confident_evidence_requests_summary_then_finish(self):
        state = example_state()
        for fact in state["required_facts"]:
            fact["status"] = "known"
        state["hypotheses"] = [
            {"id": "h_a", "label": "A", "score": 0.84},
            {"id": "h_b", "label": "B", "score": 0.16},
        ]
        state["observations"] = [{"id": "o1", "contradiction": 0.1}, {"id": "o2"}]
        self.assertEqual(decide(state)["type"], "summarize")
        state["phase"] = "conclude"
        self.assertEqual(decide(state)["type"], "finish")

    def test_stop_condition_and_objective_validation(self):
        state = example_state()
        state["objective"] = ""
        self.assertEqual(decide(state)["type"], "clarify")
        state = example_state()
        state["stop_requested"] = True
        self.assertEqual(decide(state)["type"], "finish")

    def test_record_action_increments_attempts(self):
        state = example_state()
        action = decide(state)
        updated = record_action(state, action, "Synthetic question")
        self.assertEqual(updated["required_facts"][0]["attempts"], 1)
        self.assertEqual(updated["action_history"][0]["type"], "probe")

    def test_prompt_exposes_contract_not_hidden_reasoning(self):
        state = example_state()
        prompt = build_prompt(state, decide(state))
        self.assertIn("Return only JSON", prompt)
        self.assertIn("Do not expose scores", prompt)
        self.assertNotIn("chain-of-thought", prompt.lower())

    def test_invalid_score_is_rejected(self):
        state = normalize_state(example_state())
        state["hypotheses"][0]["score"] = 1.4
        with self.assertRaises(ValueError):
            decide(state)


class EvaluatorTests(unittest.TestCase):
    def test_fixture_metrics(self):
        records = load_jsonl(ROOT / "tests" / "fixtures" / "transcripts.jsonl")
        report = evaluate(records)
        self.assertEqual(report["conversations"], 3)
        self.assertEqual(report["completion_rate"], 0.3333)
        self.assertEqual(report["average_turns"], 5.0)
        self.assertEqual(report["redundant_action_rate"], 0.2222)
        self.assertEqual(report["premature_stop_rate"], 0.3333)
        self.assertEqual(report["average_latency_ms"], 1016.67)

    def test_invalid_record_is_counted(self):
        report = evaluate([{"turns": "bad"}])
        self.assertEqual(report["conversations"], 0)
        self.assertEqual(report["invalid_records"], 1)


if __name__ == "__main__":
    unittest.main()
