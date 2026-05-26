# Evaluation

## Test Dataset

5 sample documents used for evaluation:
- `company_policy.pdf` — HR policies, 12 pages
- `product_spec.pdf` — Technical product specification, 8 pages
- `meeting_notes.pdf` — Q3 planning meeting notes, 4 pages
- `invoice_template.pdf` — Invoice with line items, 2 pages
- `resume_sample.pdf` — Sample resume, 1 page

20 evaluation questions with expected answer page references are defined in `tests/eval_questions.json` (added in Block 7).

## Metrics to Track

| Metric | Target | Method |
|---|---|---|
| Retrieval hit rate | ≥ 85% (correct chunk in top-3) | Compare retrieved chunk_index to expected |
| Answer accuracy | ≥ 80% | Manual review of 20 questions |
| Citation correctness | ≥ 90% | Check filename + page match expected |
| Fallback rate | < 10% | Count low-confidence responses |
| P95 latency | < 3s | Logged per request |
| Hallucination rate | 0% (verifiable) | All answers traceable to citations |

## Known Limitations

- ChromaDB top-k retrieval is cosine-only; no hybrid BM25 search yet (planned: reranking in Block 4).
- Chunk size of 1000 chars may split tables/code blocks — semantic chunking planned.
- Single-document queries only in MVP; cross-document retrieval may reduce precision.
- No streaming responses yet — full latency before first token shown.

## Results

_To be filled after Block 7 evaluation run._
