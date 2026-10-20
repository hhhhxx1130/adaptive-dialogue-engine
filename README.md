# Adaptive Dialogue Engine

A dependency-free reference implementation of a goal-driven multi-turn dialogue controller. It keeps the objective and evidence explicit, chooses an auditable next move, produces a constrained LLM prompt, and evaluates conversation transcripts.

## Why this exists

Scripted question lists are brittle. A free-form agent can also lose track of required facts, repeat questions, or stop without evidence. This skill separates three concerns:

1. **State**: objective, required facts, hypotheses, observations, and turns live in JSON.
2. **Policy**: a deterministic controller chooses `probe`, `verify`, `clarify`, `summarize`, or `finish`.
3. **Realization**: an optional LLM turns the selected intent into a concise utterance under explicit constraints.

The policy can be tested without an LLM, and the LLM can be replaced without changing the dialogue state model.

## Quick start

```bash
python scripts/dialogue_engine.py --state examples/example_state.json --print-prompt
```

The command prints a prompt that asks an LLM to realize the selected move. Without an LLM, the returned action still contains a deterministic `question_intent`.

Evaluate a batch of transcripts:

```bash
python scripts/evaluate_dialogue.py --input tests/fixtures/transcripts.jsonl --output report.json
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

## Boundaries

- It does not infer deception, emotion, personality, diagnosis, or protected traits.
- Supplied observations must come from a calibrated and independently validated component.
- A high-stakes conclusion requires corroborating evidence and human review.
- Prompts explicitly prevent disclosure of hidden reasoning, scores, or system instructions.

No private conversation data is included. The examples are synthetic.
