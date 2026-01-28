"""
MCP Server Metadata Detector

Parses URLs and fetches metadata for MCP servers from various sources:
- GitHub repositories
- npm packages
- Docker images
"""

import re
import requests
from typing import Optional
from urllib.parse import urlparse


class DetectionError(Exception):
    """Exception raised when detection fails."""
    pass


def parse_mcp_url(url: str) -> dict:
    """
    Parse a URL and determine the source type.

    Args:
        url: URL or identifier (GitHub URL, npm package, Docker image)

    Returns:
        dict: {
            "type": "github" | "npm" | "docker",
            "identifier": str,  # repo path, package name, or image ref
            "raw_url": str
        }

    Raises:
        DetectionError: If URL format is not recognized
    """
    url = url.strip()

    # GitHub URL patterns
    github_patterns = [
        r'^https?://github\.com/([^/]+/[^/]+)/?.*$',
        r'^github\.com/([^/]+/[^/]+)/?.*$',
        r'^gh:([^/]+/[^/]+)$',
    ]
    for pattern in github_patterns:
        match = re.match(pattern, url)
        if match:
            repo = match.group(1).rstrip('.git')
            return {
                "type": "github",
                "identifier": repo,
                "raw_url": url
            }

    # npm package patterns
    npm_patterns = [
        r'^https?://(?:www\.)?npmjs\.com/package/(.+)$',
        r'^npm:(.+)$',
    ]
    for pattern in npm_patterns:
        match = re.match(pattern, url)
        if match:
            return {
                "type": "npm",
                "identifier": match.group(1),
                "raw_url": url
            }

    # Scoped npm package (starts with @)
    if url.startswith('@') and '/' in url:
        return {
            "type": "npm",
            "identifier": url,
            "raw_url": url
        }

    # Docker image patterns
    docker_patterns = [
        r'^(ghcr\.io/.+)$',
        r'^(docker\.io/.+)$',
        r'^([\w.-]+\.[\w.-]+/.+:.+)$',  # registry.example.com/image:tag
        r'^docker:(.+)$',
    ]
    for pattern in docker_patterns:
        match = re.match(pattern, url)
        if match:
            return {
                "type": "docker",
                "identifier": match.group(1),
                "raw_url": url
            }

    # Plain package name (assume npm)
    if re.match(r'^[\w.-]+$', url):
        return {
            "type": "npm",
            "identifier": url,
            "raw_url": url
        }

    # Check if it looks like a Docker image (has slash but no github.com)
    if '/' in url and 'github' not in url.lower():
        return {
            "type": "docker",
            "identifier": url,
            "raw_url": url
        }

    raise DetectionError(f"Could not determine source type for: {url}")


def fetch_github_metadata(repo: str) -> dict:
    """
    Fetch metadata from a GitHub repository.

    Args:
        repo: Repository path (e.g., "owner/repo")

    Returns:
        dict: {
            "name": str,
            "description": str,
            "image": str or None,
            "npm_package": str or None,
            "command": list[str],
            "required_env_vars": list[str],
            "detected_from": str
        }

    Raises:
        DetectionError: If metadata cannot be fetched
    """
    owner, repo_name = repo.split('/')
    repo_name = repo_name.rstrip('.git')

    result = {
        "name": _extract_server_name(repo_name),
        "description": "",
        "image": None,
        "npm_package": None,
        "command": [],
        "required_env_vars": [],
        "required_args": [],
        "detected_from": None
    }

    # Try to fetch package.json
    pkg_urls = [
        f"https://raw.githubusercontent.com/{owner}/{repo_name}/main/package.json",
        f"https://raw.githubusercontent.com/{owner}/{repo_name}/master/package.json",
    ]

    pkg_data = None
    for pkg_url in pkg_urls:
        try:
            response = requests.get(pkg_url, timeout=10)
            if response.ok:
                pkg_data = response.json()
                result["detected_from"] = "package.json"
                break
        except Exception:
            continue

    if pkg_data:
        result["description"] = pkg_data.get("description", "")
        npm_name = pkg_data.get("name")
        result["npm_package"] = npm_name

        # For npm packages, use bun to run them
        if npm_name:
            result["image"] = "oven/bun:1"
            result["command"] = ["bunx", npm_name]
        else:
            # Detect command from bin field
            bin_field = pkg_data.get("bin")
            if bin_field:
                if isinstance(bin_field, str):
                    result["command"] = ["node", bin_field]
                elif isinstance(bin_field, dict):
                    first_bin = list(bin_field.values())[0]
                    result["command"] = ["node", first_bin]

            # If no bin, try main field
            if not result["command"]:
                main = pkg_data.get("main")
                if main:
                    result["command"] = ["node", main]

            # No npm package name, try ghcr.io
            result["image"] = f"ghcr.io/{owner}/{repo_name}:latest"
    else:
        # No package.json - might be Go/Rust with Docker releases
        result["image"] = f"ghcr.io/{owner}/{repo_name}:latest"
        result["command"] = ["stdio"]  # Common MCP server arg

    # Try to detect env vars and required args from README
    readme_urls = [
        f"https://raw.githubusercontent.com/{owner}/{repo_name}/main/README.md",
        f"https://raw.githubusercontent.com/{owner}/{repo_name}/master/README.md",
    ]

    for readme_url in readme_urls:
        try:
            response = requests.get(readme_url, timeout=10)
            if response.ok:
                readme_text = response.text
                result["required_env_vars"] = detect_env_vars(readme_text)
                result["required_args"] = detect_required_args(readme_text, result.get("npm_package", ""))
                if not result["detected_from"]:
                    result["detected_from"] = "readme"
                break
        except Exception:
            continue

    # If still no command, default for MCP servers
    if not result["command"]:
        result["command"] = ["node", "dist/index.js", "stdio"]

    return result


