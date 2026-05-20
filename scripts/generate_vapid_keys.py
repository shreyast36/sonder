"""
Generate a VAPID keypair for Web Push.

Run once per environment (dev / staging / prod):

    python -m scripts.generate_vapid_keys

Copy the printed VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY into your .env (or
the secret store on ECS / Render). The public key also has to be exposed
to the frontend so the service worker can subscribe — the backend serves
it at GET /api/push/vapid-public-key, so no separate frontend config.
"""

import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def main() -> None:
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key  = private_key.public_key()

    # VAPID uses the uncompressed 65-byte form: 0x04 || X (32) || Y (32),
    # then urlsafe-base64 without padding.
    raw_public = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    raw_private = private_key.private_numbers().private_value.to_bytes(32, "big")

    print("VAPID_PUBLIC_KEY=",  _b64url(raw_public),  sep="")
    print("VAPID_PRIVATE_KEY=", _b64url(raw_private), sep="")
    print("VAPID_SUBJECT=mailto:ops@sonder.app  # change to a real address")


if __name__ == "__main__":
    main()
