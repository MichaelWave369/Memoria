# Living Memory R11.3b — frozen retrieval comparison

Base: green R11.3a head 892a7e24f8537c7a767b0cdc4cedf3df8451df97.
Synthetic research only; authority NONE, production HELD.

## Protocol

Twelve authored ASCII documents, 24 authored queries (six literal, six
alias-only, six mixed, six unanswerable), fixed target IDs, and a twelve-edge
hand-authored directed synonym map. No fitting, no independent holdout,
no external data, no real memory. Every method ranks the same documents.
Positive overlap admits; ties break on ascending document ID. Scores
are rounded to twelve decimal places in this JS benchmark. The native
Python Jaccard implementation instead returns exact rational scores.

Five methods: query-token coverage, Jaccard, binary term TF-IDF cosine
(smoothed IDF 1+log((1+N)/(1+df))), Jaccard with one-hop query expansion
(original terms retained), and a same-size relation map with targets
rotated two places across sorted alias keys. The latter is a constructed
negative control, not a randomized statistical test. Expansion receives
additional privileged information; the map was authored with the corpus
and queries, not learned or independently sourced. No ancestry or actual
Altermath/NBG runtime is invoked. The experiment's methods are offline
references, not new application endpoints.

## Executed results

The JavaScript evaluator was executed in the authoring V8 environment
and the exact resulting report is saved as research/recall/results-v1.json.
CI will independently rerun the same evaluator under Node and compare
all report fields. A new Python test checks all 24 native scoped Jaccard
rankings against the frozen results, including an out-of-scope distractor.

| Method | Hit@1 | Hit@3 | MRR@3 | Negative false accepts |
|---|---:|---:|---:|---:|
| Coverage | 12/18 | 12/18 | 0.667 | 3/6 |
| Jaccard | 12/18 | 12/18 | 0.667 | 3/6 |
| TF-IDF | 12/18 | 12/18 | 0.667 | 3/6 |
| Relational Jaccard | 18/18 | 18/18 | 1.000 | 3/6 |
| Shuffled relational | 12/18 | 12/18 | 0.667 | 3/6 |

All six alias-only queries are answered correctly by the authored map;
the shuffled map answers all six incorrectly rather than abstaining.
The conventional methods abstain on all six alias-only queries.
Every method admits three unanswerable topical-overlap queries.
No method passes a strong abstention gate. No thresholds were optimized.

## Cost accounting

Each method compares 288 query/document pairs. Conventional methods
perform 792 query-term intersection probes; expansion methods 960,
plus 66 relation lookups and 14 added query terms. The map adds 254
compact ASCII JSON bytes to the 518 document-text bytes. TF-IDF records
63 document-frequency updates and 256 weighted-term visits.
The report counts selected algorithmic operations, not actual elapsed
time, memory allocations, complete instruction counts or disk cost.
Document tokens are prepared once for the batch, unlike the current
native API which rescans per request. Shared evaluator preparation,
sorting, map authoring, serialization overhead, key custody, encryption,
SQL, HTTP and runtime resource measurements are not included. No speed
or storage superiority claim.

## Reproduction

    node research/recall/check.mjs
    python -m unittest discover -s tests -v

The fixture and per-query results are committed, including negative outcomes.
Earlier PhiMemory9 R0.5 benchmark protocol informed the design; its corpus
and retired ancestors are not reused. Next: independently authored licensed
queries, frozen thresholds, polysemy/ambiguous aliases and equal-information
controls, full per-request cost measurement and privacy review. No automatic
promotion of the relational candidate; semantic/vector routes remain held.
No live stores accessed or modified.
