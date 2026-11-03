import { useEffect, useMemo, useState } from 'react';
import {
	Activity,
	ArrowDownRight,
	ArrowUpRight,
	Check,
	ChevronDown,
	ChevronRight,
	CircleHelp,
	Copy,
	Database,
	FileCheck2,
	Filter,
	Layers3,
	Search,
	ShieldCheck,
	Sparkles,
	X,
} from 'lucide-react';
import { ANALYSIS_STAGES, CHECKS, DATASETS, categoryCount } from './data.js';

const tone = {
	blue: 'bg-white text-[var(--ui-accent)] ring-[var(--ui-border-strong)]',
	rose: 'bg-white text-[var(--ui-accent)] ring-[var(--ui-border-strong)]',
	violet: 'bg-white text-[var(--ui-accent)] ring-[var(--ui-border-strong)]',
	amber: 'bg-white text-[var(--ui-accent)] ring-[var(--ui-border-strong)]',
	orange: 'bg-white text-[var(--ui-accent)] ring-[var(--ui-border-strong)]',
	teal: 'bg-white text-[var(--ui-accent)] ring-[var(--ui-border-strong)]',
	cyan: 'bg-white text-[var(--ui-accent)] ring-[var(--ui-border-strong)]',
	green: 'bg-white text-[var(--ui-accent)] ring-[var(--ui-border-strong)]',
	indigo: 'bg-white text-[var(--ui-accent)] ring-[var(--ui-border-strong)]',
	slate: 'bg-white text-[var(--ui-muted)] ring-[var(--ui-border)]',
};

function Tag({ children, color = 'slate' }) {
	return <span className={`inline-flex items-center rounded-md px-2 py-1 text-[11px] font-medium ring-1 ring-inset ${tone[color]}`}>{children}</span>;
}

const CHECK_HIGHLIGHTS = {
	claim_extraction: [/\b\d+(?:\.\d+)?\b/g, /\b[A-Z][a-z]{2,}\b/g],
	contradiction_detection: [/\b(but|however|although|instead|actually|no\b)\b/gi],
	factual_verification: [/\b(is|are|was|were|has|have|contains|located|founded)\b/gi],
	misrepresentation_detection: [/\b(always|never|everyone|no one|all|none|guarantee|100%)\b/gi],
	nonsense_detection: [/\b(unicorn|teleport|time\s+travel|square\s+circle)\b/gi],
	logical_coherence: [/\b(because|therefore|thus|so\b|since)\b/gi],
	semantic_coherence: [/\b(like|as\s+if|metaphor|figuratively)\b/gi],
	context_awareness: [/\b(yesterday|today|tomorrow|earlier|later|before|after)\b/gi],
	evidence_grounding: [/\b(source|evidence|cite|citation|according\s+to)\b/gi],
	uncertainty_calibration: [/\b(maybe|might|could|uncertain|unknown|unverified)\b/gi],
};

const ACCENT_RING = {
	blue: 'ring-[var(--ui-border-strong)]',
	rose: 'ring-[var(--ui-border-strong)]',
	violet: 'ring-[var(--ui-border-strong)]',
	amber: 'ring-[var(--ui-border-strong)]',
	orange: 'ring-[var(--ui-border-strong)]',
	teal: 'ring-[var(--ui-border-strong)]',
	cyan: 'ring-[var(--ui-border-strong)]',
	green: 'ring-[var(--ui-border-strong)]',
	indigo: 'ring-[var(--ui-border-strong)]',
	slate: 'ring-[var(--ui-border-strong)]',
};

function previewConversation(conversation) {
	const stripped = String(conversation ?? '')
		.replaceAll(/(^|\n)\s*[^:\n]{1,28}:\s*/g, '$1')
		.replaceAll('\n', ' ')
		.replaceAll(/\s+/g, ' ')
		.trim();
	if (!stripped) return '';
	const words = stripped.split(' ').slice(0, 14).join(' ');
	return stripped.length > words.length ? `${words}…` : words;
}

function Modal({ open, title, onClose, children }) {
	if (!open) return null;
	return (
		<div className="fixed inset-0 z-50 flex items-stretch justify-stretch">
			<button aria-label="Close modal" className="absolute inset-0 bg-white" onClick={onClose} />
			<div className="relative flex w-full flex-1 flex-col overflow-hidden border border-[var(--ui-border)] bg-[var(--ui-panel)]">
				<div className="flex items-center justify-between border-b border-[var(--ui-border)] bg-[var(--ui-panel-muted)] px-5 py-3.5">
					<div className="text-sm font-semibold text-[var(--ui-text)]">{title}</div>
					<button
						onClick={onClose}
						aria-label="Close"
						title="Close"
						className="flex size-8 items-center justify-center rounded-lg border border-[var(--ui-border)] bg-[var(--ui-panel)] text-[var(--ui-muted)] hover:text-[var(--ui-accent)]"
					>
						<X size={15} />
					</button>
				</div>
				<div className="flex-1 overflow-auto p-5">{children}</div>
			</div>
		</div>
	);
}

function CodeBlock({ children }) {
	return (
		<pre className="mt-3 overflow-x-auto rounded-xl border border-[var(--ui-border)] bg-[var(--ui-panel)] p-3 text-[11px] leading-5 text-[var(--ui-muted)]">
			<code>{children}</code>
		</pre>
	);
}

