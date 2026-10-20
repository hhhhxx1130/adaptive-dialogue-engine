---
name: adaptive-dialogue-engine
description: Build and run a goal-driven multi-turn dialogue controller that maintains explicit state, selects the next move, generates a constrained LLM prompt, and evaluates transcripts. Use for structured interviews, coaching, requirements elicitation, or other conversations that must pursue missing facts without a rigid scripted question tree.
---

# Adaptive Dialogue Engine

Use this skill when a multi-turn conversation needs an explicit objective, auditable state, adaptive follow-up questions, and a deterministic stopping rule.

## Operating rules

1. Read `references/state_schema.md` before changing the state model.
2. Represent the objective, required facts, hypotheses, observations, and prior turns explicitly. Do not keep critical dialogue state only in prose.
3. Call `scripts/dialogue_engine.py` to select the next dialogue move. Do not replace the deterministic policy with an ad hoc question list.
4. Treat only calibrated, externally supplied signals as observations. Never infer deception, guilt, diagnosis, or a protected trait from wording, voice, face, or emotion.
5. Keep scores and policy reasoning internal. The user-facing utterance should be concise, neutral, and answerable.
6. Stop when the goal is satisfied, the maximum turn count is reached, or the user asks to stop. State unresolved uncertainty instead of inventing a conclusion.

## Workflow

1. Create a state object from the template in `examples/example_state.json`.
2. Put every mandatory datum in `required_facts` and every live candidate in `hypotheses`.
3. Run the controller to obtain the next action and a prompt for an LLM.
4. Record the assistant utterance, user answer, and any calibrated observations.
5. Update fact statuses and hypothesis scores from evidence, then run the controller again.
6. Use `scripts/evaluate_dialogue.py` on evaluation transcripts before enabling a conversational policy in production.

## Commands

```bash
python scripts/dialogue_engine.py --state examples/example_state.json --print-prompt
python scripts/dialogue_engine.py --state examples/example_state.json --output next_state.json
python scripts/evaluate_dialogue.py --input tests/fixtures/transcripts.jsonl --output report.json
```

The controller uses only the Python standard library. An LLM is optional: when present, give it the generated prompt and require the structured JSON response described in `references/prompting.md`.

## Safety and scope

This is a conversation-control component, not a lie detector or a clinical decision system. High-stakes actions must use independent, validated evidence and human review. Read `references/metrics.md` for evaluation requirements and `references/prompting.md` for the LLM boundary.

## Resource map

- `scripts/dialogue_engine.py`: state validation, action policy, question intent, and LLM prompt builder.
- `scripts/evaluate_dialogue.py`: offline transcript metrics.
- `references/state_schema.md`: state contract and update rules.
- `references/metrics.md`: production evaluation checklist.
- `references/prompting.md`: constrained generation contract.
- `tests/test_dialogue_engine.py`: deterministic policy and evaluator tests.
