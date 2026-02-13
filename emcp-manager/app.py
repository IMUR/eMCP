#!/usr/bin/env python3
"""
Simple Flask API for eMCP tool selection
"""
from flask import Flask, jsonify, request, send_from_directory
import subprocess
import json
import os
import time
import requests

# Import new modules for server management
from mcp_detector import detect_server, parse_mcp_url, DetectionError
from compose_manager import (
    add_service, remove_service,
    create_mcp_config, delete_mcp_config, trigger_reload,
    get_container_status, ComposeError
)
from infisical_client import (
    create_secret, is_configured as infisical_configured,
    InfisicalError
)

app = Flask(__name__)

EMCP_CONTAINER = "emcp-server"
MCPJUNGLE_API = os.getenv("MCPJUNGLE_API", "http://emcp-server:8080")
GROUPS_DIR = "/groups"
DEFAULT_GROUP = "emcp-global"
EMCP_GROUP_FILE = os.path.join(GROUPS_DIR, f"{DEFAULT_GROUP}.json")
PRESETS_DIR = os.path.join(GROUPS_DIR, "presets")


def exec_emcp(cmd):
    """Execute command in eMCP container"""
    full_cmd = ["docker", "exec", "-t", EMCP_CONTAINER, "/mcpjungle"] + cmd
    result = subprocess.run(full_cmd, capture_output=True, text=True)
    return result


def get_all_tools():
    """Fetch all tools from MCPJungle REST API"""
    response = requests.get(f"{MCPJUNGLE_API}/api/v0/tools", timeout=10)
    response.raise_for_status()

    tools_by_server = {}
    for tool in response.json():
        # Tool name format: "server__tool_name"
        parts = tool["name"].split("__", 1)
        server_name = parts[0] if len(parts) > 1 else "unknown"

        if server_name not in tools_by_server:
            tools_by_server[server_name] = []

        tools_by_server[server_name].append({
            "name": tool["name"],
            "description": tool.get("description", ""),
            "enabled": tool.get("enabled", True)
        })

    return tools_by_server


def get_all_valid_tool_names():
    """Get set of all valid tool names from MCPJungle"""
    try:
        response = requests.get(f"{MCPJUNGLE_API}/api/v0/tools", timeout=10)
        if response.status_code != 200:
            return set()
        return {tool["name"] for tool in response.json()}
    except requests.RequestException:
        return set()


def validate_tool_names(selected_tools):
    """Validate that all selected tools exist. Returns (valid, invalid_tools)"""
    if not selected_tools:
        return True, []

    valid_tools = get_all_valid_tool_names()
    if not valid_tools:
        # Couldn't get valid tools list - skip validation rather than block
        return True, []

    invalid = [t for t in selected_tools if t not in valid_tools]
    return len(invalid) == 0, invalid


# =============================================================================
# Group Management Functions
# =============================================================================

def sanitize_group_name(name):
    """
    Sanitize group name for filesystem safety.
    Allows alphanumeric, hyphens, underscores. Rejects path traversal attempts.
    """
    if not name:
        raise ValueError("Group name cannot be empty")

    # Reject obvious path traversal
    if '..' in name or '/' in name or '\\' in name:
        raise ValueError("Invalid group name: path traversal not allowed")

    # Keep only safe characters
    safe_name = "".join(c for c in name if c.isalnum() or c in ('-', '_')).strip()

    if not safe_name:
        raise ValueError("Group name must contain alphanumeric characters")

    if len(safe_name) > 64:
        raise ValueError("Group name too long (max 64 characters)")

    return safe_name


def get_group_file(group_name):
    """Get path to group config file"""
    safe_name = sanitize_group_name(group_name)
    return os.path.join(GROUPS_DIR, f"{safe_name}.json")


def list_groups():
    """List all available groups (excludes presets subdirectory)"""
    groups = []
    if os.path.exists(GROUPS_DIR):
        for filename in os.listdir(GROUPS_DIR):
            filepath = os.path.join(GROUPS_DIR, filename)
            # Only include .json files, not directories
            if filename.endswith('.json') and os.path.isfile(filepath):
                groups.append(filename[:-5])  # Remove .json extension
    return sorted(groups)


