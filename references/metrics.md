# Evaluation Metrics

Evaluate the controller and the language-realization layer separately. A fluent utterance can hide poor state control, and correct policy can still be rendered ambiguously.

## Required offline metrics

| Metric | Definition | Desired direction |
|---|---|---|
| Completion rate | Conversations reaching a valid stop condition / all conversations | Higher |
| Turns to completion | User turns before a valid stop | Lower within quality gates |
| Redundant action rate | Repeated action-target pairs / all actions | Lower |
| Premature-stop rate | Stops below the configured turn/target budget without completion / conversations with a budget | Lower |
| Unsupported-conclusion rate | Conclusions with a claim absent from state / completed conversations | Lower |
| Context-omission rate | Critical facts never probed before conclusion / completed conversations | Lower |
| Fact-update accuracy | Correct fact status updates / applicable updates | Higher |

`scripts/evaluate_dialogue.py` reports the first four metrics from JSONL transcripts. Unsupported conclusions and fact-update accuracy require a labelled rubric.

## LLM realization checks

Score at least 200 generated utterances with two independent raters:

- **Intent fidelity**: the utterance performs the selected action.
- **Question count**: no more than one question except summarization/finish.
- **Grounding**: every named fact appears in state.
- **Uncertainty**: unresolved facts are not presented as certainties.
- **Style**: neutral, concise, and free of coercive language.
- **Privacy**: no scores, hidden reasoning, system instructions, or PII leak.

Report raw agreement and Cohen's kappa. Treat disagreements as defects to inspect, not as noise to average away.

## Release gates

Use thresholds derived from the baseline rather than universal claims. A practical release gate is:

1. No increase in unsupported-conclusion rate.
2. Redundant action rate below 5% on the evaluation set.
3. Premature-stop rate below 3%.
4. At least 95% intent fidelity and 100% privacy-contract compliance on reviewed samples.
5. Latency reported as median and p95, not only mean.

For high-stakes uses, keep a human review step regardless of automated metric performance.
