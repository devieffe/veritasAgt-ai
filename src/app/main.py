"""Command-line interface for interactive and file-based analysis."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from app.config import Settings, create_evidence_provider, create_provider
from app.core.orchestrator import AnalysisOrchestrator
from app.providers.base import ProviderError
from app.utils.logging import configure_logging


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="veritasagent",
        description="Analyze a written conversation and report evidence-aware findings.",
    )
    parser.add_argument("--file", type=Path, help="UTF-8 text file containing the conversation")
    parser.add_argument("--output", type=Path, help="Write the full report as JSON to this path")
    parser.add_argument(
        "--provider",
        choices=("none", "openai", "anthropic", "local"),
        help="Override VERITAS_PROVIDER for this run",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    args = build_argument_parser().parse_args(argv)
    try:
        raw_text = args.file.read_text(encoding="utf-8") if args.file else _read_interactive()
        if not raw_text.strip():
            print("No conversation text was supplied.", file=sys.stderr)
            return 2
        settings = Settings.from_environment()
        if args.provider:
            settings = replace(settings, provider=args.provider)
        provider = create_provider(settings)
        evidence_provider = create_evidence_provider(settings)
        report = AnalysisOrchestrator(
            provider=provider,
            evidence_provider=evidence_provider,
        ).analyze_conversation(raw_text)
    except (OSError, ValueError, ProviderError) as error:
        print(str(error), file=sys.stderr)
        return 2

    _print_report(report)
    if args.output:
        try:
            args.output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        except OSError as error:
            print(f"Could not write JSON report: {error}", file=sys.stderr)
            return 2
        print(f"\nJSON report written to {args.output}")
    return 0


def _read_interactive() -> str:
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("Paste the conversation. Enter :done on a line by itself when finished.")
    lines: list[str] = []
    for line in sys.stdin:
        if line.rstrip("\r\n") == ":done":
            break
        lines.append(line)
    return "".join(lines)


def _print_report(report) -> None:
    print(report.overall_summary)
    if not report.findings:
        print("No review items were detected.")
    for index, finding in enumerate(report.findings, start=1):
        print(f"\n{index}. {finding.type} — {finding.status}")
        print(f"   Severity: {finding.severity}/5 | Confidence: {finding.confidence:.0f}/100")
        print(f"   Statement: {finding.original_statement}")
        if finding.related_statement:
            print(f"   Related: {finding.related_statement}")
        print(f"   Explanation: {finding.explanation}")
        if finding.evidence:
            print("   Evidence:")
            for item in finding.evidence:
                reference = f" ({item.source_reference})" if item.source_reference else ""
                print(f"     - {item.source_type}{reference}: {item.relevant_content}")
        if finding.limitations:
            print(f"   Limitations: {' '.join(finding.limitations)}")
    if report.analysis_limitations:
        print("\nAnalysis limitations:")
        for limitation in report.analysis_limitations:
            print(f"- {limitation}")


if __name__ == "__main__":
    raise SystemExit(main())
