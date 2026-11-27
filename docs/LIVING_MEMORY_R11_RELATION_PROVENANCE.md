# Living Memory R11.3d — relation provenance and conflict

Base: integrated #8 merge 4f7ebc03fcbf01091ce866e70bc9e65b7ed9014a.
Promote the previously green R11.3c work together with this increment directly
to main, whose observed revision is 3800ab2c6ff1edc42f1a845f6fabdc7865b95979.
No runtime API changes; synthetic only; authority NONE.

## Research contract

A relation assertion contains id, alias, target, exact app and context,
source, provenance root, review state, lifecycle state, issued and expiry.
The fixture resolver validates exact shape, labels, distinct record IDs,
bounded record/withdrawal counts and integer times. Request contains alias,
app, context and time. Withdrawals are a supplied set of record, root or
source labels; they are not an authenticated or durable deletion ledger.
Time is a supplied fixture tick, not a trusted clock.

For an exact scope, use only approved active assertions whose issuance
interval contains the request tick (issued inclusive, expiry exclusive)
and whose record/root/source labels have not been withdrawn. Hold when
no eligible assertion remains or competing targets disagree. A majority
does not override conflict. Require a pair with distinct source AND
distinct root labels. Duplicated lineage or duplicated source labels do
not manufacture a second eligible pair. No transitive relation expansion,
truth inference or authorization. The result contains target or null,
reason, evidence counts and authority NONE.

The resolver does not validate source content, cryptographic signatures,
actual independence, identity, review authority or semantics. Distinct
labels are not independent evidence. The untyped withdrawal label
namespace is deliberately conservative: matching any of record, root or
source removes the assertion. The contract does not establish revocation
history, external custody or permission to publish these counts.

## Executed results

18 authored scenarios, all 18 match the explicitly authored protocol
expectations; 4 admitted, 14 abstained. Among admitted scenarios, 3 match
the authored truth and 1 does not. The forged-consistent-evidence control
has two approved, current, distinct-looking records for the false target
mixer. Both labels are invented, and the resolver admits the false target.
This is an expected counterexample, not a successful truth check.

Controls include duplicated root/source, pending/rejected review, retired
state, expiry and future issuance, wrong app/context, conflict despite a
majority, withdrawal by record/root/source, withdrawal of the conflicting
assertion, unknown alias, and redundant evidence after withdrawal.

No claim of measured retrieval improvement on the R11.3c query corpus:
this is an isolated relation-admission experiment, not an integration
with the ranking implementation. It does not retrospectively repair the
two misleading aliases in the previous benchmark.

## Reproduction

    node research/recall/check-provenance.mjs

The authoring JS environment executed the evaluator and retained the
complete report. The CI check recomputes it, tests permutation invariance,
malformed input, bounds, issuance/expiry edges, withdrawals and isolation
of expected/truth labels from admission. CI results are separate from
the authoring execution.

## Remaining gates

Independent source acquisition and review, independently verified
provenance, actual permission and consent, persistent authenticated
withdrawal, replay and continuity controls, typed namespaces, and
independent evaluation of retrieval quality. Do not use with real data.
No learned relations or new native memory bridge. Next development
priority is coordinated deletion and recovery; semantic retrieval and
production remain HELD.
