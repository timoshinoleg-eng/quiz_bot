# Content sources

| Source | Usage | License | Commercial status | Count |
| --- | --- | --- | --- | ---: |
| Curated RU V2 | committed offline seed, reviewed stable facts | CC0-1.0 dedication by this project | allowed | 550 |
| Existing beta seed | legacy local seed retained for compatibility | repository provenance only | not used as a provider | 30 |
| Open Trivia DB | optional future importer only | verify at import time | not imported | 0 |
| The Trivia API | experimental adapter research only | CC BY-NC must not enter production corpus | not imported | 0 |

Every imported question retains its `source`, `source_id`, license and language. Runtime play never fetches an external provider.
