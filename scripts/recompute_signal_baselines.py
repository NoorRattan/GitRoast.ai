"""Create a versioned population baseline for a scheduled job.

Run without --activate to produce a reviewable candidate. Activation remains an
explicit, auditable admin decision in the protected API.
"""

import asyncio

from app.core.config import get_settings
from app.db.session import close_db, init_db
from app.services.signal_baselines import build_signal_baseline


async def main() -> None:
    settings = get_settings()
    session_factory = init_db(settings)
    try:
        async with session_factory() as db:
            config = await build_signal_baseline(db, "scheduled-job")
            print(f"Created shadow signal baseline {config.version} from {config.sample_size} profiles.")
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
