# Content sources

| Source | Usage | Rights status | Count |
| --- | --- | --- | ---: |
| Audited Grade 4 V2 | The supplied Russian fourth-grade question set, imported from `content/packs/grade4_audited_v2.json` | Each record retains its source URL; rights are not independently verified | 500 |
| Existing beta seed | Historical repository data; not loaded by the bootstrap | repository provenance only | 0 active |
| Open Trivia DB / The Trivia API | Research register only; no runtime importer | verify before any use | 0 |

The importer writes a source ID, URL, language and rights-status marker for every active question. Runtime play never requests an external provider. `python -m scripts.content.audit` fails when an active record has missing provenance, duplicate text, invalid answer options, or placeholder distractors.
