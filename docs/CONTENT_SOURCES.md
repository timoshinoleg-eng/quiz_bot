# Content sources

| Source | Usage | License | Commercial status | Count |
| --- | --- | --- | --- | ---: |
| Curated RU V2 | committed offline seed; stable facts, editorial deduplication still pending | CC0-1.0 dedication by this project | blocked from public beta until near-duplicates are replaced | 550 |
| Existing beta seed | legacy local seed retained for compatibility | repository provenance only | not used as a provider | 30 |
| Open Trivia DB | optional future importer only | verify at import time | not imported | 0 |
| The Trivia API | experimental adapter research only | CC BY-NC must not enter production corpus | not imported | 0 |

Every imported question retains its `source`, `source_id`, license and language. Runtime play never fetches an external provider. The two provider rows above are a research register, not implemented import adapters.
