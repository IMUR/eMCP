"""
Docker Compose Manager

Safely manages MCP server entries in docker-compose.yaml.
Uses ruamel.yaml to preserve comments and formatting.

Container orchestration is handled directly via the Docker socket.
The manager container has the socket mounted, so it can create/start/stop
containers without needing systemd or docker-compose CLI on the host.
"""

import os
import re
import shutil
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

from ruamel.yaml import YAML

# Configuration
COMPOSE_DIR = os.getenv("COMPOSE_DIR", "/emcp")
COMPOSE_FILE = os.path.join(COMPOSE_DIR, "docker-compose.yaml")
BACKUP_DIR = os.path.join(COMPOSE_DIR, "backups")
CONFIGS_DIR = os.getenv("CONFIGS_DIR", "/configs")
ENV_FILE = os.path.join(COMPOSE_DIR, ".env")
NETWORK_NAME = os.getenv("EMCP_NETWORK", "emcp_emcp-network")

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


def _run_docker(args, timeout=60):
    """
    Run a docker command via the mounted socket.

    Args:
        args: List of arguments after 'docker'
        timeout: Timeout in seconds

    Returns:
        subprocess.CompletedProcess
    """
    cmd = ["docker"] + args
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout
    )


# ---------------------------------------------------------------------------
# Compose file operations
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Environment variable management
# ---------------------------------------------------------------------------

def write_env_vars(env_vars: dict) -> list[str]:
    """
    Write environment variables to the .env file.

    Docker Compose reads .env automatically. Service definitions reference
    variables as ${KEY}, which compose resolves at container start time.

    Existing keys are updated; new keys are appended.

    Args:
        env_vars: Dictionary of KEY=value pairs

    Returns:
        list[str]: List of variable names written
    """
    if not env_vars:
        return []

    # Read existing .env content
    existing = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    existing[key.strip()] = value.strip()

    # Merge new values
    existing.update(env_vars)

    # Write back
    with open(ENV_FILE, 'w') as f:
        for key, value in existing.items():
            f.write(f"{key}={value}\n")

    return list(env_vars.keys())


# ---------------------------------------------------------------------------
# Service management (compose file + direct docker)
# ---------------------------------------------------------------------------

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

    Creates a backup before modification. Does NOT start the container —
    call start_service() separately after this.

    Args:
        name: Server name (will be suffixed with -mcp)
        image: Docker image to use
        command: Command to run
        env_vars: List of environment variable names (referenced as ${KEY})
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

        return service_name

    except ComposeError:
        raise
    except Exception as e:
        raise ComposeError(f"Failed to add service: {e}")