def fetch_npm_metadata(package_name: str) -> dict:
    """
    Fetch metadata from npm registry.

    Args:
        package_name: npm package name (e.g., "@org/package" or "package")

    Returns:
        dict: Same structure as fetch_github_metadata

    Raises:
        DetectionError: If package is not found
    """
    # URL-encode scoped packages
    encoded_name = package_name.replace('/', '%2f')
    url = f"https://registry.npmjs.org/{encoded_name}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 404:
            raise DetectionError(f"npm package not found: {package_name}")
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise DetectionError(f"Failed to fetch npm metadata: {e}")

    data = response.json()
    latest_version = data.get("dist-tags", {}).get("latest", "")
    version_data = data.get("versions", {}).get(latest_version, {})

    result = {
        "name": _extract_server_name(package_name.split('/')[-1]),
        "description": data.get("description", ""),
        "image": "oven/bun:1",  # Default to Bun for npm packages
        "npm_package": package_name,
        "command": ["bunx", package_name],
        "required_env_vars": [],
        "required_args": [],
        "detected_from": "npm"
    }

    # Check for bin field
    bin_field = version_data.get("bin")
    if bin_field:
        # bunx handles bin resolution, so command stays as bunx <package>
        pass

    # Try to detect env vars and required args from README
    readme = data.get("readme", "")
    if readme:
        result["required_env_vars"] = detect_env_vars(readme)
        result["required_args"] = detect_required_args(readme, package_name)

    # Check repository for GitHub to detect Docker image
    repo_info = data.get("repository", {})
    if isinstance(repo_info, dict):
        repo_url = repo_info.get("url", "")
        if "github.com" in repo_url:
            match = re.search(r'github\.com[:/]([^/]+)/([^/.]+)', repo_url)
            if match:
                owner, repo = match.groups()
                result["image"] = f"ghcr.io/{owner}/{repo}:latest"

    return result


def fetch_docker_metadata(image_ref: str) -> dict:
    """
    Create metadata for a Docker image.

    Note: We can't easily inspect remote images without pulling them,
    so this creates a basic config that the user can customize.

    Args:
        image_ref: Docker image reference (e.g., "ghcr.io/org/image:tag")

    Returns:
        dict: Same structure as fetch_github_metadata
    """
    # Extract name from image ref
    parts = image_ref.split('/')
    name_with_tag = parts[-1]
    name = name_with_tag.split(':')[0]

    result = {
        "name": _extract_server_name(name),
        "description": f"MCP server from {image_ref}",
        "image": image_ref,
        "npm_package": None,
        "command": [],  # User will need to specify
        "required_env_vars": [],
        "required_args": [],
        "detected_from": "docker"
    }

    # Common command patterns for MCP servers
    result["command"] = ["stdio"]  # Many MCP servers just need "stdio" arg

    return result


