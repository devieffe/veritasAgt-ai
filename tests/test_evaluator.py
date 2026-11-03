from app.evaluation.evaluator import EvaluationCase, Evaluator
from app.evaluation.metrics import binary_metrics
from app.core.orchestrator import AnalysisOrchestrator


def test_binary_metrics_include_false_positive_and_false_negative_rates() -> None:
    metrics = binary_metrics([True, True, False, False], [True, False, True, False])

    assert metrics["accuracy"] == 0.5
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["f1"] == 0.5
    assert metrics["false_positive_rate"] == 0.5
    assert metrics["false_negative_rate"] == 0.5


def test_evaluator_uses_local_results_and_documented_while_pass_at_api() -> None:
    dataset = [
        EvaluationCase(
            id="neutral",
            conversation="Speaker A: I prefer tea.",
            expected_categories=[],
        ),
        EvaluationCase(
            id="conflict",
            conversation="Speaker A: The jar is full right now.\nSpeaker B: The jar is empty right now.",
            expected_categories=[
                "claim_extraction",
                "contradiction_detection",
                "factual_verification",
                "evidence_grounding",
            ],
        ),
    ]

    result, cases = Evaluator().evaluate(dataset, AnalysisOrchestrator(), dataset_name="smoke")

    assert result.sample_count == 2
    assert len(cases) == 2
    assert "accuracy" in result.category_metrics["contradiction_detection"]
    assert "pass_at_1" in result.whileai_metrics["contradiction_detection"]
