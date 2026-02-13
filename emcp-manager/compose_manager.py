"""
Docker Compose Manager

Safely manages MCP server entries in docker-compose.yaml.
Uses ruamel.yaml to preserve comments and formatting.

Container orchestration is handled by the HOST via systemd:
- This module modifies docker-compose.yaml and writes a trigger file
- Systemd watches the trigger file and runs `docker compose up -d`
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path

from ruamel.yaml import YAML

# Configuration
COMPOSE_DIR = os.getenv("COMPOSE_DIR", "/emcp")
COMPOSE_FILE = os.path.join(COMPOSE_DIR, "docker-compose.yaml")
BACKUP_DIR = os.path.join(COMPOSE_DIR, "backups")
CONFIGS_DIR = os.getenv("CONFIGS_DIR", "/configs")
TRIGGER_FILE = os.path.join(COMPOSE_DIR, ".reload-trigger")

# Label used to identify dynamically added services
DYNAMIC_LABEL = "emcp.dynamic"


class ComposeError(Exception):
    """Exception raised for compose management errors."""
    pass


def _get_yaml():
    """Get configured YAML parser that preserves formatting."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 4096  # Prevent line wrapping
    return yaml


def trigger_reload():
    """
    Signal the host to reload docker-compose.

    Writes to the trigger file that systemd is watching.
    The host will run `docker compose up -d` when this file changes.
    """
    with open(TRIGGER_FILE, 'w') as f:
        f.write(f"reload requested at {datetime.now().isoformat()}\n")


def backup_compose_file() -> str:
    """
    Create a timestamped backup of docker-compose.yaml.

    Returns:
        str: Path to the backup file
    """
    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"docker-compose.yaml.{timestamp}")

    shutil.copy2(COMPOSE_FILE, backup_path)

    # Keep only last 10 backups
    backups = sorted(Path(BACKUP_DIR).glob("docker-compose.yaml.*"))
    for old_backup in backups[:-10]:
        old_backup.unlink()

    return backup_path


def load_compose() -> dict:
    """
    Load and parse the docker-compose.yaml file.

    Returns:
        dict: Parsed compose configuration

    Raises:
        ComposeError: If file cannot be read or parsed
    """
    yaml = _get_yaml()

    try:
        with open(COMPOSE_FILE, 'r') as f:
            data = yaml.load(f)
            if data is None:
                raise ComposeError("Empty compose file")
            return data
    except FileNotFoundError:
        raise ComposeError(f"Compose file not found: {COMPOSE_FILE}")
    except Exception as e:
        raise ComposeError(f"Failed to parse compose file: {e}")


def save_compose(data: dict) -> None:
    """
    Safely save the docker-compose.yaml file.

    Uses atomic write (temp file + rename) to prevent corruption.

    Args:
        data: The compose configuration to save

    Raises:
        ComposeError: If save fails
    """
    yaml = _get_yaml()
    temp_path = f"{COMPOSE_FILE}.tmp"

    try:
        # Write to temp file
        with open(temp_path, 'w') as f:
            yaml.dump(data, f)

        # Validate by re-parsing
        with open(temp_path, 'r') as f:
            yaml.load(f)

        # Atomic rename
        os.rename(temp_path, COMPOSE_FILE)

    except Exception as e:
        # Clean up temp file on failure
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise ComposeError(f"Failed to save compose file: {e}")


def add_service(
    name: str,
    image: str,
    command: list[str],
    env_vars: list[str],
    description: str = "",
    volumes: list[str] = None
) -> str:
    """
    Add a new MCP server service to docker-compose.yaml.

    Creates a backup before modification.
    Triggers host reload after successful modification.

    Args:
        name: Server name (will be suffixed with -mcp)
        image: Docker image to use
        command: Command to run
        env_vars: List of environment variable names
        description: Optional description
        volumes: List of volume mounts (e.g., ["/host/path:/container/path:rw"])

    Returns:
        str: Container name (same as service name)

    Raises:
        ComposeError: If service already exists or save fails
    """
    service_name = f"{name}-mcp"

    # Create backup first
    backup_compose_file()

    try:
        data = load_compose()

        if 'services' not in data:
            raise ComposeError("No services section in compose file")

        if service_name in data['services']:
            raise ComposeError(f"Service '{service_name}' already exists")

        # Build service definition matching existing pattern
        service = {
            'image': image,
            'container_name': service_name,
            'stdin_open': True,
            'tty': True,
            'networks': ['emcp-network'],
            'restart': 'unless-stopped',
            'labels': {
                DYNAMIC_LABEL: 'true',
                'emcp.description': description or f'Dynamic MCP server: {name}'
            }
        }

        # Add command if specified
        if command:
            service['command'] = command

        # Add environment variables (reference from .env)
        if env_vars:
            service['environment'] = [f"{var}=${{{var}}}" for var in env_vars]

        # Add volume mounts
        if volumes:
            service['volumes'] = volumes

        # Add to services
        data['services'][service_name] = service

        save_compose(data)

        # Signal host to reload
        trigger_reload()

        return service_name

    except ComposeError:
        raise
    except Exception as e:
        raise ComposeError(f"Failed to add service: {e}")


def remove_service(name: str) -> bool:
    """
    Remove an MCP server service from docker-compose.yaml.

    Creates a backup before modification.
    Triggers host reload after successful modification.

    Args:
        name: Server name (without -mcp suffix)

    Returns:
        bool: True if service was removed

    Raises:
        ComposeError: If save fails
    """
    service_name = f"{name}-mcp"

    # Create backup first
    backup_compose_file()

    try:
        data = load_compose()

        if service_name not in data.get('services', {}):
            return False

        del data['services'][service_name]

        save_compose(data)

        # Signal host to reload (will stop removed containers)
        trigger_reload()

        return True

    except ComposeError:
        raise
    except Exception as e:
        raise ComposeError(f"Failed to remove service: {e}")




def create_mcp_config(
    name: str,
    container_name: str,
    command: list[str],
    description: str = ""
) -> str:
    """
    Create an MCP config file for MCPJungle.

    Args:
        name: Server name
        container_name: Docker container name
        command: Command to run inside container
        description: Optional description

    Returns:
        str: Path to created config file

    Raises:
        ComposeError: If config already exists or write fails
    """
    config_path = os.path.join(CONFIGS_DIR, f"{name}.json")

    if os.path.exists(config_path):
        raise ComposeError(f"Config file already exists: {config_path}")

    config = {
        "name": name,
        "transport": "stdio",
        "description": description or f"Dynamic MCP server: {name}",
        "command": "docker",
        "args": ["exec", "-i", container_name] + command
    }

    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return config_path
    except Exception as e:
        raise ComposeError(f"Failed to create config: {e}")


def delete_mcp_config(name: str) -> bool:
    """
    Delete an MCP config file.

    Args:
        name: Server name

    Returns:
        bool: True if deleted, False if didn't exist
    """
    config_path = os.path.join(CONFIGS_DIR, f"{name}.json")

    if os.path.exists(config_path):
        os.remove(config_path)
        return True
    return False


def get_container_status(container_name: str) -> dict:
    """
    Get status of a container via docker inspect.

    Args:
        container_name: Name of the container

    Returns:
        dict: {exists, running, status}
    """
    import subprocess

    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Status}}", container_name],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            status = result.stdout.strip()
            return {
                "exists": True,
                "running": status == "running",
                "status": status
            }
        else:
            return {
                "exists": False,
                "running": False,
                "status": "not found"
            }

    except Exception:
        return {
            "exists": False,
            "running": False,
            "status": "error"
        }
