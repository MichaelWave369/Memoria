# Memoria repository refresh — R11

Reviewed main 3967a22b650d41a16af09ff061c42ecbdec2de04 and the green but
separate R11.6 qualification PR #14 (ccbb0f762646bb43596b75cea2896fc819c1064a,
workflow 45929914064). This maintenance branch starts from main, not #14;
the two changes should be reviewed and merged independently.

## Reviewed surfaces

README, dependency list, FastAPI routes and authorization, native storage
and keyring, fixture export/retention contracts, operator UI, integration
client, Launchpad entry, local configuration, ignore rules and CI.
No open issues returned by repository-scoped issue search. This is a targeted
source review, not an exhaustive tree census or external security audit.

| Finding | Refresh |
|---|---|
| Original "eternal vault" branding and screenshot placeholders | Current PHI369 research positioning, architecture and evidence links |
| Overbroad privacy and permanent forgetting claims | Explicit text-encryption, logical-deletion, retention and trust limits |
| Stale API examples and endpoint status | Exact current paths, credentials and held routes |
| Client returned error JSON as success | Raise HTTPError on unsuccessful requests; preserve redirect refusal |
| Chroma bundled with routine UI installation | Core/UI/dev/native dependency groups, native Chroma pin unchanged |
| Cached shared SQLite connection in Streamlit | Fresh connection per script execution |
| Raw memory HTML and inert Agentora button | Literal text presentation, remove unimplemented action |
| Mixed-case search and misleading dashboard totals | Casefold search, loaded-view labels and refresh after capture |
| Port probe presented as app discovery | Removed; no unauthenticated app identification |
| Export labeled complete vault | Explicitly limited, potentially decrypted snapshot warning |
| Outdated Launchpad metadata and local artifact rules | Align entry with API 0.1.1, ignore local DB sidecars and exports |
| Historical R11.1 instructions appear current | Historical notice linking to later protocol documents |
| UI not covered in CI | Opt-in synthetic Streamlit AppTest smoke job |

Default Streamlit usage-statistics setting is disabled. This is not a
claim that all third-party dependencies have been independently assessed
for telemetry. The routine installation no longer pulls Chroma; install
requirements-native.txt explicitly for native fixture tests or legacy
helper investigation. This does not delete existing vector files.
Client callers that formerly inspected error JSON must now catch
requests.HTTPError. No dependency-wide latest-version upgrade or
release/tag was performed; compatibility matters more than version churn.

## Remaining risks

Production and sensitive-data use remain HELD. Local operator UI is not
an authenticated multi-user interface. Application-level deletion and
permission mutation, semantic recall and automatic vector writes remain
held. Existing plaintext vectors, external copies, legacy ciphertext
and backup migrations are not addressed here. Metadata and exports may
contain sensitive information. The historical vector helper remains
available to explicit direct callers and is not qualified. Source review
does not establish complete concurrency safety, independent key custody,
trusted rollback witness or physical erasure.

No live application, personal database, existing vault, or external service
was accessed or migrated. New client regressions and the UI smoke test must
run in CI; no local runtime execution was performed during this refresh.
