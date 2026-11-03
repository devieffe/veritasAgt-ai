"""Dataset runner and version-verified integration with While's local metrics."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.core.models import AnalysisReport, EvaluationResult, FindingType
from app.core.orchestrator import AnalysisOrchestrator
from app.evaluation.metrics import binary_metrics


class EvaluationCategory(StrEnum):
    CLAIM_EXTRACTION = "claim_extraction"
    CONTRADICTION_DETECTION = "contradiction_detection"
    FACTUAL_VERIFICATION = "factual_verification"
    MISREPRESENTATION_DETECTION = "misrepresentation_detection"
    NONSENSE_DETECTION = "nonsense_detection"
    LOGICAL_COHERENCE = "logical_coherence"
    SEMANTIC_COHERENCE = "semantic_coherence"
    CONTEXT_AWARENESS = "context_awareness"
    EVIDENCE_GROUNDING = "evidence_grounding"
    UNCERTAINTY_CALIBRATION = "uncertainty_calibration"


class EvaluationCase(BaseModel):
    id: str
    conversation: str
    expected_categories: list[EvaluationCategory] = Field(default_factory=list)
    notes: str = ""


class CaseEvaluation(BaseModel):
    case_id: str
    expected_categories: list[EvaluationCategory]
    predicted_categories: list[EvaluationCategory]
    report: AnalysisReport


class Evaluator:
    """Run labeled conversation cases through the complete analysis pipeline."""

    def evaluate(
        self,
        dataset: list[EvaluationCase],
        orchestrator: AnalysisOrchestrator,
        *,
        dataset_name: str = "in-memory",
        include_whileai: bool = True,
    ) -> tuple[EvaluationResult, list[CaseEvaluation]]:
        cases = []
        for case in dataset:
            report = orchestrator.analyze_conversation(case.conversation)
            cases.append(
                CaseEvaluation(
                    case_id=case.id,
                    expected_categories=case.expected_categories,
                    predicted_categories=self._predictions(report),
                    report=report,
                )
            )
        all_categories = list(EvaluationCategory)
        category_metrics = {
            category.value: binary_metrics(
                [category in case.expected_categories for case in cases],
                [category in case.predicted_categories for case in cases],
            )
            for category in all_categories
        }
        correctness = [
            set(case.expected_categories) == set(case.predicted_categories)
            for case in cases
        ]
        overall = binary_metrics([True] * len(correctness), correctness)
        limitations: list[str] = []
        while_metrics: dict[str, Any] = {}
        if include_whileai:
            try:
                while_metrics = self._whileai_metrics(cases, all_categories)
            except ImportError:
                limitations.append("While SDK is unavailable; local classification metrics were still computed.")
        return (
            EvaluationResult(
                dataset_name=dataset_name,
                sample_count=len(cases),
                category_metrics=category_metrics,
                overall_metrics=overall,
                whileai_metrics=while_metrics,
                limitations=limitations,
            ),
            cases,
        )

    @staticmethod
    def load_jsonl(path: str | Path) -> list[EvaluationCase]:
        cases = []
        for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                cases.append(EvaluationCase.model_validate_json(line))
            except ValueError as error:
                raise ValueError(f"Invalid evaluation case on line {line_number} of {path}") from error
        return cases

    @staticmethod
    def _predictions(report: AnalysisReport) -> list[EvaluationCategory]:
        findings = {finding.type for finding in report.findings}
        predicted: set[EvaluationCategory] = set()
        if report.extracted_claims:
            predicted.add(EvaluationCategory.CLAIM_EXTRACTION)
        if FindingType.CONTRADICTION in findings:
            predicted.add(EvaluationCategory.CONTRADICTION_DETECTION)
        if FindingType.FACTUAL_VERIFICATION in findings:
            predicted.add(EvaluationCategory.FACTUAL_VERIFICATION)
        if FindingType.MISREPRESENTATION in findings:
            predicted.add(EvaluationCategory.MISREPRESENTATION_DETECTION)
        if FindingType.NONSENSE in findings:
            predicted.update({EvaluationCategory.NONSENSE_DETECTION, EvaluationCategory.SEMANTIC_COHERENCE})
        if FindingType.LOGICAL_FALLACY in findings:
            predicted.add(EvaluationCategory.LOGICAL_COHERENCE)
        if any(
            "correction or clarification" in text
            or "correction or time change" in text
            or "different explicit time periods" in text
            for text in report.analysis_limitations
        ):
            predicted.add(EvaluationCategory.CONTEXT_AWARENESS)
        if report.findings and all(finding.evidence for finding in report.findings):
            predicted.add(EvaluationCategory.EVIDENCE_GROUNDING)
        if any(
            finding.status == "UNVERIFIED" and finding.confidence <= 50
            for finding in report.findings
        ):
            predicted.add(EvaluationCategory.UNCERTAINTY_CALIBRATION)
        return sorted(predicted, key=lambda category: category.value)

    @staticmethod
    def _whileai_metrics(cases: list[CaseEvaluation], categories: list[EvaluationCategory]) -> dict[str, Any]:
        """Use documented ``whileai.pass_at(rows)`` on local binary eval rows.

        While's SDK documents ``pass_at`` as accepting graded row dictionaries,
        and documents ``task_id`` plus binary ``reward`` as its grouping and
        scoring fields. No conversation text is sent to While by this method.
        """
        try:
            import whileai as wai
        except ImportError as error:
            raise ImportError("Install whileai to use the While evaluation adapter") from error

        output: dict[str, Any] = {}
        for category in categories:
            rows = [
                {
                    "task_id": f"{case.case_id}:{category.value}",
                    "reward": int((category in case.expected_categories) == (category in case.predicted_categories)),
                }
                for case in cases
            ]
            result = wai.pass_at(rows, min_k=1)
            output[category.value] = result.to_dict()
        return output


def default_dataset_path() -> Path:
    return Path(__file__).parent / "datasets" / "human_450.jsonl"