function HighlightedText({ text, checkIds }) {
	const matches = [];
	const uniqueCheckIds = Array.from(new Set(checkIds ?? [])).filter(Boolean);
	uniqueCheckIds.forEach((checkId) => {
		const check = CHECKS.find((item) => item.id === checkId);
		const patterns = CHECK_HIGHLIGHTS[checkId];
		if (!patterns || !check) return;
		patterns.forEach((pattern) => {
			const regex = new RegExp(pattern.source, pattern.flags);
			let found;
			while ((found = regex.exec(text))) {
				if (found[0].length === 0) break;
				matches.push({
					start: found.index,
					end: found.index + found[0].length,
					accent: check.accent,
				});
				if (!regex.global) break;
			}
		});
	});

	matches.sort((a, b) => (a.start - b.start) || (b.end - b.start) - (a.end - a.start));
	const merged = [];
	let cursor = 0;
	for (const match of matches) {
		if (match.start < cursor) continue;
		merged.push(match);
		cursor = match.end;
	}

	if (merged.length === 0) return <>{text}</>;

	const nodes = [];
	let position = 0;
	merged.forEach((match, index) => {
		if (match.start > position) nodes.push(text.slice(position, match.start));
		nodes.push(
			<mark key={`${match.start}-${index}`} className={`rounded px-1 py-0.5 bg-[var(--ui-accent-soft)] ring-2 ring-inset ${ACCENT_RING[match.accent] ?? 'ring-[var(--ui-border-strong)]'}`}>
				{text.slice(match.start, match.end)}
			</mark>,
		);
		position = match.end;
	});
	if (position < text.length) nodes.push(text.slice(position));

	return <>{nodes}</>;
}

