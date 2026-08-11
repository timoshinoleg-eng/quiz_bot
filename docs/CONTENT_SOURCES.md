# Content sources

| Source | Usage | Rights status | Count |
| --- | --- | --- | ---: |
| Approved Grade 4 core + starred V1 | The supplied Russian fourth-grade corpus, imported from `content/quiz_grade4.json` | Each record retains its source URL; rights are not independently verified | 500 |
| Approved Grade 4 visual plan V2 | Visual-treatment metadata from `content/visual_plan_grade4.json`; it never changes text, options or answers | Ten first-wave items are supplied by Visual Pack V1; remaining assets are separate work | 179 planned |
| Quiz visual pack V1 | Exact `question_id` to image-file mapping from `content/visual_assets_manifest.json`; files are served from `frontend/public/quiz-media/` | Supplied local assets | 10 |
| Existing beta seed | Historical repository data; not loaded by the bootstrap | repository provenance only | 0 active |
| Open Trivia DB / The Trivia API | Research register only; no runtime importer | verify before any use | 0 |

The importer writes a source ID, URL, language and rights-status marker for every active question. Runtime play never requests an external provider. `python -m scripts.content.audit` fails when an active record has missing provenance, duplicate text, invalid answer options, or placeholder distractors.
