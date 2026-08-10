# Content sources

| Source | Usage | License | Commercial status | Count |
| --- | --- | --- | --- | ---: |
| Curated RU V2 | committed editorial fact summaries with a per-pack reference URL | Editorial fact summary with cited reference | local audit accepted; live beta still needs platform/deployment smoke | 550 |
| Existing beta seed | legacy local seed retained for compatibility | repository provenance only | not used as a provider | 30 |
| Open Trivia DB | optional future importer only | verify at import time | not imported | 0 |
| The Trivia API | experimental adapter research only | CC BY-NC must not enter production corpus | not imported | 0 |

Every imported question retains its `source`, `source_id`, `source_url`, license and language. The audit fails if an active question has no provenance. Runtime play never fetches an external provider. The two provider rows above are a research register, not implemented import adapters. Pack-to-reference mapping is in [CONTENT_PROVENANCE.md](CONTENT_PROVENANCE.md).
