"""Utilitários de linha de comando.

    python -m app.cli vapid    # gera o par de chaves VAPID para o .env
"""

import base64
import sys

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def generate_vapid() -> None:
    vapid = Vapid()
    vapid.generate_keys()

    private_raw = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
    public_raw = vapid.public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )

    print("Cole no seu .env:\n")
    print(f"VAPID_PUBLIC_KEY={_b64(public_raw)}")
    print(f"VAPID_PRIVATE_KEY={_b64(private_raw)}")


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] != "vapid":
        print(__doc__)
        return 1
    generate_vapid()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