def get_group(group_name):
    """Get group configuration by name"""
    group_file = get_group_file(group_name)

    if not os.path.exists(group_file):
        return None

    with open(group_file, 'r') as f:
        return json.load(f)


def create_group(group_name, description=None, tools=None):
    """
    Create a new group with optional initial tools.
    MCPJungle registration is lazy - only happens when group has tools.
    Returns the created group config.
    """
    safe_name = sanitize_group_name(group_name)
    group_file = get_group_file(safe_name)

    if os.path.exists(group_file):
        raise ValueError(f"Group '{safe_name}' already exists")

    # Validate tools if provided
    if tools:
        valid, invalid_tools = validate_tool_names(tools)
        if not valid:
            raise ValueError(f"Invalid tool names: {', '.join(invalid_tools)}")

    config = {
        "name": safe_name,
        "description": description or f"Tools for {safe_name} project",
        "included_tools": tools or []
    }

    # Write config file
    with open(group_file, 'w') as f:
        json.dump(config, f, indent=2)

    # Only register with MCPJungle if group has tools
    # (MCPJungle requires at least one tool per group)
    if tools:
        result = exec_emcp(["create", "group", "-c", f"/groups/{safe_name}.json"])
        if result.returncode != 0:
            os.remove(group_file)
            error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            raise Exception(f"Failed to register group with MCPJungle: {error_msg}")
        config["registered"] = True
    else:
        config["registered"] = False
        config["note"] = "Group will be registered with MCPJungle when tools are added"

    return config


def delete_group(group_name):
    """
    Delete a group by name via MCPJungle CLI.
    Prevents deletion of the default global group.
    """
    safe_name = sanitize_group_name(group_name)

    # Protect the default global group
    if safe_name == DEFAULT_GROUP:
        raise ValueError(f"Cannot delete the default group '{DEFAULT_GROUP}'")

    group_file = get_group_file(safe_name)

    if not os.path.exists(group_file):
        raise ValueError(f"Group '{safe_name}' not found")

    # Delete from MCPJungle via CLI (no REST API for groups)
    exec_emcp(["delete", "group", safe_name])
    # Ignore return code - file cleanup is more important

    # Remove the file
    os.remove(group_file)

    return True


def update_group_tools(group_name, selected_tools):
    """
    Update tools for any group with safe UPDATE-first pattern.
    Handles lazy registration for groups that weren't registered on creation.
    """
    safe_name = sanitize_group_name(group_name)
    group_file = get_group_file(safe_name)

    if not os.path.exists(group_file):
        raise ValueError(f"Group '{safe_name}' not found")

    # SAFETY: Validate all tool names BEFORE any operation
    valid, invalid_tools = validate_tool_names(selected_tools)
    if not valid:
        raise ValueError(f"Invalid tool names (group NOT modified): {', '.join(invalid_tools)}")

    # Read existing config to preserve description
    with open(group_file, 'r') as f:
        existing = json.load(f)

    group_config = {
        "name": safe_name,
        "description": existing.get("description", f"Tools for {safe_name}"),
        "included_tools": selected_tools
    }

    # Write updated config
    with open(group_file, 'w') as f:
        json.dump(group_config, f, indent=2)

    # SAFE: Try UPDATE first (atomic, no downtime)
    config_path = f"/groups/{safe_name}.json"
    result = exec_emcp(["update", "group", "-c", config_path])

    if result.returncode != 0:
        # Group might not be registered yet (lazy registration)
        # Only try CREATE if we have tools (MCPJungle requirement)
        if selected_tools:
            result = exec_emcp(["create", "group", "-c", config_path])
            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
                raise Exception(f"Failed to update/create group: {error_msg}")

    return True


# Backwards-compatible alias for default group
def update_emcp_group(selected_tools):
    """Update the default global group (backwards compatibility)"""
    return update_group_tools(DEFAULT_GROUP, selected_tools)


