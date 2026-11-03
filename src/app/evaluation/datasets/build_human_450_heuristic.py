"""Build a heuristic-labeled variant of the human_450 dataset.

This keeps the original dataset unchanged and writes a new JSONL next to it.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.evaluation.evaluator import EvaluationCase
from app.evaluation.heuristic_labeler import label_conversation


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "human_450.jsonl"
TARGET = HERE / "human_450_heuristic.jsonl"


def main() -> None:
    cases = []
    for line_number, line in enumerate(SOURCE.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            cases.append(EvaluationCase.model_validate_json(line))
        except ValueError as error:
            raise ValueError(f"Invalid evaluation case on line {line_number} of {SOURCE}") from error

    with TARGET.open("w", encoding="utf-8") as handle:
        for case in cases:
            expected = label_conversation(case.conversation)
            payload = {
                "id": case.id,
                "conversation": case.conversation,
                "expected_categories": [item.value for item in expected],
                "notes": case.notes,
            }
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()

