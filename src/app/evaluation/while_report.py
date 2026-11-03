"""Run VeritasAgent's frozen conversation eval locally or report one baseline to While."""

from __future__ import annotations

import argparse
import hashlib
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import whileai as wai
import whileai.simulations as simulations
from whileai.platform import (
    Behavior,
    Data,
    EvalSetup,
    Harness,
    Provenance,
    RunRecord,
    track,
)

from app.core.orchestrator import AnalysisOrchestrator
from app.evaluation.evaluator import (
    CaseEvaluation,
    EvaluationCase,
    EvaluationCategory,
    Evaluator,
    default_dataset_path,
)


AGENT_ID = "veritas-agent"
RELEASE = "0.1.0"
MODEL = "none"
K = 1
RERUNS = 3
HYPOTHESIS = (
    "The five-case representative suite misses important boundary cases; a broader holdout "
    "will expose false positives and missed conversation risks without external evidence."
)
METHOD = (
    "One deterministic offline pass per conversation; binary category agreement graded by a "
    "program; three identical reruns; no model, tools, or external evidence source."
)
MEASURE = (
    "Pass@1 and exact category accuracy in points, with a 95% ask-level interval, support, "
    "failure-capable asks, and run-to-run noise for each behavior."
)
DECIDE = (
    "Treat this as a diagnostic baseline. Keep the asks frozen; improve the set before any "
    "version comparison or training decision if it has fewer than 50 failure-capable asks."
)

POLICY = """\
Extract only individually testable factual assertions; exclude opinions, questions, hypotheticals,
jokes, metaphors, speculation, and creative language. Compare claims only for genuine conflicts;
exclude corrections, clarifications, different times, and different preferences. Verify only against
supplied evidence; use UNVERIFIED when sources are insufficient and do not infer intent. Surface
observable selective presentation and unsupported universal claims. Flag semantic absurdity without
mistaking unusual factual claims or creative language for nonsense. Explain unsupported causal
inferences, false dilemmas, hasty generalizations, and circular reasoning. Review the full context,
ground findings in cited material, and preserve uncertainty.
"""

BEHAVIORS: dict[EvaluationCategory | None, tuple[str, str]] = {
    None: (
        "classify_review_findings",
        "Exact set match across all labeled review categories for a conversation.",
    ),
    EvaluationCategory.CLAIM_EXTRACTION: (
        "extract_factual_claims",
        "Extract factual assertions while excluding questions, opinions, hypotheticals, and creative language.",
    ),
    EvaluationCategory.CONTRADICTION_DETECTION: (
        "detect_statement_conflicts",
        "Identify genuine conflicts about the same proposition, not corrections or different periods.",
    ),
    EvaluationCategory.FACTUAL_VERIFICATION: (
        "verify_claims_with_evidence",
        "Compare factual claims with available evidence and leave unsupported claims unverified.",
    ),
    EvaluationCategory.MISREPRESENTATION_DETECTION: (
        "flag_observable_misrepresentation",
        "Surface selective presentation and unsupported universal claims without inferring intent.",
    ),
    EvaluationCategory.NONSENSE_DETECTION: (
        "flag_semantic_absurdity",
        "Flag semantic absurdity and category errors while preserving interpretable unusual claims.",
    ),
    EvaluationCategory.LOGICAL_COHERENCE: (
        "assess_inference_validity",
        "Explain unsupported causal inferences, false dilemmas, hasty generalizations, and circular reasoning.",
    ),
    EvaluationCategory.SEMANTIC_COHERENCE: (
        "preserve_semantic_coherence",
        "Distinguish semantic absurdity from metaphor, fiction, and other interpretable language.",
    ),
    EvaluationCategory.CONTEXT_AWARENESS: (
        "apply_conversation_context",
        "Use corrections, time references, and the full conversation before labeling a conflict.",
    ),
    EvaluationCategory.EVIDENCE_GROUNDING: (
        "ground_findings_in_evidence",
        "Attach conversation or source evidence to each surfaced finding.",
    ),
    EvaluationCategory.UNCERTAINTY_CALIBRATION: (
        "express_uncertainty_when_unverified",
        "Keep claims without adequate evidence explicitly unverified and low confidence.",
    ),
}

SETTING = re.compile(r"(lr\d|\de-0\d|-s\d+\b|_s\d+$|_seed\d+|^h-[0-9a-f]{12}$|^v\d+$)")


