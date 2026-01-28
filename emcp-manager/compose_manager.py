"""
Docker Compose Override Manager

Manages dynamically added MCP servers via docker-compose.override.yaml.
This approach keeps the main docker-compose.yaml untouched while allowing
users to add custom servers.
"""

import os
import subprocess
import yaml
from typing import Optional

# Path to the override file (relative to compose project root)
COMPOSE_DIR = os.getenv("COMPOSE_DIR", "/mnt/ops/docker/eMCP")
OVERRIDE_FILE = os.path.join(COMPOSE_DIR, "docker-compose.override.yaml")
CONFIGS_DIR = os.getenv("CONFIGS_DIR", "/configs")

# Network that all MCP servers must be on (compose prefixes with project name)
NETWORK_NAME = os.getenv("EMCP_NETWORK", "emcp_emcp-network")


class ComposeError(Exception):
    """Exception raised for compose management errors."""
    pass


def load_override() -> dict:
    """
    Load the docker-compose.override.yaml file.

    Returns:
        dict: Parsed YAML content, or empty structure if file doesn't exist
    """
    if os.path.exists(OVERRIDE_FILE):
        try:
            with open(OVERRIDE_FILE, 'r') as f:
                data = yaml.safe_load(f) or {}
                return data
        except yaml.YAMLError as e:
            raise ComposeError(f"Failed to parse override file: {e}")
    else:
        return {"services": {}}


def save_override(data: dict) -> None:
    """
    Save the docker-compose.override.yaml file.

    Args:
        data: YAML structure to save
    """
    # Ensure services key exists
    if "services" not in data:
        data["services"] = {}

    try:
        with open(OVERRIDE_FILE, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        raise ComposeError(f"Failed to save override file: {e}")


def add_service(
    name: str,
    image: str,
    command: list[str],
    env_vars: list[str],
    description: str = ""
) -> str:
    """
    Add a new MCP server service to the override file.

    Args:
        name: Server name (will be suffixed with -mcp for container)
        image: Docker image to use
        command: Command to run
        env_vars: List of environment variable names (values from .env)
        description: Optional description

    Returns:
        str: Container name

    Raises:
        ComposeError: If service already exists or save fails
    """
    data = load_override()
    service_name = f"{name}-mcp"
    container_name = f"{name}-mcp"

    if service_name in data.get("services", {}):
        raise ComposeError(f"Service '{service_name}' already exists")

    # Build service definition
    service = {
        "image": image,
        "container_name": container_name,
        "stdin_open": True,
        "tty": True,
        "networks": [NETWORK_NAME],
        "restart": "unless-stopped"
    }

    # Add command if specified
    if command:
        service["command"] = command

    # Add environment variables (reference from .env)
    if env_vars:
        service["environment"] = [f"{var}=${{{var}}}" for var in env_vars]

    # Add labels for tracking
    service["labels"] = {
        "emcp.dynamic": "true",
        "emcp.description": description
    }

    data["services"][service_name] = service
    save_override(data)

    return container_name


def remove_service(name: str) -> bool:
    """
    Remove a service from the override file.

    Args:
        name: Server name (without -mcp suffix)

    Returns:
        bool: True if service was removed
    """
    data = load_override()
    service_name = f"{name}-mcp"

    if service_name not in data.get("services", {}):
        return False

    del data["services"][service_name]
    save_override(data)

    return True


def get_dynamic_services() -> list[dict]:
    """
    Get list of dynamically added services.

    Returns:
        list[dict]: List of service info dicts with keys:
            - name: Service name
            - container_name: Container name
            - image: Docker image
            - description: Service description
    """
    data = load_override()
    services = []

    for service_name, config in data.get("services", {}).items():
        # Only include services with our dynamic label
        labels = config.get("labels", {})
        if labels.get("emcp.dynamic") == "true":
            services.append({
                "name": service_name.replace("-mcp", ""),
                "container_name": config.get("container_name", service_name),
                "image": config.get("image", "unknown"),
                "description": labels.get("emcp.description", "")
            })

    return services


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

    import json

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


def start_service(name: str) -> tuple[bool, str]:
    """
    Start a container using docker run.

    Args:
        name: Server name (without -mcp suffix)

    Returns:
        tuple[bool, str]: (success, output/error message)
    """
    container_name = f"{name}-mcp"

    # Load service config from override file
    data = load_override()
    service_name = f"{name}-mcp"

    if service_name not in data.get("services", {}):
        return False, f"Service {service_name} not found in override file"

    service = data["services"][service_name]
    image = service.get("image")
    command = service.get("command", [])
    env_vars = service.get("environment", [])

    if not image:
        return False, "No image specified for service"

    try:
        # Build docker run command
        cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "--network", NETWORK_NAME,
            "-i",  # stdin_open
            "--restart", "unless-stopped"
        ]

        # Add environment variables
        for env in env_vars:
            cmd.extend(["-e", env])

        # Add labels
        cmd.extend(["--label", "emcp.dynamic=true"])
        cmd.extend(["--label", f"emcp.description={service.get('labels', {}).get('emcp.description', '')}"])

        # Add image
        cmd.append(image)

        # Add command if specified
        if command:
            if isinstance(command, list):
                cmd.extend(command)
            else:
                cmd.append(command)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            return True, result.stdout or "Container started"
        else:
            return False, result.stderr or "Failed to start container"

    except subprocess.TimeoutExpired:
        return False, "Timeout waiting for container to start"
    except Exception as e:
        return False, str(e)


def stop_service(name: str) -> tuple[bool, str]:
    """
    Stop and remove a container.

    Args:
        name: Server name (without -mcp suffix)

    Returns:
        tuple[bool, str]: (success, output/error message)
    """
    container_name = f"{name}-mcp"

    try:
        # Stop the container
        result = subprocess.run(
            ["docker", "stop", container_name],
            capture_output=True,
            text=True,
            timeout=60
        )

        # Remove the container (ignore errors if it doesn't exist)
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            capture_output=True,
            text=True,
            timeout=30
        )

        return True, "Container stopped"

    except subprocess.TimeoutExpired:
        return False, "Timeout waiting for container to stop"
    except Exception as e:
        return False, str(e)


def restart_service(name: str) -> tuple[bool, str]:
    """
    Restart a container.

    Args:
        name: Server name (without -mcp suffix)

    Returns:
        tuple[bool, str]: (success, output/error message)
    """
    container_name = f"{name}-mcp"

    try:
        result = subprocess.run(
            ["docker", "restart", container_name],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            return True, "Container restarted"
        else:
            return False, result.stderr or "Failed to restart container"

    except subprocess.TimeoutExpired:
        return False, "Timeout waiting for container to restart"
    except Exception as e:
        return False, str(e)


def get_container_status(container_name: str) -> dict:
    """
    Get status of a container.

    Args:
        container_name: Name of the container

    Returns:
        dict: {
            "exists": bool,
            "running": bool,
            "status": str
        }
    """
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format",
             "{{.State.Status}}", container_name],
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


def is_dynamic_server(name: str) -> bool:
    """
    Check if a server is dynamically added (vs defined in main compose).

    Args:
        name: Server name (without -mcp suffix)

    Returns:
        bool: True if this is a dynamic server
    """
    services = get_dynamic_services()
    return any(s["name"] == name for s in services)
