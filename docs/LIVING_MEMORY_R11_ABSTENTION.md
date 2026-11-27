# Living Memory R11.3c — ambiguity and abstention

Base: integrated #6 merge 9ff85ced6e1800ee9e86bae46719b5f585cdf1e7.
Offline synthetic experiment; no runtime API changes. Authority NONE.

## Protocol

Two authored, document-disjoint fixtures: six calibration documents and
12 calibration queries; twelve evaluation documents and 36 evaluation
queries (20 answerable and 16 unanswerable). Each split has its own
authored alias map; aliases and targets are not independently learned.
The evaluator compares direct and expanded Jaccard ranking, guarded
versions of both, and an always-abstain decision control. All rank the
same documents in each split. The decision control intentionally still
runs ranking; its operation counts are not a minimal abstention baseline.

For each query, original terms and their one-hop alternatives contribute
support if any variant is present. Ranking is Jaccard over the expanded
term set, ties broken by ascending ID. A guarded result refuses
multi-target aliases, insufficient original-term coverage/support,
and tied or insufficient top-score margin. This is not factual inference.

Select each method's gate using calibration only: 18 combinations
(coverage 0.5/0.75/1; margin 0/0.125/0.25; support 1/2).
Minimize wrong plus false-accept decisions, then maximize correct
decisions, then prefer stricter coverage/support/margin. The direct
selection is coverage 0.5, margin 0.25, support 1; relational selection
is coverage 1, margin 0.125, support 2. Calibration has zero errors
for the direct selection but one false accept for the relational
selection. No evaluated grid choice eliminated that relational error.
No evaluation-based threshold changes.

## Executed evaluation

| Method | Correct / 20 | Wrong positive | False accepts / 16 | Abstained positives |
|---|---:|---:|---:|---:|
| Direct | 16 | 1 | 10 | 3 |
| Expanded | 20 | 0 | 13 | 0 |
| Guarded direct | 11 | 0 | 2 | 9 |
| Guarded expanded | 20 | 0 | 2 | 0 |
| Always abstain | 0 | 0 | 0 | 20 |

Guarded expanded rejects all six ambiguous and all six ordinary
negative queries, but admits two of four deliberately misleading
relations: "broken database" and "obsolete memory". Neither support
nor score margin proves a relationship is semantically justified.
The selective error rate is 2/22 for guarded expansion, versus 13/33
for unguarded expansion. Always-abstain has undefined selective error
because it admits nothing. No confidence calibration is claimed.

Selected operation counts: 432 candidate comparisons per method;
960 direct support probes versus 1224 expanded probes, with 80
relation lookups. These omit scoring overlap, sorting, calibration,
map authoring, SQL, encryption, memory allocations and elapsed time.
This is not a performance benchmark.

## Reproduction

    node research/recall/check-abstention.mjs

The authoring environment ran the JS evaluator and retained all rows,
all calibration choices and the evaluation outcomes. CI will compare
the frozen report and check that changing evaluation labels does not
change gate selection. Same-author synthetic fixtures are not external
validation. Relations remain privileged inputs and may encode answers.

Next: explicit relationship provenance, conflict and withdrawal controls,
and independently sourced evaluation before any runtime promotion.
Legacy semantic routes remain held. No live stores accessed or changed.
