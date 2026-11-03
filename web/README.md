# Veritas Eval Explorer

Small React and Tailwind interface for browsing the evaluation datasets and their expected labels.

## Run locally

From this directory:

```bash
npm install
npm run dev
```

Vite imports the JSONL datasets directly from `../src/app/evaluation/datasets/`. The explorer shows reference labels and focused Python test files; it does not run the evaluator or display prediction results.

The 500-row set is synthetic and diagnostic. Its cases share templates, so they should not be read as 500 independent real conversations.
