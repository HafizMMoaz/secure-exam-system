"""Generate a secure random JWT secret.

Usage examples:
  python backend/tools/generate_jwt_secret.py
  python backend/tools/generate_jwt_secret.py --bytes 48 --format hex

Outputs the secret to stdout.
"""
import argparse
import secrets
import base64


def generate_secret(nbytes: int = 32, fmt: str = "urlsafe") -> str:
    if fmt == "hex":
        return secrets.token_hex(nbytes)
    if fmt == "urlsafe":
        return secrets.token_urlsafe(nbytes)
    if fmt == "base64":
        raw = secrets.token_bytes(nbytes)
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("utf-8")
    raise ValueError("unsupported format")


def main():
    p = argparse.ArgumentParser(description="Generate a secure random JWT secret")
    p.add_argument("--bytes", type=int, default=32, help="number of random bytes (default: 32)")
    p.add_argument(
        "--format",
        choices=["urlsafe", "hex", "base64"],
        default="urlsafe",
        help="output encoding format (default: urlsafe)",
    )
    args = p.parse_args()

    secret = generate_secret(args.bytes, args.format)
    print(secret)


if __name__ == "__main__":
    main()
