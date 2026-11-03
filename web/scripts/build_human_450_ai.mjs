import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { env, pipeline } from '@xenova/transformers';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Keep all model downloads inside the repo (and ignored by git).
env.cacheDir = path.resolve(__dirname, '../../.transformers-cache');

const SOURCE = path.resolve(__dirname, '../../src/app/evaluation/datasets/human_450.jsonl');
const TARGET = path.resolve(__dirname, '../../src/app/evaluation/datasets/human_450_ai.jsonl');

const CATEGORIES = [
	{
		id: 'claim_extraction',
		description:
			'Conversation contains factual claims or assertions that should be extracted (not purely opinions, jokes, or questions).',
	},
	{
		id: 'contradiction_detection',
		description:
			'Conversation includes two statements that cannot both be true about the same thing at the same time (a direct contradiction).',
	},
	{
		id: 'factual_verification',
		description:
			'Conversation makes checkable factual claims that should be verified with evidence (dates, events, who did what, numbers).',
	},
	{
		id: 'misrepresentation_detection',
		description:
			'Conversation includes misrepresentation, selective quoting, or claims about what someone said/did that are not supported by the chat itself.',
	},
	{
		id: 'nonsense_detection',
		description:
			'Conversation contains nonsense or incoherent content that breaks meaning (not just metaphor or humor).',
	},
	{
		id: 'logical_coherence',
		description:
			'Conversation includes flawed reasoning (bad inference, invalid causality, false dilemma, circular logic).',
	},
	{
		id: 'semantic_coherence',
		description:
			'Conversation has semantic ambiguity or meaning issues that require care (distinguish metaphor from nonsense).',
	},
	{
		id: 'context_awareness',
		description:
			'Conversation includes corrections, time shifts, or context that should prevent naive contradiction labeling.',
	},
	{
		id: 'evidence_grounding',
		description:
			'Conversation references evidence like attachments, links, screenshots, or quoted material that should be grounded when making findings.',
	},
	{
		id: 'uncertainty_calibration',
		description:
			'Conversation requires uncertainty calibration (unknown facts, guesses, hedging, or overconfidence without evidence).',
	},
];

const CANDIDATE_LABELS = CATEGORIES.map((item) => `${item.id}: ${item.description}`);

function parseArgs(argv) {
	const args = {
		limit: null,
		threshold: 0.55,
		maxLabels: 4,
		model: 'Xenova/mobilebert-uncased-mnli',
		progressEvery: 25,
		maxChars: 2000,
	};
	for (let i = 0; i < argv.length; i++) {
		const item = argv[i];
		if (item === '--limit') args.limit = Number(argv[++i]);
		if (item === '--threshold') args.threshold = Number(argv[++i]);
		if (item === '--max-labels') args.maxLabels = Number(argv[++i]);
		if (item === '--model') args.model = argv[++i];
		if (item === '--progress-every') args.progressEvery = Number(argv[++i]);
		if (item === '--max-chars') args.maxChars = Number(argv[++i]);
	}
	return args;
}

async function main() {
	const options = parseArgs(process.argv.slice(2));

	const raw = await fs.readFile(SOURCE, 'utf8');
	const lines = raw.split(/\r?\n/).filter(Boolean);
	const rows = lines.map((line) => JSON.parse(line));
	const slice = options.limit ? rows.slice(0, options.limit) : rows;

	const classifier = await pipeline('zero-shot-classification', options.model);

	const out = [];
	let index = 0;
	for (const row of slice) {
		index += 1;
		if (options.progressEvery > 0 && index % options.progressEvery === 0) {
			console.error(`labeled ${index}/${slice.length}`);
		}
		const text = String(row.conversation ?? '').trim();
		if (!text) {
			out.push(JSON.stringify({ ...row, expected_categories: [] }));
			continue;
		}
		const snippet = text.slice(0, options.maxChars);

		// Run one category at a time so we can keep label text rich and stable.
		const result = await classifier(snippet, CANDIDATE_LABELS, {
			multi_label: true,
		});

		const scores = (result.labels ?? []).map((label, index) => {
			const id = String(label).split(':', 1)[0].trim();
			return { id, score: result.scores?.[index] ?? 0 };
		});

		scores.sort((a, b) => b.score - a.score);
		const chosen = scores
			.filter((item) => item.score >= options.threshold)
			.slice(0, options.maxLabels)
			.map((item) => item.id)
			.sort();

		out.push(JSON.stringify({ ...row, expected_categories: chosen }));
	}

	await fs.writeFile(TARGET, out.join('\n') + '\n', 'utf8');
}

await main();

