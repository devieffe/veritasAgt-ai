# Architecture

## Project layout

The installable package is `src/app/`. `app.core` owns validated domain models, transcript parsing, and orchestration. Each module in `app.engines` is independently callable and accepts the shared conversation models. `app.providers` contains vendor adapters, and `app.evaluation` owns datasets, local metrics, and the optional While SDK adapter. The CLI lives in `app.main`.

## Analysis flow

1. `ConversationParser` preserves message wording and explicit speaker labels, assigns message order and IDs, and leaves unlabelled text without an invented identity.
2. `ClaimExtractionEngine` identifies exact factual spans and links each one to its source message.
3. Contradiction detection compares claims while filtering explicit corrections and distinct time periods.
4. Factual verification checks supplied evidence, configured evidence sources, or conversation context. It does not treat the absence of evidence as proof of falsity.
5. Misrepresentation, nonsense, and logical coherence run independently so an implausible factual claim is not automatically categorized as nonsense.
6. Context analysis reviews candidate findings for corrections, timing, ambiguity, and alternative interpretations.
7. The orchestrator removes duplicate findings and returns an `AnalysisReport` with provenance and limitations.

## Provider abstraction

`LLMProvider` defines `generate_response()` and a shared `analyze_structured()` method. OpenAI, Anthropic, and local OpenAI-compatible adapters implement that interface; engines do not contain vendor SDK calls. Model responses are validated with Pydantic, and model-generated quotations are kept only when they match the source text exactly.

The default provider is `none`, which allows the CLI and tests to run offline. Pattern checks are deliberately conservative. Select a model provider to use semantic analysis. A model or network error is surfaced instead of silently presented as a completed semantic review.

## Evidence sources

Callers can pass user-document or external-source `Evidence` values directly to the verifier, or inject an `EvidenceProvider`. The optional `ConfiguredJsonEvidenceProvider` calls only a user-configured endpoint. That endpoint must accept a `q` query parameter and return `{"results": [{"source_reference": "...", "relevant_content": "...", "reliability_assessment": "...", "retrieval_information": {}}]}`. This is VeritasAgent's adapter contract; it does not claim compatibility with any particular search vendor.

## While SDK integration

The SDK version in the initial lockfile is `whileai` 0.131. Its official eval documentation describes local agent evaluation and `pass_at` over graded row dictionaries. `Evaluator` adapts each labeled case/category result to `{"task_id": ..., "reward": 0|1}` and calls the documented `whileai.pass_at(rows, min_k=1)` function. Conversation text stays local. Category precision/recall/F1 and false-positive/negative rates are calculated by VeritasAgent's own metrics module.
