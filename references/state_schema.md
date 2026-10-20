# Dialogue State Schema

The state is a serializable JSON object. It is the source of truth between turns; prose transcripts are output, not policy state.

## Top-level fields

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | State format version. Current version is `1.0`. |
| `objective` | string | The concrete outcome the conversation must achieve. Required. |
| `language` | string | BCP 47-like language tag such as `en` or `zh-CN`. |
| `phase` | string | `collect`, `test`, or `conclude`. |
| `stop_requested` | boolean | Immediately forces a `finish` action when true. |
| `required_facts` | array | Mandatory information needed for a defensible conclusion. |
| `hypotheses` | array | Mutually exclusive candidate answers and their evidence scores. |
| `observations` | array | Calibrated measurements supplied by another validated component. |
| `turns` | array | User and assistant utterances with optional metadata. |
| `action_history` | array | Selected dialogue moves, used to detect repetition. |
| `policy` | object | Thresholds and stopping rules. |

## Required fact

```json
{
  "id": "deadline",
  "description": "the required delivery date",
  "critical": true,
  "status": "unknown",
  "attempts": 0
}
```

Allowed `status` values are `unknown`, `partial`, `known`, and `conflict`. Increment `attempts` after asking for the fact. A critical fact with status other than `known` blocks a confident conclusion.

## Hypothesis

```json
{"id": "fast", "label": "express delivery", "score": 0.34}
```

- Scores must be in `[0, 1]` and should be normalized across hypotheses.
- Update scores only from recorded evidence, never from rhetorical style.
- Do not store hidden chain-of-thought in a hypothesis label or observation.

## Observation

```json
{
  "id": "obs_004",
  "source": "validated_component_name",
  "fact_id": "deadline",
  "contradiction": 0.2,
  "quality": 0.91,
  "created_at": "2026-01-01T12:00:00Z"
}
```

`contradiction` is an optional calibrated value in `[0, 1]`. Raw emotion, tone, facial movement, or speech style must not be relabeled as deception. If a signal is not calibrated on representative data, leave it out of the policy.

## Policy defaults

| Key | Default | Effect |
|---|---:|---|
| `max_turns` | 12 | Stops the dialogue after this many user turns. |
| `max_attempts_per_fact` | 2 | Moves on after repeated unsuccessful probing. |
| `max_repeated_actions` | 2 | Prevents asking the same action/target indefinitely. |
| `min_hypothesis_score` | 0.72 | Required score for a confident summary. |
| `min_hypothesis_margin` | 0.20 | Required gap between the top two hypotheses. |
| `contradiction_threshold` | 0.65 | Triggers verification of competing hypotheses. |
| `min_evidence_items` | 2 | Minimum observation count before summary. |

Tune these only against held-out evaluation data. Do not lower thresholds merely to improve apparent completion rate.

## Update invariants

1. Every conclusion must point to a `required_facts` entry or recorded observation.
2. A new user answer updates the relevant fact and evidence, not just the transcript.
3. A summary cannot introduce a fact that is absent from state.
4. A `finish` action must preserve unresolved uncertainty in the final utterance.
5. PII and raw media belong outside this state object unless a separate retention policy explicitly permits storage.