def _get_group_tools(group_name=None):
    """Read tool selection for a group from disk"""
    if group_name is None:
        group_name = DEFAULT_GROUP

    group_file = get_group_file(group_name)
    if os.path.exists(group_file):
        with open(group_file, 'r') as f:
            return json.load(f).get("included_tools", [])
    return []


# Backwards-compatible alias
def _get_current_tools():
    """Read current tool selection from default group (backwards compatibility)"""
    return _get_group_tools(DEFAULT_GROUP)


def _modify_group_tool(group_name, tool_name, action):
    """
    Modify tool selection for a specific group.

    Args:
        group_name: The group to modify
        tool_name: The tool to modify (e.g., "github__search_code")
        action: One of "enable", "disable", "toggle"

    Returns:
        tuple: (current_tools, message, is_now_enabled)
    """
    if not tool_name:
        raise ValueError("Tool name required")

    safe_name = sanitize_group_name(group_name)
    current = _get_group_tools(safe_name)
    was_present = tool_name in current

    if action == "enable":
        if not was_present:
            current.append(tool_name)
            update_group_tools(safe_name, current)
        return current, f"Tool '{tool_name}' {'enabled' if not was_present else 'already enabled'}", True

    elif action == "disable":
        if was_present:
            current.remove(tool_name)
            update_group_tools(safe_name, current)
        return current, f"Tool '{tool_name}' {'disabled' if was_present else 'already disabled'}", False

    elif action == "toggle":
        if was_present:
            current.remove(tool_name)
        else:
            current.append(tool_name)
        update_group_tools(safe_name, current)
        is_enabled = not was_present
        return current, f"Tool '{tool_name}' {'enabled' if is_enabled else 'disabled'}", is_enabled

    raise ValueError(f"Unknown action: {action}")


# Backwards-compatible alias
def _modify_tool_selection(tool_name, action):
    """Modify tool selection in default group (backwards compatibility)"""
    return _modify_group_tool(DEFAULT_GROUP, tool_name, action)


@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('.', 'index.html')


