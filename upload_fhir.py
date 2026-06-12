#!/usr/bin/env python3

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import jwt
import requests

TOKEN_CACHE_FILE = Path(".oauth_token.json")
TOKEN_REFRESH_SKEW_SECONDS = 60  # refresh 1 minute early


def load_client_secret(secret_file: Optional[Path]) -> str:
    """Load OAuth client secret from a file or CLIENT_SECRET environment variable."""

    if secret_file is not None:
        if not secret_file.is_file():
            print(f"Client secret file not found: {secret_file}", file=sys.stderr)
            sys.exit(1)
        secret = secret_file.read_text().strip()
        if not secret:
            print(f"Client secret file is empty: {secret_file}", file=sys.stderr)
            sys.exit(1)
        return secret

    secret = os.environ.get("CLIENT_SECRET", "").strip()
    if not secret:
        print(
            "Client secret required: set CLIENT_SECRET or pass --client-secret-file",
            file=sys.stderr,
        )
        sys.exit(1)
    return secret


def request_token(client_secret: str):
    """Request a new OAuth2 access token using client_credentials."""

    token_endpoint = os.environ["TOKEN_ENDPOINT"]

    response = requests.post(
        token_endpoint,
        data={
            "grant_type": "client_credentials",
            "scope": "default",
            "client_id": os.environ["CLIENT_ID"],
            "client_secret": client_secret,
        },
        timeout=30,
    )

    response.raise_for_status()

    token_response = response.json()

    access_token = token_response["access_token"]

    TOKEN_CACHE_FILE.write_text(
        json.dumps(token_response, indent=2)
    )

    return access_token


def jwt_is_expired(token):
    """
    Return True if token is expired or about to expire.

    Decodes JWT without signature verification solely
    to inspect the exp claim.
    """
    try:
        claims = jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_exp": False,
            },
        )

        exp = claims.get("exp")
        if not exp:
            return True

        return time.time() >= (exp - TOKEN_REFRESH_SKEW_SECONDS)

    except Exception:
        return True


def get_access_token(client_secret: str):
    """Load cached token if valid; otherwise request a new one."""

    if TOKEN_CACHE_FILE.exists():
        try:
            token_data = json.loads(TOKEN_CACHE_FILE.read_text())
            token = token_data["access_token"]

            if not jwt_is_expired(token):
                return token

        except Exception:
            pass

    return request_token(client_secret)


def submit_fhir_bundle(bundle_path, client_secret: str):
    """Submit a FHIR bundle file."""

    token = get_access_token(client_secret)

    with open(bundle_path, "rb") as f:
        response = requests.post(
            os.environ["FHIR_BASE_URL"],
            headers={
                "Content-Type": "application/fhir+json",
                "Authorization": f"Bearer {token}",
            },
            data=f,
            timeout=300,
        )

    # Retry once if token unexpectedly expired or was revoked
    if response.status_code == 401:
        token = request_token(client_secret)

        with open(bundle_path, "rb") as f:
            response = requests.post(
                os.environ["FHIR_BASE_URL"],
                headers={
                    "Content-Type": "application/fhir+json",
                    "Authorization": f"Bearer {token}",
                },
                data=f,
                timeout=300,
            )

    response.raise_for_status()

    print(f"{bundle_path}: {response.status_code}")


def main():
    parser = argparse.ArgumentParser(
        description="Upload FHIR bundle JSON files to a FHIR server."
    )
    parser.add_argument(
        "--client-secret-file",
        metavar="PATH",
        type=Path,
        help="File containing OAuth client secret (default: CLIENT_SECRET environment variable)",
    )
    parser.add_argument(
        "bundles",
        nargs="+",
        metavar="bundle",
        help="One or more FHIR bundle JSON files to upload",
    )
    args = parser.parse_args()

    client_secret = load_client_secret(args.client_secret_file)

    for bundle_file in args.bundles:
        submit_fhir_bundle(bundle_file, client_secret)


if __name__ == "__main__":
    main()