function App() {
	const [aboutOpen, setAboutOpen] = useState(false);
	const [activeView, setActiveView] = useState('data');
	const [datasetId, setDatasetId] = useState(DATASETS[0].id);
	const [query, setQuery] = useState('');
	const [categoryFilter, setCategoryFilter] = useState('all');
	const [emptyOnly, setEmptyOnly] = useState(false);
	const [selectedId, setSelectedId] = useState('');
	const [showStageDetails, setShowStageDetails] = useState(false);
	const [copied, setCopied] = useState(false);
	const [modalRow, setModalRow] = useState(null);
	const [modalCheckId, setModalCheckId] = useState('');
	const dataset = DATASETS.find((item) => item.id === datasetId) ?? DATASETS[0];
	const rows = dataset.rows;
	const noFindingCount = rows.filter((row) => row.expected_categories.length === 0).length;
	const filteredRows = useMemo(() => {
		const needle = query.trim().toLowerCase();
		return rows.filter((row) => {
			const matchesCategory = categoryFilter === 'all' || row.expected_categories.includes(categoryFilter);
			const matchesEmpty = !emptyOnly || row.expected_categories.length === 0;
			const matchesSearch = !needle || `${row.id} ${row.conversation} ${row.notes}`.toLowerCase().includes(needle);
			return matchesCategory && matchesEmpty && matchesSearch;
		});
	}, [rows, query, categoryFilter, emptyOnly]);
	const selectedRow = filteredRows.find((row) => row.id === selectedId) ?? filteredRows[0];
	const maxCount = Math.max(1, ...CHECKS.map((check) => categoryCount(rows, check.id)));

	const selectDataset = (id) => {
		setDatasetId(id);
		setSelectedId('');
		setQuery('');
		setCategoryFilter('all');
		setEmptyOnly(false);
	};

	const runCommand = `uv run python -m app.evaluation.while_report --dataset src/app/evaluation/datasets/${dataset.file}`;
	const trackCommand = `${runCommand} --track`;
	const copyCommand = async () => {
		await navigator.clipboard.writeText(trackCommand);
		setCopied(true);
		window.setTimeout(() => setCopied(false), 1800);
	};

	useEffect(() => {
		const modalOpen = aboutOpen || Boolean(modalRow) || Boolean(modalCheckId);
		if (!modalOpen) return;
		const previousOverflow = document.body.style.overflow;
		document.body.style.overflow = 'hidden';
		return () => {
			document.body.style.overflow = previousOverflow;
		};
	}, [aboutOpen, modalRow, modalCheckId]);

	const openConversationModal = (row) => {
		if (!row) return;
		setModalRow(row);
	};

	const openCheckModal = (checkId) => {
		if (!checkId) return;
		setModalCheckId(checkId);
	};

	const closeModals = () => {
		setModalRow(null);
		setModalCheckId('');
	};

	const modalCheck = CHECKS.find((item) => item.id === modalCheckId);
	const modalCheckRows = modalCheck ? rows.filter((row) => row.expected_categories.includes(modalCheck.id)) : [];
	const activeHighlightChecks = categoryFilter === 'all' ? (selectedRow?.expected_categories ?? []) : [categoryFilter];

	return (
		<div className="min-h-screen bg-[var(--ui-bg)] text-[var(--ui-text)]">
			<Modal open={aboutOpen} title="While eval workflow" onClose={() => setAboutOpen(false)}>
				<div className="max-w-[920px] text-sm leading-6 text-[var(--ui-text)]">
					<p className="text-[13px] text-[var(--ui-muted)]">
						Use <span className="font-semibold text-[var(--ui-accent)]">whileai</span> to build better evals for VeritasAgent.
						Keep the workflow tight: simulate → grade → measure → select → train. Track runs with an experiment question first, consistent naming, points (not fractions), one chart, and failed rows attached.
					</p>

					<div className="mt-5 grid gap-3">
						<div className="rounded-xl border border-[var(--ui-border)] bg-[var(--ui-panel)] p-4">
							<div className="text-xs font-semibold uppercase tracking-[.16em] text-[var(--ui-accent)]">Paste into your coding agent</div>
							<CodeBlock>{`Use whileai to build me better evals for my agent.

1. Install it: uv add whileai
2. Follow this skill: https://github.com/whilehq/whileai-sdk/blob/main/skills/strengthen-your-evals/SKILL.md
3. Read the docs at docs.while.ai when you need more.
4. You know my repo best: name the agent, behaviors and versions in its words. Rules: https://docs.while.ai/platform/naming
5. Before a second version, a sweep or a training run, follow https://docs.while.ai/platform/experiments: the question first, then per run five lines (Changed, Moved, Why, Learned, Reproduce), one chart, the rows that failed, points not fractions; then readback(tracked) reads the page the way I will.`}</CodeBlock>
						</div>

						<div className="rounded-xl border border-[var(--ui-border)] bg-[var(--ui-panel)] p-4">
							<div className="text-xs font-semibold uppercase tracking-[.16em] text-[var(--ui-accent)]">Run locally</div>
							<p className="mt-1 text-[13px] text-[var(--ui-muted)]">
								Run a local report, or add <span className="font-semibold">--track</span> to post a baseline run to your signed-in While account.
							</p>
							<CodeBlock>{runCommand}</CodeBlock>
							<CodeBlock>{trackCommand}</CodeBlock>
						</div>
					</div>
				</div>
			</Modal>
			<aside className="fixed inset-y-0 left-0 z-20 hidden w-[226px] flex-col bg-[var(--ui-sidebar)] px-4 py-5 overflow-y-auto lg:flex">
				<a className="flex items-center gap-3 px-2" href="#overview" onClick={() => setActiveView('data')}>
					<div className="flex size-9 items-center justify-center rounded-xl bg-[#d100a8] text-white"><ShieldCheck size={19} /></div>
					<div><div className="text-[15px] font-semibold tracking-tight">veritasAgt</div></div>
				</a>
				<div className="mt-10 px-2 text-[10px] font-semibold uppercase tracking-[.16em] text-[var(--ui-muted-2)]">Workspace</div>
				<nav className="mt-3 space-y-1">
					<NavItem icon={Database} active={activeView === 'data'} onClick={() => setActiveView('data')}>Data explorer</NavItem>
					<NavItem icon={FileCheck2} active={activeView === 'checks'} onClick={() => setActiveView('checks')}>Checks <span className="ml-auto rounded-md bg-[var(--ui-accent-soft)] px-1.5 py-0.5 text-[10px] text-[var(--ui-muted)]">10</span></NavItem>
				</nav>
				<div className="mt-9 px-2 text-[10px] font-semibold uppercase tracking-[.16em] text-[var(--ui-muted-2)]">Datasets</div>
				<div className="mt-3 space-y-1">
					{DATASETS.map((item) => <button key={item.id} onClick={() => { selectDataset(item.id); setActiveView('data'); }} className={`flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs transition ${datasetId === item.id ? 'bg-[var(--ui-accent-soft)] font-medium text-[var(--ui-accent)]' : 'text-[var(--ui-muted)] hover:bg-[var(--ui-panel-muted)]'}`}><span className={`size-1.5 rounded-full ${datasetId === item.id ? 'bg-[var(--ui-accent)]' : 'bg-[var(--ui-border-strong)]'}`} />{item.shortName}<span className="ml-auto text-[10px] text-[var(--ui-muted-2)]">{item.rows.length}</span></button>)}
				</div>
				<div className="mt-auto rounded-xl border border-[var(--ui-border)] bg-[var(--ui-panel)] p-3">
					<div className="flex items-center gap-2 text-xs font-medium"><Activity size={14} className="text-[var(--ui-accent)]" />Local evaluation</div>
				<p className="mt-1.5 text-[10px] leading-4 text-[var(--ui-muted)]">Run the While-style evaluator locally (or track to While).</p>
				<button onClick={copyCommand} title={trackCommand} className="mt-2 inline-flex items-center gap-2 whitespace-nowrap text-[10px] font-semibold text-[var(--ui-accent)] hover:text-[var(--ui-accent-hover)]"><span>{copied ? 'Copied' : 'Run command'}</span><span className="inline-flex items-center">{copied ? <Check size={12} /> : <Copy size={12} />}</span></button>
				</div>
			</aside>

			<div className="lg:pl-[226px]">
				<header className="sticky top-0 z-10 flex h-[58px] items-center justify-between border-b border-[var(--ui-border)] bg-[var(--ui-panel-muted)] px-5 md:px-8">
					<div className="flex items-center gap-2 text-xs text-[var(--ui-muted-2)]"><span className="font-medium text-[var(--ui-text)]">Veritas</span><ChevronRight size={13} /><span>{activeView === 'data' ? 'Data explorer' : 'Checks'}</span></div>
					<div className="flex items-center gap-2"><span className="hidden rounded-full border border-[var(--ui-border)] bg-[var(--ui-panel)] px-2.5 py-1 text-[10px] text-[var(--ui-muted)] sm:inline-flex">OFFLINE · PROVIDER NONE</span><button onClick={() => setAboutOpen(true)} aria-label="While eval workflow" title="While eval workflow" className="flex size-8 items-center justify-center rounded-lg border border-[var(--ui-border)] bg-[var(--ui-panel)] text-[var(--ui-muted)] hover:text-[var(--ui-accent)]"><CircleHelp size={15} /></button><div className="flex size-8 items-center justify-center rounded-full bg-[#d100a8] text-[10px] font-semibold text-white">VA</div></div>
				</header>

				<main className="mx-auto max-w-[1440px] px-5 pb-12 pt-7 md:px-8 md:pt-9">
					<div className="mb-5 flex gap-2 lg:hidden">
						<button onClick={() => setActiveView('data')} className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs ${activeView === 'data' ? 'bg-[var(--ui-accent-soft)] font-medium text-[var(--ui-accent)]' : 'border border-[var(--ui-border)] bg-[var(--ui-panel)] text-[var(--ui-muted)]'}`}><Database size={14} />Data</button>
						<button onClick={() => setActiveView('checks')} className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs ${activeView === 'checks' ? 'bg-[var(--ui-accent-soft)] font-medium text-[var(--ui-accent)]' : 'border border-[var(--ui-border)] bg-[var(--ui-panel)] text-[var(--ui-muted)]'}`}><FileCheck2 size={14} />Checks</button>
					</div>
					{activeView === 'data' ? (
						<>
							<div className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
								<div><div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.17em] text-[var(--ui-accent)]"><Sparkles size={12} />Evaluation data</div><h1 className="text-[27px] font-semibold tracking-[-.04em] md:text-[32px]">A closer look at Veritas.</h1><p className="mt-2 max-w-[600px] text-sm leading-6 text-[var(--ui-muted)]">Explore the conversations and expected checks behind your evaluation sets.</p></div>
								<select value={datasetId} onChange={(event) => selectDataset(event.target.value)} className="self-start rounded-lg border border-[var(--ui-border)] bg-[var(--ui-panel)] px-3 py-2 text-xs text-[var(--ui-text)] outline-none md:self-auto">{DATASETS.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.rows.length} rows</option>)}</select>
							</div>

							<div className="mt-7 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
								<StatCard icon={Database} label="Conversations" value={rows.length} detail={dataset.file} />
								<StatCard icon={Layers3} label="Check behaviors" value={CHECKS.length} detail="Expected category labels" />
								<StatCard icon={ShieldCheck} label="No finding expected" value={noFindingCount} detail={`${rows.length ? Math.round((noFindingCount / rows.length) * 100) : 0}% of this dataset`} />
								<StatCard icon={Activity} label="Analysis stages" value={ANALYSIS_STAGES.length} detail="Used by the local pipeline" />
							</div>

							<div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(330px,.8fr)]">
								<section className="overflow-hidden rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-panel)]">
									<div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--ui-border)] bg-[var(--ui-panel-muted)] px-5 py-4 md:px-6"><div><h2 className="text-sm font-semibold">Expected check coverage</h2><p className="mt-1 text-xs text-[var(--ui-muted)]">Conversations labeled for each behavior</p></div><div className="rounded-md bg-[var(--ui-panel)] px-2 py-1 text-[10px] text-[var(--ui-muted)]">{rows.length} conversations</div></div>
									<div className="space-y-0.5 px-5 py-3 md:px-6">{CHECKS.map((check) => {
										const count = categoryCount(rows, check.id);
										return <button key={check.id} onClick={() => { setCategoryFilter(categoryFilter === check.id ? 'all' : check.id); setEmptyOnly(false); }} className={`group grid w-full grid-cols-[minmax(130px,1fr)_minmax(80px,1.35fr)_42px] items-center gap-3 rounded-lg px-2 py-2 text-left transition hover:bg-[var(--ui-panel-muted)] ${categoryFilter === check.id ? 'bg-[var(--ui-accent-soft)]' : ''}`}><span className="truncate text-xs text-[var(--ui-text)] group-hover:text-[var(--ui-accent)]">{check.short}</span><span className="h-1.5 overflow-hidden rounded-full bg-[var(--ui-accent-soft)]"><span className="block h-full rounded-full bg-[var(--ui-accent)]" style={{ width: `${Math.max(count ? 3 : 0, (count / maxCount) * 100)}%` }} /></span><span className="text-right font-mono text-[11px] text-[var(--ui-muted)]">{count}</span></button>;
									})}</div>
									<div className="flex items-center justify-between border-t border-[var(--ui-border)] px-6 py-3 text-[10px] text-[var(--ui-muted-2)]"><span>Rows may carry more than one expected label.</span><button onClick={() => { setCategoryFilter('all'); setEmptyOnly(false); }} className="font-medium text-[var(--ui-accent)] hover:text-[var(--ui-accent-hover)]">Clear filter</button></div>
								</section>
								<section className="rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-panel)] p-5 md:p-6">
									<div className="flex items-start justify-between"><div><h2 className="text-sm font-semibold">About this set</h2><p className="mt-1 text-xs text-[var(--ui-muted)]">Source and limits</p></div><span className="flex size-8 items-center justify-center rounded-lg bg-[var(--ui-accent-soft)] text-[var(--ui-accent)]"><CircleHelp size={15} /></span></div>
									<p className="mt-5 text-[13px] leading-6 text-[var(--ui-muted)]">{dataset.description}</p>
									{dataset.id === 'heldout-500' && <div className="mt-4 rounded-xl border border-[var(--ui-border-strong)] bg-[var(--ui-panel)] p-3.5"><div className="flex items-center gap-2 text-xs font-medium text-[var(--ui-accent)]"><span className="size-1.5 rounded-full bg-[var(--ui-accent)]" />Diagnostic only</div><p className="mt-1.5 text-[11px] leading-5 text-[var(--ui-muted)]">Repeated templates mean these 500 rows should not be treated as 500 independent real conversations.</p></div>}
										<div className="mt-5 border-t border-[var(--ui-border)] pt-4"><div className="mb-3 text-[10px] font-semibold uppercase tracking-[.14em] text-[var(--ui-muted-2)]">Pipeline stages</div><button onClick={() => setShowStageDetails(!showStageDetails)} className="flex w-full items-center justify-between text-left text-xs text-[var(--ui-text)]"><span className="flex items-center gap-2"><span className="flex -space-x-1">{ANALYSIS_STAGES.slice(0, 4).map((stage) => <span key={stage} className="size-5 rounded-full border-2 border-[var(--ui-accent)] bg-white ring-2 ring-[var(--ui-border)]" />)}</span>{ANALYSIS_STAGES.length} stages</span><ChevronDown size={14} className={`transition-transform ${showStageDetails ? 'rotate-180' : ''}`} /></button>{showStageDetails && <div className="mt-3 grid grid-cols-2 gap-2">{ANALYSIS_STAGES.map((stage, i) => <div key={stage} className="flex items-center gap-2 text-[10px] text-[var(--ui-muted)]"><span className="font-mono text-[var(--ui-muted-2)]">0{i + 1}</span>{stage}</div>)}</div>}</div>
									</section>
							</div>

							<section className="mt-5 overflow-hidden rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-panel)]">
													<div className="flex flex-col justify-between gap-4 border-b border-[var(--ui-border)] bg-[var(--ui-panel-muted)] px-5 py-4 md:flex-row md:items-center md:px-6"><div><h2 className="text-sm font-semibold">Conversation rows</h2><p className="mt-1 text-xs text-[var(--ui-muted)]">Showing {filteredRows.length} of {rows.length} examples</p></div><div className="flex flex-wrap items-center gap-2"><label className="flex h-9 min-w-[220px] items-center gap-2 rounded-lg border border-[var(--ui-border)] bg-[var(--ui-panel)] px-3 text-[var(--ui-muted-2)]"><Search size={14} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search conversations…" className="w-full bg-white text-xs text-[var(--ui-text)] outline-none placeholder:text-[var(--ui-muted-2)]" /></label><select value={categoryFilter} onChange={(event) => { setCategoryFilter(event.target.value); setEmptyOnly(false); }} className="h-9 rounded-lg border border-[var(--ui-border)] bg-[var(--ui-panel)] px-2.5 text-xs text-[var(--ui-text)] outline-none"><option value="all">All checks</option>{CHECKS.map((check) => <option key={check.id} value={check.id}>{check.short}</option>)}</select><button onClick={() => { setEmptyOnly(!emptyOnly); setCategoryFilter('all'); }} className={`flex h-9 items-center gap-1.5 rounded-lg border px-2.5 text-xs ${emptyOnly ? 'border-[var(--ui-border-strong)] bg-[var(--ui-accent-soft)] text-[var(--ui-accent)]' : 'border-[var(--ui-border)] bg-[var(--ui-panel)] text-[var(--ui-muted)]'}`}><Filter size={13} />No finding</button></div></div>
									<div className="grid min-h-[420px] xl:grid-cols-[minmax(0,1.45fr)_minmax(300px,.75fr)]">
										<div className="max-h-[560px] overflow-auto scrollbar-thin"><table className="w-full min-w-[600px] text-left"><thead className="sticky top-0 z-[1] bg-[var(--ui-panel-muted)]"><tr className="border-b border-[var(--ui-border)] text-[10px] font-medium uppercase tracking-[.1em] text-[var(--ui-muted-2)]"><th className="px-5 py-3 font-medium md:px-6">Conversation</th><th className="px-3 py-3 font-medium">Expected checks</th><th className="px-4 py-3 font-medium text-right">Explore</th></tr></thead><tbody>{filteredRows.map((row) => <tr key={row.id} onClick={() => { setSelectedId(row.id); openConversationModal(row); }} className={`cursor-pointer border-b border-[var(--ui-border)] transition hover:bg-[var(--ui-panel-muted)] ${selectedRow?.id === row.id ? 'bg-[var(--ui-accent-soft)]' : ''}`}><td className="max-w-[360px] px-5 py-3.5 md:px-6"><div className="truncate font-mono text-[10px] text-[var(--ui-muted-2)]">{row.id}</div><div className="mt-1 truncate text-xs text-[var(--ui-text)]">{previewConversation(row.conversation)}</div></td><td className="px-3 py-3.5"><div className="flex max-w-[330px] flex-wrap gap-1">{row.expected_categories.length ? row.expected_categories.slice(0, 3).map((id) => { const check = CHECKS.find((item) => item.id === id); return <Tag key={id} color={check?.accent}>{check?.short ?? id}</Tag>; }) : <Tag>No finding</Tag>}{row.expected_categories.length > 3 && <span className="px-1 py-1 text-[10px] text-[var(--ui-muted)]">+{row.expected_categories.length - 3}</span>}</div></td><td className="px-4 py-3.5 text-right"><button aria-label="Open conversation" title="Open conversation" onClick={(event) => { event.stopPropagation(); openConversationModal(row); }} className="ml-auto inline-flex items-center justify-center rounded-lg border border-[var(--ui-border)] bg-[var(--ui-panel)] px-2 py-1 text-[10px] text-[var(--ui-muted)] hover:text-[var(--ui-accent)]"><ArrowUpRight size={12} /></button></td></tr>)}</tbody></table>{filteredRows.length === 0 && <div className="px-6 py-14 text-center text-sm text-[var(--ui-muted)]">No conversations match those filters.</div>}</div>
									<CaseDetail row={selectedRow} highlightChecks={activeHighlightChecks} onExplore={() => openConversationModal(selectedRow)} onOpenCheck={openCheckModal} />
									</div>
								</section>
							</>
					) : <ChecksView rows={rows} onFilter={(id) => { setActiveView('data'); setCategoryFilter(id); setEmptyOnly(false); }} onOpenCheck={openCheckModal} />}
				</main>
			</div>

			<Modal open={Boolean(modalRow)} title={modalRow ? `Conversation · ${modalRow.id}` : ''} onClose={closeModals}>
				{modalRow && (
					<>
						<div className="rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-panel)] p-4">
							<div className="mb-2 text-[10px] font-semibold uppercase tracking-[.12em] text-[var(--ui-muted-2)]">Conversation</div>
							<p className="whitespace-pre-wrap text-[13px] leading-6 text-[var(--ui-text)]">
								<HighlightedText text={modalRow.conversation} checkIds={modalRow.expected_categories} />
							</p>
						</div>

						<div className="mt-4 rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-panel)] p-4">
							<div className="flex items-center justify-between">
								<div className="text-[10px] font-semibold uppercase tracking-[.14em] text-[var(--ui-muted-2)]">Expected checks</div>
								<span className="font-mono text-[10px] text-[var(--ui-muted-2)]">{modalRow.expected_categories.length} labels</span>
							</div>
							<div className="mt-2 flex flex-wrap gap-1.5">
								{modalRow.expected_categories.length ? modalRow.expected_categories.map((id) => {
									const check = CHECKS.find((item) => item.id === id);
									return (
										<button key={id} onClick={() => openCheckModal(id)} className="rounded-md">
											<Tag color={check?.accent}>{check?.short ?? id}</Tag>
										</button>
									);
								}) : <Tag>No finding expected</Tag>}
							</div>
							{modalRow.notes && (
								<div className="mt-4 rounded-xl border border-[var(--ui-border)] bg-[var(--ui-panel-muted)] p-3.5">
									<div className="text-[10px] font-semibold uppercase tracking-[.12em] text-[var(--ui-muted-2)]">Label note</div>
									<p className="mt-1.5 text-[11px] leading-5 text-[var(--ui-muted)]">{modalRow.notes}</p>
								</div>
							)}
							<div className="mt-3 text-[10px] text-[var(--ui-muted)]">Highlights are heuristic and meant for quick scanning.</div>
						</div>
					</>
				)}
			</Modal>

			<Modal open={Boolean(modalCheck)} title={modalCheck ? `Check · ${modalCheck.short}` : ''} onClose={closeModals}>
				{modalCheck && (
					<>
						<div className="rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-panel)] p-4">
							<div className="flex flex-wrap items-start justify-between gap-3">
								<div>
									<div className="text-[10px] font-semibold uppercase tracking-[.14em] text-[var(--ui-muted-2)]">Behavior</div>
									<div className="mt-1 text-sm font-semibold">{modalCheck.name}</div>
									<p className="mt-2 text-xs leading-5 text-[var(--ui-muted)]">{modalCheck.description}</p>
								</div>
								<div className="text-right">
									<Tag color={modalCheck.accent}>{modalCheckRows.length} rows</Tag>
									<div className="mt-2 text-[9px] font-semibold uppercase tracking-[.13em] text-[var(--ui-muted-2)]">Focused tests</div>
									<div className="mt-1 flex flex-wrap justify-end gap-1.5">
										{modalCheck.tests.map((test) => <span key={test} className="rounded-md bg-[var(--ui-panel-muted)] px-2 py-1 font-mono text-[9px] text-[var(--ui-muted)]">{test}</span>)}
									</div>
								</div>
							</div>
						</div>

						<div className="mt-4 rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-panel)]">
							<div className="flex items-center justify-between border-b border-[var(--ui-border)] bg-[var(--ui-panel-muted)] px-4 py-3">
								<div className="text-xs font-semibold">Labeled conversations</div>
								<div className="text-[10px] text-[var(--ui-muted)]">Click to explore</div>
							</div>
							<div className="max-h-[46vh] overflow-auto">
								{modalCheckRows.slice(0, 40).map((row) => (
									<button key={row.id} onClick={() => { openConversationModal(row); setModalCheckId(''); }} className="block w-full border-b border-[var(--ui-border)] px-4 py-3 text-left hover:bg-[var(--ui-panel-muted)]">
										<div className="font-mono text-[10px] text-[var(--ui-muted-2)]">{row.id}</div>
										<div className="mt-1 max-h-10 overflow-hidden text-xs text-[var(--ui-text)]">
											<HighlightedText text={row.conversation.replaceAll('\n', ' ')} checkIds={[modalCheck.id]} />
										</div>
									</button>
								))}
								{modalCheckRows.length > 40 && <div className="px-4 py-3 text-[10px] text-[var(--ui-muted)]">Showing first 40 rows.</div>}
								{modalCheckRows.length === 0 && <div className="px-4 py-6 text-sm text-[var(--ui-muted)]">No rows in this dataset.</div>}
							</div>
						</div>
					</>
				)}
			</Modal>
		</div>
	);
}