def remove_service(name: str) -> bool:
    """
    Remove an MCP server service from docker-compose.yaml.

    Creates a backup before modification. Does NOT stop/remove the container —
    call stop_service() separately before this.

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

        return True

    except ComposeError:
        raise
    except Exception as e:
        raise ComposeError(f"Failed to remove service: {e}")


# ---------------------------------------------------------------------------
# Container lifecycle (direct docker commands via socket)
# ---------------------------------------------------------------------------

def pull_image(image: str, timeout: int = 600) -> bool:
    """
    Pull a Docker image.

    Args:
        image: Image name with optional tag
        timeout: Timeout in seconds (default 10 min for large images)

    Returns:
        True if pull succeeded or image exists locally

    Raises:
        ComposeError: If image cannot be obtained
    """
    try:
        result = _run_docker(["pull", image], timeout=timeout)
        if result.returncode == 0:
            return True

        # Pull failed — check if image exists locally
        check = _run_docker(["images", "-q", image])
        if check.returncode == 0 and check.stdout.strip():
            return True

        raise ComposeError(
            f"Failed to pull image '{image}' and not found locally: "
            f"{result.stderr.strip()}"
        )

    except subprocess.TimeoutExpired:
        # Check local
        check = _run_docker(["images", "-q", image])
        if check.returncode == 0 and check.stdout.strip():
            return True
        raise ComposeError(f"Timed out pulling image '{image}'")


def start_service(service_name: str, image: str, command: list[str],
                  env_vars: dict = None, volumes: list[str] = None,
                  timeout: int = 60) -> bool:
    """
    Start a container using direct docker commands.

    Creates and starts the container, connecting it to the eMCP network.

    Args:
        service_name: Container/service name (e.g., "myserver-mcp")
        image: Docker image to use
        command: Command + args to run
        env_vars: Dict of environment variable key=value pairs
        volumes: List of volume mount strings
        timeout: Seconds to wait for container to start

    Returns:
        True if container started successfully

    Raises:
        ComposeError: If container fails to start
    """
    # Build docker create command
    create_args = [
        "create",
        "--name", service_name,
        "--network", NETWORK_NAME,
        "--restart", "unless-stopped",
        "--interactive",
        "--tty",
        "--label", f"{DYNAMIC_LABEL}=true",
    ]

    # Add environment variables with actual values
    if env_vars:
        for key, value in env_vars.items():
            create_args.extend(["-e", f"{key}={value}"])

    # Add volume mounts
    if volumes:
        for vol in volumes:
            create_args.extend(["-v", vol])

    # Image and command
    create_args.append(image)
    if command:
        create_args.extend(command)

    # Create
    result = _run_docker(create_args)
    if result.returncode != 0:
        raise ComposeError(
            f"Failed to create container '{service_name}': {result.stderr.strip()}"
        )

    # Start
    result = _run_docker(["start", service_name])
    if result.returncode != 0:
        # Clean up created container
        _run_docker(["rm", "-f", service_name])
        raise ComposeError(
            f"Failed to start container '{service_name}': {result.stderr.strip()}"
        )

    # Wait for running
    for _ in range(timeout // 2):
        time.sleep(2)
        status = get_container_status(service_name)
        if status.get("running"):
            return True

    raise ComposeError(
        f"Container '{service_name}' did not reach running state within {timeout}s"
    )


def stop_service(service_name: str) -> bool:
    """
    Stop and remove a container.

    Args:
        service_name: Container name

    Returns:
        True if container was stopped/removed
    """
    # Stop first (graceful shutdown)
    _run_docker(["stop", service_name], timeout=30)
    # Then remove
    result = _run_docker(["rm", "-f", service_name], timeout=15)
    return result.returncode == 0


# ---------------------------------------------------------------------------
# MCP readiness check
# ---------------------------------------------------------------------------

def wait_for_mcp_ready(container_name: str, command: list[str],
                       timeout: int = 90) -> bool:
    """
    Wait for the MCP server inside a container to respond to initialize.

    Sends a JSON-RPC initialize request to the server's stdin and checks
    for a valid response. This ensures the server is actually ready to
    handle tool registration, not just that the container is running.

    Args:
        container_name: Docker container name
        command: The MCP server command to exec (e.g., ["npx", "..."])
        timeout: Max seconds to wait

    Returns:
        True if MCP server responded to initialize
    """
    init_request = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "emcp-readiness-check", "version": "1.0"}
        }
    }) + "\n"

    interval = 3
    attempts = timeout // interval

    for attempt in range(attempts):
        try:
            result = subprocess.run(
                ["docker", "exec", "-i", container_name] + command,
                input=init_request,
                capture_output=True,
                text=True,
                timeout=10
            )
            if '"result"' in result.stdout and '"protocolVersion"' in result.stdout:
                return True
        except (subprocess.TimeoutExpired, Exception):
            pass

        time.sleep(interval)

    return False


# ---------------------------------------------------------------------------
# MCP config file management
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Container status
# ---------------------------------------------------------------------------

def get_container_status(container_name: str) -> dict:
    """
    Get status of a container via docker inspect.

    Args:
        container_name: Name of the container

    Returns:
        dict: {exists, running, status}
    """
    try:
        result = _run_docker(
            ["inspect", "--format", "{{.State.Status}}", container_name],
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
