import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SOURCE = path.resolve(__dirname, '../src/app/evaluation/datasets/human_450.jsonl');
const TARGET = path.resolve(__dirname, '../src/app/evaluation/datasets/human_450_heuristic.jsonl');

const CORRECTION_RE = /\b(actually|correction:|i\s+mean(t)?|sorry,?\s+i\s+misread)\b/i;
const MISREPRESENTATION_RE = /\b(i\s+never\s+said\s+that|you\s+never\s+said\s+that|that's\s+a\s+lie|liar)\b/i;
const UNCERTAINTY_RE = /\b(maybe|probably|i\s+think|not\s+sure|unsure|guess)\b/i;
const OVERCONFIDENT_RE = /\b(100%|definitely|for\s+sure|no\s+doubt|guarantee)\b/i;
const EVIDENCE_RE = /\b(see\s+attached|attachment|screenshot|link:|http[s]?:\/\/)\b/i;

const ANTONYM_PAIRS = [
	['yes', 'no'],
	['open', 'closed'],
	['on', 'off'],
	['true', 'false'],
	['full', 'empty'],
	['here', 'there'],
];

function labelConversation(conversation) {
	const text = (conversation ?? '').trim();
	if (!text) return [];
	const lowered = text.toLowerCase();
	const labels = new Set();

	if (/(\b(is|are|was|were|will|did|sent|paid|met|said|told)\b)/i.test(text) || /\d/.test(text)) {
		labels.add('claim_extraction');
	}
	if (CORRECTION_RE.test(text)) {
		labels.add('context_awareness');
	}
	if (MISREPRESENTATION_RE.test(text)) {
		labels.add('misrepresentation_detection');
		labels.add('factual_verification');
	}
	if (EVIDENCE_RE.test(text)) {
		labels.add('evidence_grounding');
	}
	if (UNCERTAINTY_RE.test(text) || OVERCONFIDENT_RE.test(text)) {
		labels.add('uncertainty_calibration');
	}
	if (/(\b(today|tomorrow|yesterday|at\s+\d|am|pm|\d{1,2}:\d{2})\b)/i.test(text) || /(\b(price|bank|invoice|receipt|contract|address|email)\b)/i.test(text)) {
		labels.add('factual_verification');
	}
	for (const [left, right] of ANTONYM_PAIRS) {
		const leftRe = new RegExp(`\\b${left.replaceAll(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')}\\b`, 'i');
		const rightRe = new RegExp(`\\b${right.replaceAll(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')}\\b`, 'i');
		if (leftRe.test(lowered) && rightRe.test(lowered)) {
			labels.add('contradiction_detection');
			break;
		}
	}

	const letters = [...text].filter((ch) => /[a-z]/i.test(ch)).length;
	if (letters > 0) {
		const nonLetters = text.length - letters;
		if (nonLetters / text.length > 0.45) {
			labels.add('nonsense_detection');
			labels.add('semantic_coherence');
		}
	}

	return [...labels].sort();
}

async function main() {
	const raw = await fs.readFile(SOURCE, 'utf8');
	const lines = raw.split(/\r?\n/).filter(Boolean);
	const out = [];
	for (const line of lines) {
		const item = JSON.parse(line);
		out.push(
			JSON.stringify(
				{
					...item,
					expected_categories: labelConversation(item.conversation),
				},
				{ ensureAscii: false },
			),
		);
	}
	await fs.writeFile(TARGET, out.join('\n') + '\n', 'utf8');
}

await main();

