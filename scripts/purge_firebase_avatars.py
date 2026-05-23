"""
Wipe every blob under cotraveller_avatars/ in Firebase Storage.

Use this before re-seeding to avoid stale avatars from older runs piling
up in the bucket. Pinecone --purge clears the metadata pointers, but
the actual PNGs in Storage are orphaned otherwise.

Usage:
    python -m scripts.purge_firebase_avatars
"""

from __future__ import annotations

import sys

from mushahid.realtime.storage import _get_bucket


def main() -> None:
    if sys.platform == "win32":
        # Avoid Windows asyncio cleanup noise (unused here but consistent
        # with the other seed scripts).
        pass

    bucket = _get_bucket()
    blobs = list(bucket.list_blobs(prefix="cotraveller_avatars/"))
    if not blobs:
        print(f"No blobs under cotraveller_avatars/ in {bucket.name} — nothing to purge.")
        return

    print(f"Found {len(blobs)} blobs under cotraveller_avatars/ in {bucket.name}.")
    # Bulk delete in one request per 100 (GCS supports batch but firebase_admin
    # doesn't expose it cleanly — sequential is fast enough for ~96 blobs).
    for i, blob in enumerate(blobs, 1):
        blob.delete()
        if i % 25 == 0 or i == len(blobs):
            print(f"  deleted {i}/{len(blobs)}")
    print("Done.")


if __name__ == "__main__":
    main()
