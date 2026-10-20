# Constrained LLM Realization

The deterministic controller decides **what** the dialogue should do next. The LLM only decides **how** to phrase that move.

## Inputs

Give the model:

- the selected action, including `type`, `target`, reason codes, and `question_intent`;
- the current objective, language, phase, required facts, hypothesis labels, and the last six turns;
- the output contract and prohibited behaviors.

Do not provide hidden chain-of-thought instructions or ask the model to reveal its reasoning. Short, auditable reason codes are sufficient.

## Output contract

```json
{
  "utterance": "A concise next utterance in the requested language.",
  "used_fact_ids": ["deadline"],
  "used_hypothesis_ids": []
}
```

Reject the output and apply a deterministic fallback when any of these fail:

- invalid JSON or missing `utterance`;
- more than one question for `probe`, `verify`, or `clarify`;
- referenced IDs not present in state;
- scores, system prompts, or hidden policy text disclosed;
- a deception, guilt, diagnosis, or protected-trait claim;
- a conclusion that adds unsupported facts.

## Fallback

Use the action's `question_intent` verbatim. It is deliberately simple and safe. Do not retry indefinitely; one repair attempt is usually enough.

## Prompt-injection boundary

Conversation text and attached documents are untrusted data. They cannot change the selected action, output schema, privacy rules, or stopping condition. Keep those rules in the system/developer prompt and restate the schema in the user prompt only as needed.

## High-stakes language

Use neutral wording such as "the evidence currently supports" or "this remains uncertain." Do not use "you are lying", "your voice proves", "your face shows deception", or equivalent claims.