@app.route('/api/tools', methods=['GET'])
def api_get_tools():
    """API endpoint to get all available tools"""
    try:
        tools = get_all_tools()
        return jsonify({
            "success": True,
            "servers": tools
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/update', methods=['POST'])
def api_update_group():
    """API endpoint to update the eMCP tool group"""
    try:
        data = request.get_json()
        selected_tools = data.get('tools', [])

        if not isinstance(selected_tools, list):
            return jsonify({
                "success": False,
                "error": "Invalid tools format"
            }), 400

        update_emcp_group(selected_tools)

        return jsonify({
            "success": True,
            "message": f"Updated eMCP group with {len(selected_tools)} tools",
            "tools": selected_tools
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/current', methods=['GET'])
def api_get_current():
    """API endpoint to get current eMCP group selection"""
    try:
        return jsonify({"success": True, "tools": _get_current_tools()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



@app.route('/api/presets', methods=['GET'])
def api_list_presets():
    """API endpoint to list available presets"""
    try:
        presets = []
        if os.path.exists(PRESETS_DIR):
            for filename in os.listdir(PRESETS_DIR):
                if filename.endswith('.json'):
                    presets.append(filename[:-5])  # Remove .json extension
        return jsonify({
            "success": True,
            "presets": sorted(presets)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/presets/save', methods=['POST'])
def api_save_preset():
    """API endpoint to save current selection as a preset"""
    try:
        data = request.get_json()
        name = data.get('name')
        tools = data.get('tools', [])

        if not name:
            return jsonify({"success": False, "error": "Preset name required"}), 400

        # Sanitize filename
        safe_name = "".join([c for c in name if c.isalpha() or c.isdigit() or c in ('-', '_')]).strip()
        if not safe_name:
            return jsonify({"success": False, "error": "Invalid preset name"}), 400

        filepath = os.path.join(PRESETS_DIR, f"{safe_name}.json")

        with open(filepath, 'w') as f:
            json.dump({"name": name, "tools": tools}, f, indent=2)

        return jsonify({
            "success": True,
            "message": f"Preset '{safe_name}' saved",
            "name": safe_name
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/presets/load', methods=['POST'])
def api_load_preset():
    """API endpoint to load a preset and update the group"""
    try:
        data = request.get_json()
        name = data.get('name')

        if not name:
            return jsonify({"success": False, "error": "Preset name required"}), 400

        filepath = os.path.join(PRESETS_DIR, f"{name}.json")

        if not os.path.exists(filepath):
            return jsonify({"success": False, "error": "Preset not found"}), 404

        with open(filepath, 'r') as f:
            preset_data = json.load(f)
            tools = preset_data.get('tools', [])

        # Update the group with these tools
        update_emcp_group(tools)

        return jsonify({
            "success": True,
            "message": f"Loaded preset '{name}' with {len(tools)} tools",
            "tools": tools
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/presets/delete', methods=['POST'])
def api_delete_preset():
    """API endpoint to delete a preset"""
    try:
        data = request.get_json()
        name = data.get('name')

        if not name:
            return jsonify({"success": False, "error": "Preset name required"}), 400

        filepath = os.path.join(PRESETS_DIR, f"{name}.json")

        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({
                "success": True,
                "message": f"Preset '{name}' deleted"
            })
        else:
            return jsonify({"success": False, "error": "Preset not found"}), 404

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500



# =============================================================================
# Group API Endpoints
# =============================================================================

@app.route('/api/groups', methods=['GET'])
def api_list_groups():
    """API endpoint to list all available groups"""
    try:
        groups = list_groups()
        return jsonify({
            "success": True,
            "groups": groups,
            "default": DEFAULT_GROUP
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/groups/<group_name>', methods=['GET'])
def api_get_group(group_name):
    """API endpoint to get a specific group's configuration"""
    try:
        group = get_group(group_name)
        if group is None:
            return jsonify({"success": False, "error": f"Group '{group_name}' not found"}), 404
        return jsonify({
            "success": True,
            "group": group
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/groups/<group_name>', methods=['POST'])
def api_create_group(group_name):
    """API endpoint to create a new group"""
    try:
        data = request.get_json() or {}
        description = data.get('description')
        tools = data.get('tools', [])

        config = create_group(group_name, description=description, tools=tools)

        return jsonify({
            "success": True,
            "message": f"Group '{config['name']}' created",
            "group": config
        }), 201
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/groups/<group_name>', methods=['DELETE'])
def api_delete_group(group_name):
    """API endpoint to delete a group"""
    try:
        delete_group(group_name)
        return jsonify({
            "success": True,
            "message": f"Group '{group_name}' deleted"
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# =============================================================================
# Per-Group Tool Management Endpoints
# =============================================================================

@app.route('/api/groups/<group_name>/tools', methods=['GET'])
def api_get_group_tools(group_name):
    """API endpoint to get tools for a specific group"""
    try:
        tools = _get_group_tools(group_name)
        return jsonify({"success": True, "group": group_name, "tools": tools})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/groups/<group_name>/tools', methods=['POST'])
def api_update_group_tools(group_name):
    """API endpoint to update tools for a specific group"""
    try:
        data = request.get_json()
        selected_tools = data.get('tools', [])

        if not isinstance(selected_tools, list):
            return jsonify({"success": False, "error": "Invalid tools format"}), 400

        update_group_tools(group_name, selected_tools)

        return jsonify({
            "success": True,
            "message": f"Updated group '{group_name}' with {len(selected_tools)} tools",
            "group": group_name,
            "tools": selected_tools
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/groups/<group_name>/tools/enable', methods=['POST'])
def api_enable_group_tool(group_name):
    """API endpoint to enable a tool in a specific group"""
    try:
        data = request.get_json()
        tools, message, _ = _modify_group_tool(group_name, data.get('tool'), "enable")
        return jsonify({"success": True, "message": message, "group": group_name, "tools": tools})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/groups/<group_name>/tools/disable', methods=['POST'])
def api_disable_group_tool(group_name):
    """API endpoint to disable a tool in a specific group"""
    try:
        data = request.get_json()
        tools, message, _ = _modify_group_tool(group_name, data.get('tool'), "disable")
        return jsonify({"success": True, "message": message, "group": group_name, "tools": tools})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/groups/<group_name>/tools/toggle', methods=['POST'])
def api_toggle_group_tool(group_name):
    """API endpoint to toggle a tool in a specific group"""
    try:
        data = request.get_json()
        tools, message, enabled = _modify_group_tool(group_name, data.get('tool'), "toggle")
        return jsonify({
            "success": True,
            "message": message,
            "group": group_name,
            "tools": tools,
            "enabled": enabled
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# =============================================================================
# Tool Toggle Endpoints (default group - backwards compatibility)
# =============================================================================

@app.route('/api/tools/enable', methods=['POST'])
def api_enable_tool():
    """API endpoint to enable a specific tool in default group"""
    try:
        data = request.get_json()
        tools, message, _ = _modify_tool_selection(data.get('tool'), "enable")
        return jsonify({"success": True, "message": message, "tools": tools})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/tools/disable', methods=['POST'])
def api_disable_tool():
    """API endpoint to disable a specific tool"""
    try:
        data = request.get_json()
        tools, message, _ = _modify_tool_selection(data.get('tool'), "disable")
        return jsonify({"success": True, "message": message, "tools": tools})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/tools/toggle', methods=['POST'])
def api_toggle_tool():
    """API endpoint to toggle a specific tool"""
    try:
        data = request.get_json()
        tools, message, enabled = _modify_tool_selection(data.get('tool'), "toggle")
        return jsonify({"success": True, "message": message, "tools": tools, "enabled": enabled})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# =============================================================================
# Server Management Endpoints
# =============================================================================

@app.route('/api/servers/detect', methods=['POST'])
def api_detect_server():
    """
    Detect MCP server configuration from a URL.

    Input: {"url": "https://github.com/..." | "@org/package" | "ghcr.io/..."}

    Returns detected configuration including:
    - name: Suggested server name
    - description: Server description
    - image: Docker image to use
    - command: Command to run
    - required_env_vars: Environment variables needed
    """
    try:
        data = request.get_json()
        url = data.get('url', '').strip()

        if not url:
            return jsonify({
                "success": False,
                "error": "URL is required"
            }), 400

        detected = detect_server(url)

        return jsonify({
            "success": True,
            "detected": detected
        })

    except DetectionError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Detection failed: {str(e)}"
        }), 500


@app.route('/api/servers/provision', methods=['POST'])
def api_provision_server():
    """
    Provision a new MCP server.

    Input: {
        "name": "server-name",
        "image": "docker-image:tag",
        "command": ["cmd", "args"],
        "env_vars": {"KEY": "value", ...},
        "description": "optional description"
    }

    This will:
    1. Store secrets in Infisical (if configured)
    2. Add service to docker-compose.override.yaml
    3. Create MCP config in /configs/
    4. Start the container
    5. Verify tools are discovered
    """
    try:
        data = request.get_json()

        # Validate required fields
        name = data.get('name', '').strip()
        image = data.get('image', '').strip()
        command = data.get('command', [])
        env_vars = data.get('env_vars', {})
        description = data.get('description', '')

        if not name:
            return jsonify({"success": False, "error": "Server name is required"}), 400

        if not image:
            return jsonify({"success": False, "error": "Docker image is required"}), 400

        # Sanitize name
        safe_name = "".join(c for c in name.lower() if c.isalnum() or c == '-').strip('-')
        if not safe_name or len(safe_name) > 50:
            return jsonify({"success": False, "error": "Invalid server name"}), 400

        # Store secrets in Infisical if configured and env vars provided
        env_var_names = []
        if env_vars:
            if infisical_configured():
                for key, value in env_vars.items():
                    if value:  # Only store non-empty values
                        try:
                            create_secret(key, value)
                            env_var_names.append(key)
                        except InfisicalError as e:
                            return jsonify({
                                "success": False,
                                "error": f"Failed to store secret '{key}': {str(e)}"
                            }), 500
            else:
                # Infisical not configured - secrets need to be added manually
                env_var_names = list(env_vars.keys())

        # Detect host paths in command and create volume mounts
        volumes = []
        for arg in command:
            # Check if arg looks like a host path (absolute path starting with /)
            if arg.startswith('/') and not arg.startswith('//'):
                # Skip common non-path arguments
                if arg in ['/dev/null', '/dev/stdin', '/dev/stdout', '/dev/stderr']:
                    continue
                # Add as volume mount (same path inside container)
                volumes.append(f"{arg}:{arg}:rw")

        # Explicitly pull the image first to prevent timeout during reload
        # This uses the mounted docker socket so it pulls to the host daemon
        try:
             pull_result = subprocess.run(
                 ["docker", "pull", image],
                 capture_output=True,
                 text=True,
                 timeout=600  # 10 minute timeout for pull
             )
             if pull_result.returncode != 0:
                 # Pull failed - check if image exists locally
                 check_local = subprocess.run(
                     ["docker", "images", "-q", image],
                     capture_output=True,
                     text=True
                 )
                 if check_local.returncode == 0 and check_local.stdout.strip():
                     # Image exists locally, proceed with warning/info
                     print(f"Warning: Failed to pull '{image}', using local version.")
                 else:
                     return jsonify({
                         "success": False,
                         "error": f"Failed to pull image '{image}' and not found locally: {pull_result.stderr}"
                     }), 500
        except subprocess.TimeoutExpired:
             # Timeout - check if image exists locally
             check_local = subprocess.run(
                 ["docker", "images", "-q", image],
                 capture_output=True,
                 text=True
             )
             if check_local.returncode == 0 and check_local.stdout.strip():
                 print(f"Warning: Timed out pulling '{image}', using local version.")
             else:
                 return jsonify({
                     "success": False,
                     "error": f"Timed out pulling image '{image}'"
                 }), 500
        except Exception as e:
             return jsonify({
                 "success": False,
                 "error": f"Error pulling image '{image}': {str(e)}"
             }), 500

        # Add service to docker-compose.yaml
        try:
            container_name = add_service(
                name=safe_name,
                image=image,
                command=command if command else [],
                env_vars=env_var_names,
                description=description,
                volumes=volumes if volumes else None
            )
        except ComposeError as e:
            return jsonify({
                "success": False,
                "error": f"Failed to add service: {str(e)}"
            }), 500

        # Create MCP config file
        try:
            config_path = create_mcp_config(
                name=safe_name,
                container_name=container_name,
                command=command if command else ["stdio"],
                description=description
            )
        except ComposeError as e:
            # Rollback: remove service from override
            remove_service(safe_name)
            return jsonify({
                "success": False,
                "error": f"Failed to create config: {str(e)}"
            }), 500

        # add_service() already triggered host reload via systemd
        # add_service() already triggered host reload via systemd
        
        # Wait for container to start (polling for up to 60s to allow for image pulls)
        max_retries = 30
        container_running = False
        container_status = "unknown"
        
        for _ in range(max_retries):
            time.sleep(2)
            status = get_container_status(container_name)
            container_running = status.get("running", False)
            container_status = status.get("status", "unknown")
            if container_running:
                break
        
        if not container_running:
            # If container didn't start, registration will definitely fail
            delete_mcp_config(safe_name)
            remove_service(safe_name)
            return jsonify({
                "success": False,
                "error": f"Container failed to start after 60s. Status: {container_status}. Check docker logs."
            }), 500

        # Register server with MCPJungle
        register_result = exec_emcp(["register", "-c", f"/configs/{safe_name}.json"])
        if register_result.returncode != 0:
            error_msg = register_result.stderr.strip() or register_result.stdout.strip()
            # Rollback
            delete_mcp_config(safe_name)
            remove_service(safe_name)
            return jsonify({
                "success": False,
                "error": f"Failed to register with MCPJungle: {error_msg}"
            }), 500

        # Count discovered tools
        tool_count = 0
        try:
            tools_response = requests.get(f"{MCPJUNGLE_API}/api/v0/tools", timeout=10)
            if tools_response.ok:
                all_tools = tools_response.json()
                tool_count = len([t for t in all_tools if t.get("name", "").startswith(f"{safe_name}__")])
        except Exception:
            pass  # Tool count is optional

        # Server was added - success. Container status is separate.
        response = {
            "success": True,
            "message": f"Server '{safe_name}' added",
            "name": safe_name,
            "container_name": container_name,
            "container_running": container_running,
            "container_status": container_status,
            "tool_count": tool_count,
            "infisical_configured": infisical_configured()
        }

        if not container_running:
            response["warning"] = f"Container status: {container_status}. Check 'docker logs {container_name}' if it doesn't start."

        return jsonify(response)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Provisioning failed: {str(e)}"
        }), 500


@app.route('/api/servers', methods=['GET'])
def api_list_servers():
    """
    List all MCP servers.

    Returns server info including:
    - name: Server name
    - container_name: Docker container name
    - running: Whether container is running
    - tool_count: Number of tools from this server
    """
    try:
        servers = []

        # Get all tools to count per server
        tool_counts = {}
        try:
            tools_response = requests.get(f"{MCPJUNGLE_API}/api/v0/tools", timeout=10)
            if tools_response.ok:
                for tool in tools_response.json():
                    server_name = tool.get("name", "").split("__")[0]
                    tool_counts[server_name] = tool_counts.get(server_name, 0) + 1
        except Exception:
            pass

        # Get servers from configs directory
        configs_dir = "/configs"
        if os.path.exists(configs_dir):
            for filename in os.listdir(configs_dir):
                if filename.endswith('.json'):
                    config_path = os.path.join(configs_dir, filename)
                    try:
                        with open(config_path) as f:
                            config = json.load(f)
                            name = config.get("name", filename[:-5])
                            container_name = f"{name}-mcp"

                            status = get_container_status(container_name)
                            servers.append({
                                "name": name,
                                "container_name": container_name,
                                "description": config.get("description", ""),
                                "running": status.get("running", False),
                                "status": status.get("status", "unknown"),
                                "tool_count": tool_counts.get(name, 0)
                            })
                    except Exception:
                        continue

        return jsonify({
            "success": True,
            "servers": servers
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/servers/<name>', methods=['DELETE'])
def api_delete_server(name):
    """
    Delete an MCP server.

    This will:
    1. Deregister from MCPJungle
    2. Delete the MCP config file
    3. Remove from docker-compose.yaml (triggers host reload)
    4. Host reload stops/removes the container
    """
    try:
        # Deregister from MCPJungle first
        exec_emcp(["deregister", name])
        # Ignore errors - server might not be registered

        # Delete config file
        delete_mcp_config(name)

        # Remove from docker-compose.yaml (this triggers host reload)
        # The reload will stop/remove the container
        removed = remove_service(name)

        if not removed:
            return jsonify({
                "success": False,
                "error": f"Server '{name}' not found in docker-compose.yaml"
            }), 404

        return jsonify({
            "success": True,
            "message": f"Server '{name}' deleted."
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/servers/<name>/restart', methods=['POST'])
def api_restart_server(name):
    """
    Restart an MCP server container.

    Uses docker restart directly (works via socket).
    """
    try:
        container_name = f"{name}-mcp"

        result = subprocess.run(
            ["docker", "restart", container_name],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            return jsonify({
                "success": True,
                "message": f"Server '{name}' restarted"
            })
        else:
            return jsonify({
                "success": False,
                "error": result.stderr or "Failed to restart container"
            }), 500

    except subprocess.TimeoutExpired:
        return jsonify({
            "success": False,
            "error": "Timeout waiting for container to restart"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/servers/infisical-status', methods=['GET'])
def api_infisical_status():
    """Check if Infisical is configured for secret management."""
    return jsonify({
        "success": True,
        "configured": infisical_configured()
    })


if __name__ == '__main__':
    # Ensure groups and presets directories exist
    os.makedirs(GROUPS_DIR, exist_ok=True)
    os.makedirs(PRESETS_DIR, exist_ok=True)

    # Run Flask server
    app.run(host='0.0.0.0', port=5000, debug=False)