def detect_env_vars(text: str) -> list[str]:
    """
    Detect environment variable names from text (README, documentation).

    Looks for common patterns:
    - `API_KEY`, `$API_KEY`, `${API_KEY}`
    - Environment variable sections in docs
    - Variable names with common suffixes (_KEY, _TOKEN, _SECRET, etc.)

    Args:
        text: Text to search

    Returns:
        list[str]: Unique environment variable names found
    """
    env_vars = set()

    # Pattern for common env var naming conventions
    patterns = [
        # Variables with common suffixes
        r'\b([A-Z][A-Z0-9_]*(?:_KEY|_TOKEN|_SECRET|_API_KEY|_ACCESS_TOKEN|_PASSWORD|_CREDENTIAL))\b',
        # Variables in backticks
        r'`([A-Z][A-Z0-9_]{2,})`',
        # Variables with $ prefix
        r'\$\{?([A-Z][A-Z0-9_]{2,})\}?',
        # Variables in example code (KEY=value patterns)
        r'\b([A-Z][A-Z0-9_]{2,})=["\']?[^"\'\s]+["\']?',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        env_vars.update(matches)

    # Filter out common false positives
    false_positives = {
        'README', 'MIT', 'API', 'CLI', 'NPM', 'URL', 'HTTP', 'HTTPS',
        'JSON', 'TRUE', 'FALSE', 'NULL', 'ENV', 'PATH', 'HOME', 'USER',
        'NODE', 'VERSION', 'EXAMPLE', 'CONFIG', 'DEFAULT', 'OPTIONS',
        'MCP', 'SERVER', 'CLIENT', 'HOST', 'PORT'
    }
    env_vars = {v for v in env_vars if v not in false_positives}

    # Sort for consistent output
    return sorted(env_vars)


def detect_required_args(text: str, package_name: str = "") -> list[dict]:
    """
    Detect required command-line arguments from text (README, documentation).

    Looks for patterns like:
    - Usage: command <path>
    - Usage: npx @package/name /path/to/vault
    - Required: path to X

    Args:
        text: Text to search
        package_name: Package name to look for in usage examples

    Returns:
        list[dict]: List of {name, description, placeholder} for each required arg
    """
    args = []

    # Pattern 1: Usage lines with angle brackets <arg> or positional paths
    # e.g., "Usage: npx @package/name <path>" or "Usage: command /path/to/vault"
    usage_patterns = [
        # <argument> style
        r'[Uu]sage:?\s*(?:npx\s+)?(?:@?[\w./-]+\s+)?<([^>]+)>',
        # /path/to/something style
        r'[Uu]sage:?\s*(?:npx\s+)?(?:@?[\w./-]+)\s+(/\S+)',
        # [required] style
        r'[Uu]sage:?\s*(?:npx\s+)?(?:@?[\w./-]+\s+)?\[([^\]]+)\]',
    ]

    for pattern in usage_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            arg_name = match.strip()
            # Skip optional indicators
            if arg_name.lower().startswith('option'):
                continue
            # Normalize path-like args
            if arg_name.startswith('/path') or 'path' in arg_name.lower():
                args.append({
                    "name": "path",
                    "description": f"Path argument: {arg_name}",
                    "placeholder": "/path/to/directory"
                })
            elif 'vault' in arg_name.lower():
                args.append({
                    "name": "vault_path",
                    "description": "Path to Obsidian vault",
                    "placeholder": "/path/to/vault"
                })
            elif 'dir' in arg_name.lower() or 'folder' in arg_name.lower():
                args.append({
                    "name": "directory",
                    "description": f"Directory: {arg_name}",
                    "placeholder": "/path/to/directory"
                })
            else:
                args.append({
                    "name": arg_name.replace(' ', '_').replace('-', '_').lower(),
                    "description": arg_name,
                    "placeholder": f"<{arg_name}>"
                })

    # Pattern 2: Look for "Required:" or "Required argument:" sections
    required_pattern = r'[Rr]equired(?:\s+argument)?:?\s*[`"]?([^`"\n]+)[`"]?'
    matches = re.findall(required_pattern, text)
    for match in matches:
        match = match.strip()
        if match and len(match) < 100:  # Sanity check
            # Check if it's describing a path
            if 'path' in match.lower() or 'directory' in match.lower() or 'folder' in match.lower():
                arg_name = "path"
                if 'vault' in match.lower():
                    arg_name = "vault_path"
                args.append({
                    "name": arg_name,
                    "description": match,
                    "placeholder": "/path/to/directory"
                })

    # Pattern 3: Common MCP patterns - look for specific keywords
    if 'vault' in text.lower() and 'obsidian' in text.lower():
        # Obsidian-specific detection
        if not any(a['name'] == 'vault_path' for a in args):
            args.append({
                "name": "vault_path",
                "description": "Path to Obsidian vault",
                "placeholder": "/path/to/obsidian/vault"
            })

    # Deduplicate by name
    seen = set()
    unique_args = []
    for arg in args:
        if arg['name'] not in seen:
            seen.add(arg['name'])
            unique_args.append(arg)

    return unique_args


def detect_server(url: str) -> dict:
    """
    Main entry point: detect server metadata from any URL.

    Args:
        url: URL or identifier

    Returns:
        dict: Detected server configuration

    Raises:
        DetectionError: If detection fails
    """
    parsed = parse_mcp_url(url)

    if parsed["type"] == "github":
        return fetch_github_metadata(parsed["identifier"])
    elif parsed["type"] == "npm":
        return fetch_npm_metadata(parsed["identifier"])
    elif parsed["type"] == "docker":
        return fetch_docker_metadata(parsed["identifier"])
    else:
        raise DetectionError(f"Unknown source type: {parsed['type']}")


def _extract_server_name(raw_name: str) -> str:
    """
    Extract a clean server name from a package/repo name.

    Examples:
        "my-mcp-server" -> "my"
        "@org/mcp-package" -> "package"
        "github-mcp-server" -> "github"
    """
    name = raw_name.lower()

    # Remove common MCP-related suffixes/prefixes
    name = re.sub(r'^mcp[-_]', '', name)
    name = re.sub(r'[-_]mcp$', '', name)
    name = re.sub(r'[-_]mcp[-_]server$', '', name)
    name = re.sub(r'[-_]server$', '', name)

    # Remove scope prefix
    if '/' in name:
        name = name.split('/')[-1]

    # Clean up remaining
    name = re.sub(r'^[@]', '', name)
    name = re.sub(r'[^a-z0-9-]', '-', name)
    name = re.sub(r'-+', '-', name)
    name = name.strip('-')

    return name or "custom"
