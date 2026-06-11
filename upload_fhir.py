#!/usr/bin/env python3

import json
import os
import sys
import time
from pathlib import Path

import jwt
import requests

TOKEN_CACHE_FILE = Path(".oauth_token.json")
TOKEN_REFRESH_SKEW_SECONDS = 60  # refresh 1 minute early


def request_token():
    """Request a new OAuth2 access token using client_credentials."""

    token_endpoint = os.environ["TOKEN_ENDPOINT"]

    response = requests.post(
        token_endpoint,
        data={
            "grant_type": "client_credentials",
            "scope": "default",
            "client_id": os.environ["CLIENT_ID"],
            "client_secret": os.environ["CLIENT_SECRET"],
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


def get_access_token():
    """Load cached token if valid; otherwise request a new one."""

    if TOKEN_CACHE_FILE.exists():
        try:
            token_data = json.loads(TOKEN_CACHE_FILE.read_text())
            token = token_data["access_token"]

            if not jwt_is_expired(token):
                return token

        except Exception:
            pass

    return request_token()


def submit_fhir_bundle(bundle_path):
    """Submit a FHIR bundle file."""

    token = get_access_token()

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
        token = request_token()

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
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} bundle1.json [bundle2.json ...]")
        sys.exit(1)

    for bundle_file in sys.argv[1:]:
        submit_fhir_bundle(bundle_file)


if __name__ == "__main__":
    main()