function NavItem({ icon: Icon, active, onClick, children }) {
	return <button onClick={onClick} className={`flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2.5 text-left text-xs transition ${active ? 'bg-[var(--ui-accent-soft)] font-semibold text-[var(--ui-accent)]' : 'text-[var(--ui-muted)] hover:bg-[var(--ui-panel-muted)]'}`}><Icon size={15} strokeWidth={1.8} />{children}</button>;
}

function StatCard({ icon: Icon, label, value, detail }) {
	return <div className="rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-panel)] p-4"><div className="flex items-center justify-between"><span className="text-[11px] text-[var(--ui-muted)]">{label}</span><span className="flex size-7 items-center justify-center rounded-lg bg-[var(--ui-accent-soft)] text-[var(--ui-accent)]"><Icon size={14} /></span></div><div className="mt-3 flex items-baseline gap-2"><span className="text-[25px] font-semibold tracking-[-.04em]">{value}</span>{label === 'Conversations' && <span className="inline-flex items-center gap-0.5 text-[10px] text-[var(--ui-muted)]"><ArrowUpRight size={11} /> dataset</span>}</div><div className="mt-1 truncate text-[10px] text-[var(--ui-muted-2)]">{detail}</div></div>;
}

function CaseDetail({ row, highlightChecks = [], onExplore, onOpenCheck }) {
	if (!row) {
		return (
			<div className="flex items-center justify-center border-t border-[var(--ui-border)] p-8 text-xs text-[var(--ui-muted)] xl:border-l xl:border-t-0">
				Select a conversation to inspect it.
			</div>
		);
	}

	return (
		<aside className="border-t border-[var(--ui-border)] bg-[var(--ui-panel-muted)] p-5 md:p-6 xl:border-l xl:border-t-0">
			<div className="flex items-start justify-between gap-3">
				<div>
					<div className="text-[10px] font-semibold uppercase tracking-[.14em] text-[var(--ui-muted-2)]">Selected conversation</div>
					<h3 className="mt-1.5 break-all font-mono text-xs font-medium text-[var(--ui-text)]">{row.id}</h3>
				</div>
				<div className="flex items-center gap-2">
					<button onClick={onExplore} className="rounded-lg border border-[var(--ui-border)] bg-[var(--ui-panel)] px-2.5 py-1 text-[10px] font-medium text-[var(--ui-muted)] hover:text-[var(--ui-accent)]">Explore</button>
					<span className="rounded-md border border-[var(--ui-border)] bg-[var(--ui-panel)] px-2 py-1 text-[10px] text-[var(--ui-muted)]">reference</span>
				</div>
			</div>

			<div className="mt-5 rounded-xl border border-[var(--ui-border)] bg-[var(--ui-panel)] p-4">
				<div className="mb-2 text-[10px] font-medium uppercase tracking-[.12em] text-[var(--ui-muted-2)]">Conversation</div>
				<p className="whitespace-pre-wrap text-[13px] leading-6 text-[var(--ui-text)]">
					<HighlightedText text={row.conversation} checkIds={highlightChecks.length ? highlightChecks : row.expected_categories} />
				</p>
			</div>

			<div className="mt-5">
				<div className="flex items-center justify-between">
					<div className="text-[10px] font-semibold uppercase tracking-[.14em] text-[var(--ui-muted-2)]">Expected checks</div>
					<span className="font-mono text-[10px] text-[var(--ui-muted-2)]">{row.expected_categories.length} labels</span>
				</div>
				<div className="mt-2 flex flex-wrap gap-1.5">
					{row.expected_categories.length ? row.expected_categories.map((id) => {
						const check = CHECKS.find((item) => item.id === id);
						return (
							<button key={id} onClick={() => onOpenCheck?.(id)} className="rounded-md">
								<Tag color={check?.accent}>{check?.short ?? id}</Tag>
							</button>
						);
					}) : <Tag>No finding expected</Tag>}
				</div>
			</div>

			{row.notes && (
				<div className="mt-5 rounded-xl border border-[var(--ui-border)] bg-[var(--ui-panel)] p-3.5">
					<div className="text-[10px] font-semibold uppercase tracking-[.12em] text-[var(--ui-muted-2)]">Label note</div>
					<p className="mt-1.5 text-[11px] leading-5 text-[var(--ui-muted)]">{row.notes}</p>
				</div>
			)}

			<div className="mt-5 flex items-start gap-2 border-t border-[var(--ui-border)] pt-4 text-[10px] leading-5 text-[var(--ui-muted-2)]">
				<CircleHelp size={13} className="mt-0.5 shrink-0" />
				<span>Highlights are heuristic; open the modal for more detail.</span>
			</div>
		</aside>
	);
}

