# Curated RU V2 provenance

Each active V2 record is an original short editorial formulation with a source URL retained in the database. The source provides the underlying fact; it is not copied verbatim into the question. The bootstrap assigns the reference for every question in its pack, and the content audit fails when an active record lacks URL or license metadata.

| Pack | Reference |
| --- | --- |
| Космос | NASA |
| Животные | Encyclopaedia Britannica |
| Логика и математика | Khan Academy |
| Страны мира | National Geographic |
| История | Encyclopaedia Britannica |
| Наука | National Geographic |
| Цифровой мир | Computer History Museum |
| Культура | The Met Museum |
| Спорт | Olympic Charter |
| Английский вокруг нас | Cambridge Dictionary |

The exact URLs are stored in `content/packs/curated_ru.py` and copied into `Question.source_url` by `scripts/content/bootstrap.py`. Before a content expansion, the editor must check the target fact against the linked source, write an original Russian question and explanation, provide three distinct distractors, and then run the full bootstrap/audit gate.
