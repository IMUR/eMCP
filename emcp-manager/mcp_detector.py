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
        result["npm_package"] = pkg_data.get("name")

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

    # Check for ghcr.io Docker image
    ghcr_image = f"ghcr.io/{owner}/{repo_name}:latest"
    result["image"] = ghcr_image

    # Try to detect env vars from README
    readme_urls = [
        f"https://raw.githubusercontent.com/{owner}/{repo_name}/main/README.md",
        f"https://raw.githubusercontent.com/{owner}/{repo_name}/master/README.md",
    ]

    for readme_url in readme_urls:
        try:
            response = requests.get(readme_url, timeout=10)
            if response.ok:
                env_vars = detect_env_vars(response.text)
                result["required_env_vars"] = env_vars
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
        "detected_from": "npm"
    }

    # Check for bin field
    bin_field = version_data.get("bin")
    if bin_field:
        # bunx handles bin resolution, so command stays as bunx <package>
        pass

    # Try to detect env vars from README
    readme = data.get("readme", "")
    if readme:
        result["required_env_vars"] = detect_env_vars(readme)

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
