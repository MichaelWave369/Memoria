# Living Memory R11.6 — native source qualification dossier

Audited base: 3967a22b650d41a16af09ff061c42ecbdec2de04.
Synthetic research candidate only. Production HELD, authority NONE.

## Evidence register

The following exact PR-head workflows were observed completed successfully.
The merge chain was checked; #4–#6 and #8 merged into intermediate branches,
then were promoted through #7 and #9. This is an observed CI register,
not a fresh independently executed audit.

| PR | Tested head | Workflow run | Scope |
|---|---|---:|---|
| 3 | 41801d7c88688917c369c9fbf9578a0ad0344c33 | 45911677638 | Scoped application API |
| 4 | ae1009eaa1c1064293cc188b089c193059b8937d | 45916931244 | Explicit keyring |
| 5 | 892a7e24f8537c7a767b0cdc4cedf3df8451df97 | 45917765149 | Ephemeral lexical recall |
| 6 | a3ffacb15581e7ea044cc5572ba77a7d231b8eec | 45918363059 | Retrieval comparison |
| 7 | 9ff85ced6e1800ee9e86bae46719b5f585cdf1e7 | 45921883342 | Main promotion |
| 8 | eb688350ccfa0a5aaa27e76d5e5684169d577bba | 45921980818 | Calibration and abstention |
| 9 | 60f644d5c6a73ef1c5a18dd1140269262bd0a95b | 45922352265 | Provenance and promotion |
| 10 | b70e4ce6cba805ab951198dea7c2058b9951bd21 | 45924159252 | Logical deletion |
| 11 | 60a4563a4d3594ff2dd3182c204a022c38089403 | 45925875279 | Native Chroma cleanup |
| 12 | 72427fb11215915947854d076c3ee15086898c3d | 45927309913 | Fresh-process reconciliation |
| 13 | ce9a536bf1df89953e380e278ebbcea1916b5395 | 45928827651 | Retention rollback witness |

Workflow URLs: https://github.com/MichaelWave369/Memoria/actions/runs/{run}.
Review the associated PR and exact test files to reproduce each scope.

## Qualification matrix

| Capability | Evidence | Remaining boundary |
|---|---|---|
| Application authorization | Disposable HTTP regressions | Trusted host/UI, identity provisioning, rate limits |
| Text encryption | Versioned Fernet envelopes and rotation tests | Metadata/backup protection, legacy ciphertext, key custody |
| Lexical recall | Scoped bounded native SQL path | No private semantic embedding qualification |
| Relational ranking | Same-author frozen experiments | Privileged authored maps, false accepts, no live integration |
| Logical forgetting | Atomic intent and ID guard | Entire DB rollback and historical deletes |
| Vector cleanup | Bound Chroma fixture, observed absence | No live collection adoption or physical erasure |
| Restart | Controlled fresh-process tests | Not arbitrary power loss or concurrent writers |
| Continuity | Keyed retention topology and native anchor harness | Not full content integrity or independently administered witness |
| Cross-repo handoff | Metadata-only fixture export | All nine target policy fields remain unknown |

## R11.6 handoff

db/fixture_qualification.py wraps the existing export in a serialized
SQLite transaction. Exact source fixture marker and current explicit
read permission are checked by the unchanged exporter. The wrapper
rejects an existing caller transaction. It returns the unchanged legacy
metadata snapshot, a domain-separated SHA-256 digest of its canonical
JSON, the audited base revision, original adapter revision, blockers,
and HELD/NONE/live_ready=false. The byte budget is checked after
serialization; it is not a hostile-input resource sandbox.

The historical adapter revision 9c480fcaea467615252d347956eac42ff038edf7
identifies the original R0.4 compatibility contract, not the executing
checkout. The audited base identifies the inspected source, not a
cryptographically attested runtime revision. No self-issued receipt
proves trust, consent, review or code identity. The outer digest binds
only the inner snapshot; it does not authenticate the outer fields.
Metadata includes tags and identifiers and is not intrinsically public.
Never supply real user records. No payload or metadata_json export.
No persistent cross-repository memory admission.

The native test passes the unmodified inner snapshot through actual
PhiMemory9 review_snapshot and stage_snapshot at pinned revision
d897308cb0af166bda9c897eac6ed03d8958577d. The existing nine unknown
policy fields stay None and eligibility stays zero. No PhiMemory9
source changes are required for this compatibility experiment.

## Reproduce

    python -m unittest discover -s tests -v
    node research/recall/check.mjs
    node research/recall/check-abstention.mjs
    node research/recall/check-provenance.mjs

Use the existing native CI job (Chroma 1.0.20, pinned PhiMemory9 and
NBGPocketMesh checkouts) for cold process, cleanup, retention and native
handoff tests. The new suite has seven methods, including one opt-in
actual upstream intake test. CI must run before asserting new passes.

## Open gates

Independent security review; actual source permissions and consent;
external key custody; legacy vector and external copy coverage;
independent rollback witness; full content integrity; runtime authority.
The prior source-security blocker is narrowed by specific local fixes,
not discharged for production. No live stores or external deployment.
R12 should inspect the actual SML store and export boundaries, retaining
HELD until equivalent native source and target governance is explicit.
