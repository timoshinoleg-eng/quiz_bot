# Grade 4 V2 provenance

The active catalogue is the supplied approved fourth-grade corpus in `content/quiz_grade4.json`. Every question has its own `source_url`; the importer copies it to `Question.source_url` and records `quiz_grade4_core_plus_starred_v1` as the source.

The corpus contains five Russian-language subject packs of 100 questions each: Russian language, mathematics, literature reading, world around us, and English. The sources describe the underlying facts and are not reproduced verbatim by the application.

`content/visual_plan_grade4.json` is also validated against the approved question text, options, answer and source URL before its metadata is applied. It cannot alter a correct answer. It marks 74 first-wave visual candidates, 32 second-wave candidates and 73 questions that should be text-only; image assets themselves have not been supplied.

Source URLs are retained for traceability only. Their licence or permission for commercial reuse has not been independently verified, so the database explicitly stores that status. Before adding new material, verify rights and facts, give it an original formulation, provide three distinct distractors, then run the bootstrap and audit gates.
