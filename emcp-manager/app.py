#!/usr/bin/env python3
"""
Simple Flask API for eMCP tool selection
"""
from flask import Flask, jsonify, request, send_from_directory
import subprocess
import json
import os
import requests

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


if __name__ == '__main__':
    # Ensure groups and presets directories exist
    os.makedirs(GROUPS_DIR, exist_ok=True)
    os.makedirs(PRESETS_DIR, exist_ok=True)

    # Run Flask server
    app.run(host='0.0.0.0', port=5000, debug=False)
