# Content sources

| Source | Usage | Rights status | Count |
| --- | --- | --- | ---: |
| Approved Grade 4 core + starred V1 | The supplied Russian fourth-grade corpus, imported from `content/quiz_grade4.json` | Each record retains its source URL; rights are not independently verified | 500 |
| Approved Grade 4 visual plan V2 | Visual-treatment metadata from `content/visual_plan_grade4.json`; it never changes text, options or answers | No image assets were supplied; generation remains a separate step | 179 planned |
| Existing beta seed | Historical repository data; not loaded by the bootstrap | repository provenance only | 0 active |
| Open Trivia DB / The Trivia API | Research register only; no runtime importer | verify before any use | 0 |

The importer writes a source ID, URL, language and rights-status marker for every active question. Runtime play never requests an external provider. `python -m scripts.content.audit` fails when an active record has missing provenance, duplicate text, invalid answer options, or placeholder distractors.
