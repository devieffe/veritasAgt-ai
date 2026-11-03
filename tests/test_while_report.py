from app.core.models import AnalysisReport
from app.evaluation.evaluator import CaseEvaluation, EvaluationCase, EvaluationCategory
from app.evaluation.while_report import _half_width, _rows, load_cases, test_version as make_test_version


def test_heldout_dataset_is_frozen_and_has_unique_cases():
    cases = load_cases("src/app/evaluation/datasets/heldout.jsonl")

    assert len(cases) == 33
    assert len({case.id for case in cases}) == len(cases)
    assert len({case.conversation for case in cases}) == len(cases)
    assert make_test_version(cases).startswith("t-")


def test_test_version_tracks_ask_content_not_input_order():
    first = EvaluationCase(id="first", conversation="A: The box is open.")
    second = EvaluationCase(id="second", conversation="B: The box is closed.")

    assert make_test_version([first, second]) == make_test_version([second, first])
    assert make_test_version([first, second]) != make_test_version([first])


def test_behavior_rows_keep_case_ids_and_binary_rewards():
    case = EvaluationCase(
        id="conflict-case",
        conversation="A: The light is on. B: The light is off.",
        expected_categories=[EvaluationCategory.CONTRADICTION_DETECTION],
    )
    result = CaseEvaluation(
        case_id=case.id,
        expected_categories=case.expected_categories,
        predicted_categories=[EvaluationCategory.CONTRADICTION_DETECTION],
        report=AnalysisReport(original_conversation_reference=case.id, overall_summary=""),
    )

    rows = _rows([case], [result], EvaluationCategory.CONTRADICTION_DETECTION)

    assert rows[0]["task_id"] == case.id
    assert rows[0]["reward"] == 1
    assert rows[0]["ok"] is True


def test_perfect_score_still_has_nonzero_exact_interval():
    assert 0 < _half_width(None, 1.0, 18) < 1
