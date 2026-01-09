from __future__ import annotations

import asyncio
from src.lang_graph_agent.metrics.db import ENGINE
from src.lang_graph_agent.metrics.models import Base
from dotenv import load_dotenv
load_dotenv()

async def main() -> None:
    async with ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(main())
