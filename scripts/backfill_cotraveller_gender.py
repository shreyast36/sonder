"""
One-shot backfill: patch the missing `gender` field onto every existing
co-traveller persona in Pinecone.

Why this exists
---------------
seed_cotravellers.py used to omit `gender` from the Pinecone metadata
dict (it was only on log_preview). When the same-gender hard filter
shipped in /cotraveller, it rejected every candidate because none
had gender in metadata, and solo users saw "No matches surfaced".

The seed script is fixed going forward, but existing Pinecone records
still lack the field. Re-running the full seed would re-call the LLM
and gpt-image-1 (~$2-4) for no new persona content. This script just
patches metadata via `index.update(set_metadata=...)` — fast, free,
no LLM, no regeneration.

How it works
------------
Rebuilds the deterministic diversity matrix from seed_cotravellers
(every (city, age_bucket, gender, i) tuple → stable profile_id),
then for each slot calls Pinecone's metadata-only update API. Records
that don't exist (matrix expanded between runs) are skipped with a
warning, not an error.

Usage:
    python -m scripts.backfill_cotraveller_gender
    python -m scripts.backfill_cotraveller_gender --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from scripts.seed_cotravellers import build_diversity_matrix
from shreyas.retrieval.client import get_pinecone_index

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("backfill_gender")


async def main(dry_run: bool) -> int:
    slots = build_diversity_matrix()
    log.info("Backfilling gender on %d cotraveller records", len(slots))

    if dry_run:
        for s in slots[:6]:
            log.info("  would set %s.gender = %r  (city=%s, age=%d-%d)",
                     s["profile_id"], s["gender"], s["city"], s["age_lo"], s["age_hi"])
        log.info("  … and %d more", max(0, len(slots) - 6))
        log.info("Dry run — no Pinecone writes. Re-run without --dry-run to apply.")
        return 0

    index = await get_pinecone_index()
    updated = 0
    missing = 0
    failed = 0

    for s in slots:
        pid = s["profile_id"]
        try:
            await asyncio.to_thread(
                lambda p=pid, g=s["gender"]: index.update(
                    id=p,
                    set_metadata={"gender": g},
                    namespace="cotravellers",
                )
            )
            updated += 1
            if updated % 10 == 0:
                log.info("  patched %d / %d", updated, len(slots))
        except Exception as e:
            msg = str(e).lower()
            # Pinecone returns 404 / "not found" when the id doesn't
            # exist — usually means the user partially re-seeded or
            # added matrix entries after the last seed run. Not fatal.
            if "not found" in msg or "404" in msg:
                missing += 1
                log.debug("  skipped missing record %s", pid)
            else:
                failed += 1
                log.warning("  update failed for %s: %s", pid, e)

    log.info("Done — updated=%d missing=%d failed=%d total=%d",
             updated, missing, failed, len(slots))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Print what would change without writing to Pinecone.")
    args = ap.parse_args()
    sys.exit(asyncio.run(main(args.dry_run)))
