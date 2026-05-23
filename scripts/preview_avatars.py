"""
Cheap dry-run for the avatar prompt — generate 5 portraits across a
diverse slice of the seed matrix and dump the PNGs into
./seed_assets/preview/ so we can eyeball the new prompt before paying
to re-render all 224.

Skips persona-infer, emotional-signature, Pinecone, and Firebase
entirely. Only runs LLM-A (to get appearance_descriptor + visual_cue)
and gpt-image-1.

Cost: 5 × ~$0.005 (LLM-A) + 5 × $0.042 (image) ≈ $0.25.

Usage:
    python -m scripts.preview_avatars
    python -m scripts.preview_avatars --quality high   # ~$1 instead
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from scripts.seed_cotravellers import (
    build_diversity_matrix, llm_a_generate, _portrait_prompt, _openai,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("preview_avatars")


# 5 slots chosen to span gender, age, and appearance/accent buckets.
PREVIEW_SLOT_PICKS = [
    {"city": "Tokyo, Japan",   "age_lo": 40, "gender": "female"},
]


def _select_slots() -> list[dict]:
    matrix = build_diversity_matrix()
    picks = []
    for want in PREVIEW_SLOT_PICKS:
        match = next(
            (s for s in matrix
             if s["city"] == want["city"]
             and s["age_lo"] == want["age_lo"]
             and s["gender"] == want["gender"]),
            None,
        )
        if match is None:
            raise RuntimeError(f"could not find slot for {want}")
        picks.append(match)
    return picks


async def _generate_one(slot: dict, quality: str, out_dir: Path, sem: asyncio.Semaphore) -> None:
    import base64
    persona = await llm_a_generate(slot, sem)
    if persona is None:
        log.warning("  LLM-A failed for %s — skipping", slot["profile_id"][-6:])
        return

    descriptor = persona.get("appearance_descriptor", "?")
    cue = persona.get("visual_cue", "?")
    log.info("  slot %s  %s / %s / %d / %s",
             slot["profile_id"][-6:], slot["city"], slot["gender"],
             persona.get("age", 0), descriptor)
    log.info("    cue: %s", cue)

    prompt = _portrait_prompt(persona, slot)
    try:
        resp = await _openai().images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024",
            quality=quality,
            n=1,
        )
        b64 = resp.data[0].b64_json
        if not b64:
            log.warning("    empty b64 — skipping")
            return
        png = base64.b64decode(b64)
    except Exception as e:
        log.warning("    image generation failed: %s", e)
        return

    pid = slot["profile_id"]
    name = f"{pid}_{slot['city'].split(',')[0].replace(' ', '')}_{slot['gender']}_{persona.get('age', 0)}_{quality}.png"
    path = out_dir / name
    path.write_bytes(png)
    log.info("    wrote %s (%d KB)", path, len(png) // 1024)


async def main(quality: str) -> None:
    slots = _select_slots()
    out_dir = Path("seed_assets") / "preview"
    out_dir.mkdir(parents=True, exist_ok=True)
    log.info("Generating %d preview portraits at quality=%s → %s", len(slots), quality, out_dir)
    sem = asyncio.Semaphore(3)
    await asyncio.gather(*(_generate_one(s, quality, out_dir, sem) for s in slots))
    log.info("Done. Open the PNGs in %s to compare.", out_dir)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    p = argparse.ArgumentParser()
    p.add_argument("--quality", choices=["medium", "high"], default="medium")
    args = p.parse_args()
    asyncio.run(main(args.quality))
