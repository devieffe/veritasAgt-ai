import heldout500 from '../../src/app/evaluation/datasets/heldout_500.jsonl?raw';
import heldout from '../../src/app/evaluation/datasets/heldout.jsonl?raw';
import representative from '../../src/app/evaluation/datasets/representative.jsonl?raw';
import human450 from '../../src/app/evaluation/datasets/human_450.jsonl?raw';
import human450Heuristic from '../../src/app/evaluation/datasets/human_450_heuristic.jsonl?raw';
import human450Ai from '../../src/app/evaluation/datasets/human_450_ai.jsonl?raw';

const parseJsonl = (source) => {
	const trimmed = source.trim();
	if (!trimmed) return [];
	return trimmed.split('\n').filter(Boolean).map((line) => JSON.parse(line));
};

export const DATASETS = [
	{
		id: 'human-450-heuristic',
		name: 'Human chat (heuristic-labeled)',
		shortName: 'Human 450 (auto)',
		file: 'human_450_heuristic.jsonl',
		description: 'Deterministic offline heuristic labels generated from the same raw chats. Use this to get coverage charts immediately; treat results as a reviewable starting point, not gold truth.',
		rows: parseJsonl(human450Heuristic),
	},
	{
		id: 'human-450-ai',
		name: 'Human chat (AI-labeled)',
		shortName: 'Human 450 (AI)',
		file: 'human_450_ai.jsonl',
		description: 'transformers.js zero-shot labels generated locally. This is a silver label source; review and spot-check before treating as gold truth.',
		rows: parseJsonl(human450Ai),
	},
	{
		id: 'human-450',
		name: 'Human chat (unlabeled)',
		shortName: 'Human 450',
		file: 'human_450.jsonl',
		description: '450 human-like chat examples with 1–4 users and 1–20 replies each. This set is unlabeled (expected checks are empty) and is meant for UI browsing and qualitative testing.',
		rows: parseJsonl(human450),
	},
	{
		id: 'heldout-500',
		name: 'Held-out diagnostic',
		shortName: 'Held-out 500',
		file: 'heldout_500.jsonl',
		description: 'A larger synthetic diagnostic set. Many examples share templates, so row count is not the same as independent real-world coverage.',
		rows: parseJsonl(heldout500),
	},
	{
		id: 'heldout',
		name: 'Frozen holdout',
		shortName: 'Frozen 33',
		file: 'heldout.jsonl',
		description: 'A content-hashed holdout for keeping asks fixed across future comparisons.',
		rows: parseJsonl(heldout),
	},
	{
		id: 'representative',
		name: 'Representative',
		shortName: 'Representative',
		file: 'representative.jsonl',
		description: 'A compact set of examples spanning common findings and neutral controls.',
		rows: parseJsonl(representative),
	},
];

export const CHECKS = [
	{
		id: 'claim_extraction',
		name: 'Extract factual claims',
		short: 'Claim extraction',
		description: 'Keep factual assertions; skip opinions, questions, hypotheticals, and creative language.',
		tests: ['test_claim_extraction.py'],
		accent: 'blue',
	},
	{
		id: 'contradiction_detection',
		name: 'Detect statement conflicts',
		short: 'Contradictions',
		description: 'Find genuine conflicts about the same proposition, not corrections or different time periods.',
		tests: ['test_contradictions.py', 'test_context.py'],
		accent: 'rose',
	},
	{
		id: 'factual_verification',
		name: 'Verify with evidence',
		short: 'Factual verification',
		description: 'Compare claims only with available evidence. Missing evidence means unverified, not false.',
		tests: ['test_verification.py'],
		accent: 'violet',
	},
	{
		id: 'misrepresentation_detection',
		name: 'Flag observable misrepresentation',
		short: 'Misrepresentation',
		description: 'Surface selective presentation and unsupported universal claims without guessing intent.',
		tests: ['test_misrepresentation.py'],
		accent: 'amber',
	},
	{
		id: 'nonsense_detection',
		name: 'Flag semantic absurdity',
		short: 'Nonsense detection',
		description: 'Catch category errors while preserving unusual but interpretable claims.',
		tests: ['test_nonsense.py'],
		accent: 'orange',
	},
	{
		id: 'logical_coherence',
		name: 'Assess inference validity',
		short: 'Logical coherence',
		description: 'Explain unsupported causes, false dilemmas, hasty generalizations, and circular reasoning.',
		tests: ['test_logic.py'],
		accent: 'teal',
	},
	{
		id: 'semantic_coherence',
		name: 'Preserve semantic coherence',
		short: 'Semantic coherence',
		description: 'Distinguish absurdity from metaphor, fiction, and other meaningful language.',
		tests: ['test_nonsense.py'],
		accent: 'cyan',
	},
	{
		id: 'context_awareness',
		name: 'Apply conversation context',
		short: 'Context awareness',
		description: 'Use corrections, time references, and the full conversation before labeling a conflict.',
		tests: ['test_context.py', 'test_contradictions.py'],
		accent: 'green',
	},
	{
		id: 'evidence_grounding',
		name: 'Ground findings in evidence',
		short: 'Evidence grounding',
		description: 'Attach conversation or source evidence to each surfaced finding.',
		tests: ['test_verification.py', 'test_orchestrator.py'],
		accent: 'indigo',
	},
	{
		id: 'uncertainty_calibration',
		name: 'Express uncertainty',
		short: 'Uncertainty calibration',
		description: 'Keep unsupported claims explicitly unverified and confidence appropriately low.',
		tests: ['test_verification.py', 'test_context.py'],
		accent: 'slate',
	},
];

export const ANALYSIS_STAGES = [
	'Claim extraction',
	'Contradiction detection',
	'Factual verification',
	'Misrepresentation detection',
	'Nonsense detection',
	'Logical coherence',
	'Context analysis',
];

export function categoryCount(rows, categoryId) {
	return rows.filter((row) => row.expected_categories.includes(categoryId)).length;
}
