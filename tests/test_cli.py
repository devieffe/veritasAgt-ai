import json
from pathlib import Path

from app.main import main


def test_file_cli_exports_json_report(tmp_path: Path, capsys) -> None:
    fixture = Path(__file__).parent / "fixtures" / "representative_conversation.txt"
    output = tmp_path / "analysis.json"

    exit_code = main(["--file", str(fixture), "--output", str(output)])

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["extracted_claims"]
    assert payload["findings"]
    assert "JSON report written" in capsys.readouterr().out