function ChecksView({ rows, onFilter, onOpenCheck }) {
	return <>
		<div className="flex flex-col justify-between gap-5 md:flex-row md:items-end"><div><div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.17em] text-[var(--ui-accent)]"><FileCheck2 size={12} />Behavior map</div><h1 className="text-[27px] font-semibold tracking-[-.04em] md:text-[32px]">What Veritas checks for.</h1><p className="mt-2 max-w-[600px] text-sm leading-6 text-[var(--ui-muted)]">Evaluation behaviors, the cases that exercise them, and the focused Python tests.</p></div><Tag color="rose">{CHECKS.length} labeled behaviors</Tag></div>
		<div className="mt-7 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{CHECKS.map((check, index) => { const count = categoryCount(rows, check.id); return <article key={check.id} className="rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-panel)] p-5 transition hover:border-[var(--ui-border-strong)]"><div className="flex items-start justify-between"><div className="flex size-9 items-center justify-center rounded-xl bg-[var(--ui-accent-soft)] text-[var(--ui-accent)]"><span className="font-mono text-xs">{String(index + 1).padStart(2, '0')}</span></div><Tag color={check.accent}>{count} rows</Tag></div><h2 className="mt-4 text-sm font-semibold">{check.name}</h2><p className="mt-2 min-h-[48px] text-xs leading-5 text-[var(--ui-muted)]">{check.description}</p><div className="mt-4 border-t border-[var(--ui-border)] pt-3"><div className="mb-2 text-[9px] font-semibold uppercase tracking-[.13em] text-[var(--ui-muted-2)]">Focused tests</div><div className="flex flex-wrap gap-1.5">{check.tests.map((test) => <span key={test} className="rounded-md bg-[var(--ui-panel-muted)] px-2 py-1 font-mono text-[9px] text-[var(--ui-muted)]">{test}</span>)}</div></div><div className="mt-4 flex items-center justify-between"><button onClick={() => onFilter(check.id)} className="flex items-center gap-1 text-[11px] font-medium text-[var(--ui-accent)] hover:text-[var(--ui-accent-hover)]">Browse labeled cases<ArrowDownRight size={12} /></button><button onClick={() => onOpenCheck?.(check.id)} className="text-[11px] font-medium text-[var(--ui-muted)] hover:text-[var(--ui-accent)]">Details</button></div></article>; })}</div>
		<div className="mt-6 grid gap-4 lg:grid-cols-[1.2fr_.8fr]"><section className="rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-panel)] p-5"><div className="flex items-center gap-2"><Layers3 size={15} className="text-[var(--ui-accent)]" /><h2 className="text-sm font-semibold">Local analysis stages</h2></div><p className="mt-1 text-xs text-[var(--ui-muted)]">Stages called by the conversation orchestrator</p><div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">{ANALYSIS_STAGES.map((stage, index) => <div key={stage} className="flex items-center gap-2 rounded-lg bg-[var(--ui-panel-muted)] px-3 py-2.5"><span className="font-mono text-[10px] text-[var(--ui-muted-2)]">0{index + 1}</span><span className="text-xs text-[var(--ui-text)]">{stage}</span><Check size={13} className="ml-auto text-[var(--ui-accent)]" /></div>)}</div></section><section className="rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-panel-muted)] p-5"><div className="flex items-center gap-2"><CircleHelp size={15} className="text-[var(--ui-accent)]" /><h2 className="text-sm font-semibold">How to read this page</h2></div><p className="mt-3 text-xs leading-5 text-[var(--ui-muted)]">The case counts show how many rows carry each expected label. They are not pass rates. The linked Python tests exercise focused rules; run the dataset evaluator locally to compare predictions against labels.</p><div className="mt-4 flex items-start gap-2 rounded-lg bg-[var(--ui-accent-soft)] p-3 text-[10px] leading-5 text-[var(--ui-muted)]"><CircleHelp size={13} className="mt-0.5 shrink-0" />The offline pipeline is conservative and does not check external facts. Unsupported claims stay unverified.</div></section></div>
	</>;
}

export default App;
