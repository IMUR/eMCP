"""
Infisical API Client for eMCP Manager

Provides programmatic access to Infisical secrets using a pre-configured
access token (Token Auth or Service Token).
"""

import os
import requests
from typing import Optional

# Configuration from environment
INFISICAL_API_URL = os.getenv("INFISICAL_API_URL", "https://app.infisical.com")
INFISICAL_TOKEN = os.getenv("EMCP_INFISICAL_SECRET", "") or os.getenv("INFISICAL_TOKEN", "")
INFISICAL_WORKSPACE_ID = os.getenv("INFISICAL_WORKSPACE_ID", "")
INFISICAL_ENVIRONMENT = os.getenv("INFISICAL_ENVIRONMENT", "prod")


class InfisicalError(Exception):
    """Exception raised for Infisical API errors."""
    pass


def is_configured() -> bool:
    """Check if Infisical token is configured."""
    return bool(INFISICAL_TOKEN and INFISICAL_WORKSPACE_ID)


def get_access_token() -> str:
    """
    Get the configured Infisical access token.

    Returns:
        str: Access token

    Raises:
        InfisicalError: If token is not configured
    """
    if not INFISICAL_TOKEN:
        raise InfisicalError("Infisical token not configured. Set EMCP_INFISICAL_SECRET or INFISICAL_TOKEN.")
    return INFISICAL_TOKEN


def create_secret(key: str, value: str, path: str = "/emcp") -> bool:
    """
    Create a new secret in Infisical.

    Args:
        key: Secret key name (e.g., "MY_API_KEY")
        value: Secret value
        path: Secret path (default: /emcp)

    Returns:
        bool: True if created successfully

    Raises:
        InfisicalError: If creation fails
    """
    token = get_access_token()

    url = f"{INFISICAL_API_URL}/api/v3/secrets/raw/{key}"

    try:
        response = requests.post(
            url,
            json={
                "workspaceId": INFISICAL_WORKSPACE_ID,
                "environment": INFISICAL_ENVIRONMENT,
                "secretPath": path,
                "secretValue": value,
                "type": "shared"
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=30
        )

        if response.status_code == 400:
            # Secret might already exist, try updating instead
            return update_secret(key, value, path)

        response.raise_for_status()
        return True

    except requests.exceptions.RequestException as e:
        raise InfisicalError(f"Failed to create secret '{key}': {e}")


def update_secret(key: str, value: str, path: str = "/emcp") -> bool:
    """
    Update an existing secret in Infisical.

    Args:
        key: Secret key name
        value: New secret value
        path: Secret path (default: /emcp)

    Returns:
        bool: True if updated successfully

    Raises:
        InfisicalError: If update fails
    """
    token = get_access_token()

    url = f"{INFISICAL_API_URL}/api/v3/secrets/raw/{key}"

    try:
        response = requests.patch(
            url,
            json={
                "workspaceId": INFISICAL_WORKSPACE_ID,
                "environment": INFISICAL_ENVIRONMENT,
                "secretPath": path,
                "secretValue": value
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        response.raise_for_status()
        return True

    except requests.exceptions.RequestException as e:
        raise InfisicalError(f"Failed to update secret '{key}': {e}")


def get_secret(key: str, path: str = "/emcp") -> Optional[str]:
    """
    Retrieve a secret value from Infisical.

    Args:
        key: Secret key name
        path: Secret path (default: /emcp)

    Returns:
        str or None: Secret value, or None if not found

    Raises:
        InfisicalError: If retrieval fails (other than not found)
    """
    token = get_access_token()

    url = f"{INFISICAL_API_URL}/api/v3/secrets/raw/{key}"

    try:
        response = requests.get(
            url,
            params={
                "workspaceId": INFISICAL_WORKSPACE_ID,
                "environment": INFISICAL_ENVIRONMENT,
                "secretPath": path
            },
            headers={
                "Authorization": f"Bearer {token}"
            },
            timeout=30
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()

        data = response.json()
        secret = data.get("secret", {})
        return secret.get("secretValue")

    except requests.exceptions.RequestException as e:
        raise InfisicalError(f"Failed to get secret '{key}': {e}")


def delete_secret(key: str, path: str = "/emcp") -> bool:
    """
    Delete a secret from Infisical.

    Args:
        key: Secret key name
        path: Secret path (default: /emcp)

    Returns:
        bool: True if deleted successfully

    Raises:
        InfisicalError: If deletion fails
    """
    token = get_access_token()

    url = f"{INFISICAL_API_URL}/api/v3/secrets/raw/{key}"

    try:
        response = requests.delete(
            url,
            json={
                "workspaceId": INFISICAL_WORKSPACE_ID,
                "environment": INFISICAL_ENVIRONMENT,
                "secretPath": path
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=30
        )

        if response.status_code == 404:
            return True  # Already doesn't exist

        response.raise_for_status()
        return True

    except requests.exceptions.RequestException as e:
        raise InfisicalError(f"Failed to delete secret '{key}': {e}")


def list_secrets(path: str = "/emcp") -> list[str]:
    """
    List all secret keys at a path.

    Args:
        path: Secret path (default: /emcp)

    Returns:
        list[str]: List of secret key names

    Raises:
        InfisicalError: If listing fails
    """
    token = get_access_token()

    url = f"{INFISICAL_API_URL}/api/v3/secrets/raw"

    try:
        response = requests.get(
            url,
            params={
                "workspaceId": INFISICAL_WORKSPACE_ID,
                "environment": INFISICAL_ENVIRONMENT,
                "secretPath": path
            },
            headers={
                "Authorization": f"Bearer {token}"
            },
            timeout=30
        )
        response.raise_for_status()

        data = response.json()
        secrets = data.get("secrets", [])
        return [s.get("secretKey") for s in secrets if s.get("secretKey")]

    except requests.exceptions.RequestException as e:
        raise InfisicalError(f"Failed to list secrets: {e}")


def secret_exists(key: str, path: str = "/emcp") -> bool:
    """
    Check if a secret exists.

    Args:
        key: Secret key name
        path: Secret path (default: /emcp)

    Returns:
        bool: True if secret exists
    """
    return get_secret(key, path) is not None