def load_cases(path: str | Path) -> list[EvaluationCase]:
    cases = Evaluator.load_jsonl(path)
    ids = [case.id for case in cases]
    prompts = [case.conversation for case in cases]
    if not cases:
        raise ValueError(f"Evaluation dataset is empty: {path}")
    if len(ids) != len(set(ids)):
        raise ValueError("Evaluation case ids must be unique")
    if len(prompts) != len(set(prompts)):
        raise ValueError("Frozen evaluation conversations must be unique")
    return cases


def test_version(cases: Sequence[EvaluationCase]) -> str:
    asks = sorted(case.conversation for case in cases)
    return "t-" + hashlib.sha256("\n".join(asks).encode("utf-8")).hexdigest()[:8]


def _half_width(ci95: Sequence[float] | None, mean: float, n_asks: int) -> float:
    if ci95 and ci95[1] > ci95[0]:
        return (float(ci95[1]) - float(ci95[0])) / 2
    if mean not in (0.0, 1.0):
        raise ValueError(f"Unexpected zero-width interval for a non-boundary score: {mean}, {ci95}")
    return 1 - 0.025 ** (1 / n_asks)


def _score(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result = wai.pass_at(rows, k=K)
    mean = float(result.pass_at_1)
    n = int(result.n_groups)
    ci = _half_width(result.ci95, mean, n)
    return {
        "points": round(100 * mean, 1),
        "ci": round(100 * ci, 1),
        "n": n,
        "failure_capable": sum(value < 1 for value in result.per_task.values()),
        "pass_at_1": mean,
    }


def _gold(case: EvaluationCase) -> set[EvaluationCategory]:
    return set(case.expected_categories)


def _predicted(case: CaseEvaluation) -> set[EvaluationCategory]:
    return set(case.predicted_categories)


def _rows(
    cases: Sequence[EvaluationCase],
    evaluated: Sequence[CaseEvaluation],
    category: EvaluationCategory | None,
) -> list[dict[str, Any]]:
    evaluated_by_id = {item.case_id: item for item in evaluated}
    rows = []
    for case in cases:
        result = evaluated_by_id[case.id]
        gold, predicted = _gold(case), _predicted(result)
        expected = gold == predicted if category is None else (category in gold) == (category in predicted)
        expected_text = ", ".join(sorted(item.value for item in gold)) or "none"
        predicted_text = ", ".join(sorted(item.value for item in predicted)) or "none"
        rows.append(
            {
                "task_id": case.id,
                "reward": int(expected),
                "prompt": case.conversation,
                "reply": predicted_text,
                "ok": expected,
                "why": "matched the labeled categories" if expected else "category mismatch",
                "reference": expected_text,
                "detail": case.notes,
                "tags": {"case_id": case.id, "behavior": BEHAVIORS[category][0] if category else "all"},
            }
        )
    return rows


def _summarize(
    cases: Sequence[EvaluationCase], evaluated: Sequence[CaseEvaluation]
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    summaries: dict[str, dict[str, Any]] = {}
    rows_by_name: dict[str, list[dict[str, Any]]] = {}
    for category, (name, _description) in BEHAVIORS.items():
        rows = _rows(cases, evaluated, category)
        summaries[name] = _score(rows)
        rows_by_name[name] = rows
    return summaries, rows_by_name


def _coverage_report() -> str:
    old_cases = Evaluator.load_jsonl(default_dataset_path())
    gap = simulations.coverage_gap(
        [case.conversation for case in old_cases],
        tools=[],
        system_prompt=POLICY,
    )
    return simulations.format_coverage_gap(gap)


def _print_report(
    cases: Sequence[EvaluationCase],
    test: str,
    summaries: dict[str, dict[str, Any]],
    noise: dict[str, float],
    need: dict[str, Any],
    evaluated: Sequence[CaseEvaluation],
) -> None:
    exact = summaries[BEHAVIORS[None][0]]
    print(f"held-out test {test}: {len(cases)} conversations, k={K}")
    print(
        f"exact category accuracy {exact['points']} points (±{exact['ci']}, n={exact['n']}); "
        f"failure-capable asks {exact['failure_capable']}/{exact['n']}; "
        f"noise floor {noise[BEHAVIORS[None][0]]} points across {RERUNS} identical reruns"
    )
    print("behavior                          points   95% half-width   asks   failed")
    for name, _description in BEHAVIORS.values():
        item = summaries[name]
        print(
            f"{name:<32} {item['points']:>5.1f} {item['ci']:>14.1f} "
            f"{item['n']:>7} {item['failure_capable']:>7}"
        )
    print(
        f"asks to resolve a 5-point effect: {need.get('n_tasks')} "
        f"(current n={need.get('n_paired') or len(cases)}; source={need.get('sd_source')})"
    )
    mismatches = [
        (case, item)
        for case, item in zip(cases, evaluated, strict=True)
        if _gold(case) != _predicted(item)
    ]
    print(f"exact-label failures: {len(mismatches)}")
    for case, item in mismatches[:20]:
        expected = ", ".join(sorted(value.value for value in case.expected_categories)) or "none"
        actual = ", ".join(sorted(value.value for value in item.predicted_categories)) or "none"
        print(f"  {case.id}: expected [{expected}], predicted [{actual}]")


def _run_note(
    test: str,
    cases: Sequence[EvaluationCase],
    summary: dict[str, dict[str, Any]],
    noise: dict[str, float],
    evaluated: Sequence[CaseEvaluation],
    need: dict[str, Any],
) -> str:
    headline = summary[BEHAVIORS[None][0]]
    failures = [
        case.id
        for case, item in zip(cases, evaluated, strict=True)
        if _gold(case) != _predicted(item)
    ]
    failure_text = ", ".join(failures[:8]) if failures else "none"
    limit = "This is a diagnostic set, not a release-quality proof."
    reproduce = "`PYTHONPATH=src uv run python -m app.evaluation.while_report --track`"
    if len(cases) == 500:
        limit += " The 500 synthetic cases include templated scenario families and are not 500 independent real-world conversations."
        reproduce = (
            "`PYTHONPATH=src uv run python -m app.evaluation.while_report "
            "--dataset src/app/evaluation/datasets/heldout_500.jsonl --track`"
        )
    if headline["failure_capable"] < 50:
        limit += " Fewer than 50 failure-capable asks; add independently authored cases before a version comparison or training decision."
    return "\n".join(
        (
            f"Changed: Baseline only: ran {AGENT_ID} {RELEASE} with the deterministic offline pipeline on frozen test {test}; no model or external evidence source.",
            f"Moved: No earlier version compared; exact category accuracy {headline['points']} points (±{headline['ci']}) on {headline['n']} asks; noise floor {noise[BEHAVIORS[None][0]]} points across {RERUNS} identical reruns.",
            f"Why: {len(failures)} exact-label failures ({failure_text}); every behavior's failed rows are attached to its score.",
            f"Learned: This frozen set measures claim, contradiction, evidence, uncertainty, context, and reasoning boundaries; the single-run estimate points to {need.get('n_tasks')} asks for a 5-point effect (model-based; current n={need.get('n_paired') or len(cases)}). {limit}",
            f"Reproduce: {reproduce} (test {test}, package {AGENT_ID} {RELEASE}).",
        )
    )


def _readback(tracked: Any) -> list[str]:
    """Read the account as a teammate would; an empty list means no detected issues."""
    problems = []
    if tracked.experiment() is None:
        problems.append("no question posted: tracked.experiment(question=...)")
    for behavior in tracked.behaviors():
        if SETTING.search(behavior.name):
            problems.append(f"behavior {behavior.name!r} encodes a setting")
        if not (behavior.test_version or "").startswith("t-"):
            problems.append(f"behavior {behavior.name!r} has no content-hash test_version")
    pictured = {figure.run for figure in tracked.figures()}
    for run in tracked.runs():
        version = run["version"]
        note = run.get("notes") or ""
        if SETTING.search(version):
            problems.append(f"version {version!r} encodes a setting")
        if not (run.get("record") or {}).get("data"):
            problems.append(f"run {version!r} has no RunRecord data")
        for word in ("Changed", "Moved", "Why", "Learned", "Reproduce"):
            if f"{word}:" not in note:
                problems.append(f"run {version!r} note is missing {word}:")
        if run["id"] not in pictured:
            problems.append(f"run {version!r} has no chart")
        for score in run.get("evals") or []:
            if 0 < score["score"] < 1:
                problems.append(f"{version} {score['behavior']} reads as a fraction")
    return problems


def _track(
    cases: Sequence[EvaluationCase],
    evaluated: Sequence[CaseEvaluation],
    test: str,
    summary: dict[str, dict[str, Any]],
    rows_by_name: dict[str, list[dict[str, Any]]],
    noise: dict[str, float],
    headline_variance: dict[str, Any],
    need: dict[str, Any],
) -> list[str]:
    harness = Harness(label="offline-default@none", model=MODEL, instructions=POLICY, tools=[])
    tracked = track(AGENT_ID, model=MODEL, harness=harness)

    # The question is written before the first score or run is created.
    tracked.experiment(
        question=(
            f"Does shipped offline VeritasAgent identify review-worthy claims and reasoning while "
            f"preserving corrections, time changes, opinions, and metaphor across this frozen set "
            f"of {len(cases)} conversations?"
        ),
        hypothesis=HYPOTHESIS,
        method=METHOD,
        measure=MEASURE,
        decide=DECIDE,
    )
    for category, (name, description) in BEHAVIORS.items():
        tracked.behavior(
            Behavior(
                name=name,
                test_version=test,
                n=len(cases),
                noise_floor=noise[name],
                contamination=0,
                reward_is_judge=False,
                graded_by="program",
                description=description,
                rubric=description,
            )
        )

    data_hash = hashlib.sha256(
        "\n".join(case.id for case in cases).encode("utf-8")
    ).hexdigest()
    record = RunRecord(
        data=Data(holdout=test, holdout_hash=data_hash, n_holdout=len(cases), decontaminated_dropped=0),
        eval=EvalSetup(
            metric="pass@1",
            k=K,
            run_std=float(headline_variance["run_std"]),
            run_std_runs=RERUNS,
            reader="deterministic category rubric",
        ),
        provenance=Provenance(pins={"veritas-agent": RELEASE, "whileai": "0.131"}),
    )
    run = tracked.run(
        RELEASE,
        method="eval",
        targets=[name for name, _description in BEHAVIORS.values()],
        harness=harness,
        record=record,
    )
    status = "failed"
    try:
        for name, _description in BEHAVIORS.values():
            stats = summary[name]
            run.score(
                name,
                stats["points"],
                ci=stats["ci"],
                n=stats["n"],
                test_version=test,
                rows=rows_by_name[name],
            )
        run.note(_run_note(test, cases, summary, noise, evaluated, need))

        names = [name for name, _description in BEHAVIORS.values()]
        tracked.figure(
            "baseline-behaviors",
            {
                "data": [
                    {
                        "type": "bar",
                        "x": names,
                        "y": [summary[name]["points"] for name in names],
                        "error_y": {
                            "type": "data",
                            "array": [summary[name]["ci"] for name in names],
                            "visible": True,
                        },
                    }
                ],
                "layout": {
                    "title": "VeritasAgent 0.1.0: exact category agreement, points",
                    "yaxis": {"title": "points out of 100", "range": [0, 100]},
                    "xaxis": {"tickangle": -35},
                },
            },
            caption=f"One offline baseline on frozen test {test}; intervals are ask-level 95% half-widths.",
            run=run,
        )
        status = "evaluated"
    finally:
        run.finish(status=status, cost_usd=0.0, record=record, say=False)

    print(tracked.brief())
    print(tracked.verdict())
    problems = _readback(tracked)
    print("readback(tracked):")
    if problems:
        for problem in problems:
            print(f"  {problem}")
    else:
        print("  clean")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path(__file__).parent / "datasets" / "human_450.jsonl")
    parser.add_argument("--track", action="store_true", help="post one baseline run to the signed-in While account")
    args = parser.parse_args()

    cases = load_cases(args.dataset)
    test = test_version(cases)
    evaluator = Evaluator()
    evaluated_runs: list[list[CaseEvaluation]] = []
    for _ in range(RERUNS):
        _result, evaluated = evaluator.evaluate(
            cases,
            AnalysisOrchestrator(),
            dataset_name=test,
            include_whileai=False,
        )
        evaluated_runs.append(evaluated)
    evaluated = evaluated_runs[0]
    summaries, rows_by_name = _summarize(cases, evaluated)
    rows_by_run: dict[str, list[list[dict[str, Any]]]] = {
        name: [
            _rows(cases, run_result, category)
            for run_result in evaluated_runs
        ]
        for category, (name, _description) in BEHAVIORS.items()
    }
    noise: dict[str, float] = {}
    headline_variance: dict[str, Any] | None = None
    for name, runs in rows_by_run.items():
        variance = wai.eval_variance(*runs)
        noise[name] = round(100 * float(variance["noise_band"]), 1)
        if name == BEHAVIORS[None][0]:
            headline_variance = variance
    if headline_variance is None:
        raise RuntimeError("The headline behavior has no variance report")

    headline_rows = rows_by_name[BEHAVIORS[None][0]]
    need = wai.holdout_size(0.05, rows=headline_rows, k=K)
    _print_report(cases, test, summaries, noise, need, evaluated)
    print("\ncoverage gap in the five-case representative suite:")
    print(_coverage_report())
    if args.track:
        _track(cases, evaluated, test, summaries, rows_by_name, noise, headline_variance, need)


if __name__ == "__main__":
    main()
