# Evaluation

## Dataset

`src/app/evaluation/datasets/representative.jsonl` includes direct contradictions, unsupported claims, corrections, metaphors, subjective disagreement, and a neutral case. The representative conversation contains no personal, company, brand, or place names. Extend the JSONL with positive examples, negative examples, ambiguous cases, and cases whose correct outcome is no finding.

`src/app/evaluation/datasets/heldout.jsonl` is a separate, content-hashed holdout with positive and negative probes for the same boundaries, including direct conflicts, corrections, time changes, selective presentation, reasoning errors, metaphor, questions, and unsupported claims. Keep its conversations and labels fixed for any later comparison; changing an ask changes the `t-<sha256>` test version.

`src/app/evaluation/datasets/heldout_500.jsonl` is a larger diagnostic holdout generated reproducibly by `python src/app/evaluation/datasets/build_heldout_500.py`. It contains the original 33 cases plus 467 synthetic cases across claim, contradiction, context, misrepresentation, reasoning, semantic, uncertainty, and negative-control families. Several cases share templates, so 500 rows must not be interpreted as 500 independent real-world conversations. The current offline system is deterministic; a baseline with fewer than 50 failure-capable asks is not suitable for a version comparison or training decision, even if the row count is 500.

Each row has an `id`, a raw `conversation`, `expected_categories`, and an optional note. Categories cover claim extraction, contradiction detection, factual verification, misrepresentation detection, nonsense detection, logical coherence, semantic coherence, context awareness, evidence grounding, and uncertainty calibration.

## Metrics

`app.evaluation.metrics.binary_metrics()` reports accuracy, precision, recall, F1, false-positive rate, and false-negative rate, with the confusion counts and support. Undefined denominators produce zero rather than an exception; inspect support when comparing categories.

The `Evaluator` runs each case through the full orchestrator. When `whileai` is installed, it also sends local binary result rows to the documented `whileai.pass_at()` API. The While SDK score is an additional pass-rate view; the project metrics remain the source for category-level precision and recall. No While account, API key, or network call is needed for this local scoring path.

`python -m app.evaluation.while_report` runs the deterministic offline pipeline three times and reports exact category-set accuracy plus one program-graded behavior for each category. It uses ask-level pass@1 intervals, reports failed cases, measures the repeated-run noise floor, and estimates the holdout size for a five-point effect. The 33-case holdout is diagnostic and intentionally does not claim release-level power or independent human agreement. The While coverage-gap probe compares the old representative suite with the analysis rules documented by this repository; it is a design aid because the offline agent has no tool schemas or single system prompt.

After signing in with `wai login`, `python -m app.evaluation.while_report --track` posts one `eval` baseline to While. Pass `--dataset src/app/evaluation/datasets/heldout_500.jsonl` to post the larger diagnostic set. The question is recorded before the run, all categories are graded by a deterministic program, scores use points, failed rows and one interval chart are attached, and the runner reads the result back with `readback(tracked)`. It sends the synthetic held-out conversations and labels as eval rows; do not put private conversations in this dataset.

## Testing and reproducibility

Run the test suite with `uv run --extra dev pytest`. Run the While eval locally with `uv run python -m app.evaluation.while_report`; add `--track` only when signed in and ready to post the baseline. The same fixture conversation is used by the orchestrator integration test. Tests cover exact wording, message references, contradictory and corrected statements, unavailable evidence, misleading scope, nonsense versus metaphor, fallacies, and neutral cases. Dataset labels and model settings should be versioned alongside reported results.

The default checks are heuristic and deterministic, not a benchmark of language-model truthfulness. Results can change when provider/model versions or prompts change. Report the provider and dataset version with any external comparison. A result from a small dataset is not a general reliability guarantee.
