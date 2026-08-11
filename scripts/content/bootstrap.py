"""Replace the local quiz catalogue with the audited fourth-grade corpus."""
from __future__ import annotations

import asyncio

from db import init_db
from scripts.content.grade4_audited_v2 import replace_content


async def main() -> None:
    await init_db()
    result = await replace_content()
    print(
        f"Removed questions: {result['removed_questions']}\n"
        f"Imported: {result['imported_questions']}\n"
        f"Packs: {result['packs']}\n"
        "Rejected: 0"
    )


if __name__ == "__main__":
    asyncio.run(main())
