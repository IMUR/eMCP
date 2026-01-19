#!/usr/bin/env python3
"""
eMCP Taxonomy Extractor

Extracts taxonomy metadata (operations, domain, token_count) from tool descriptions
using the emcp-extractor Ollama model.
"""

import json
import os
import sys
from pathlib import Path

import ollama
import requests

# Configuration
MODEL = os.getenv("EMCP_EXTRACTOR_MODEL", "emcp-extractor")
MCPJUNGLE_API = os.getenv("MCPJUNGLE_API", "http://localhost:8090")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Resolve paths relative to eMCP root (two levels up from script)
EMCP_ROOT = Path(__file__).parent.parent.parent
OUTPUT_PATH = os.getenv("EMCP_METADATA_PATH", str(EMCP_ROOT / "data" / "tool_metadata.json"))


def fetch_tools_from_mcpjungle() -> list:
    """Fetch all tools from MCPJungle API.

    Returns:
        list: List of tool dicts with name, description, etc.
    """
    try:
        response = requests.get(f"{MCPJUNGLE_API}/api/v0/tools", timeout=30)
        response.raise_for_status()
        data = response.json()

        # MCPJungle returns a flat list of tools with format "server__toolname"
        tools = []
        for tool in data:
            name = tool.get("name", "")
            parts = name.split("__", 1)
            server_name = parts[0] if len(parts) > 1 else "unknown"

            tools.append({
                "server": server_name,
                "name": name,
                "description": tool.get("description", ""),
                "input_schema": tool.get("inputSchema", {}),
            })

        return tools
    except requests.exceptions.RequestException as e:
        print(f"Error fetching tools from MCPJungle: {e}", file=sys.stderr)
        return []


def estimate_token_count(tool: dict) -> int:
    """Estimate token count for a tool based on its schema complexity.

    Args:
        tool: Tool dict with input_schema

    Returns:
        int: Estimated token count
    """
    schema = tool.get("input_schema", {})
    properties = schema.get("properties", {})

    # Base cost
    base = 80

    # Add for each property
    prop_cost = len(properties) * 30

    # Add for description length
    desc_cost = len(tool.get("description", "")) // 20

    return min(base + prop_cost + desc_cost, 500)


def extract_taxonomy(tool: dict) -> dict:
    """Extract taxonomy metadata for a single tool using the extractor model.

    Args:
        tool: Tool dict with name and description

    Returns:
        dict: Tool with operations and domain added
    """
    prompt = f"""Extract taxonomy for this tool:

Name: {tool['name']}
Description: {tool['description']}

Output JSON with: name, operations (list), domain, token_count"""

    try:
        response = ollama.chat(
            model=MODEL,
            messages=[{'role': 'user', 'content': prompt}],
        )

        content = response.message.content

        # Parse JSON from response
        start = content.find('{')
        end = content.rfind('}') + 1
        if start >= 0 and end > start:
            result = json.loads(content[start:end])
            # Ensure required fields
            return {
                "name": tool["name"],
                "server": tool.get("server", tool["name"].split("__")[0]),
                "description": tool["description"],
                "operations": result.get("operations", ["read"]),
                "domain": result.get("domain", "unknown"),
                "token_count": result.get("token_count", estimate_token_count(tool)),
            }
    except Exception as e:
        print(f"Error extracting taxonomy for {tool['name']}: {e}", file=sys.stderr)

    # Fallback
    return {
        "name": tool["name"],
        "server": tool.get("server", tool["name"].split("__")[0]),
        "description": tool["description"],
        "operations": ["read"],
        "domain": "unknown",
        "token_count": estimate_token_count(tool),
    }


def extract_all(tools: list, verbose: bool = False) -> list:
    """Extract taxonomy for all tools.

    Args:
        tools: List of tool dicts
        verbose: Print progress

    Returns:
        list: Tools with taxonomy metadata
    """
    results = []

    for i, tool in enumerate(tools):
        if verbose:
            print(f"[{i+1}/{len(tools)}] Extracting: {tool['name']}")

        result = extract_taxonomy(tool)
        results.append(result)

        if verbose:
            print(f"  -> operations={result['operations']}, domain={result['domain']}")

    return results


def save_metadata(tools: list, output_path: str):
    """Save tool metadata to JSON file.

    Args:
        tools: List of tool metadata dicts
        output_path: Path to output file
    """
    # Ensure directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(tools, f, indent=2)

    print(f"Saved {len(tools)} tools to {output_path}")


def main():
    """CLI entry point."""
    global MODEL, MCPJUNGLE_API
    import argparse

    parser = argparse.ArgumentParser(description="eMCP Taxonomy Extractor")
    parser.add_argument("-o", "--output", default=OUTPUT_PATH, help="Output file path")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--model", default=MODEL, help=f"Ollama model (default: {MODEL})")
    parser.add_argument("--api", default=MCPJUNGLE_API, help="MCPJungle API URL")
    parser.add_argument("--from-file", help="Read tools from JSON file instead of API")

    args = parser.parse_args()

    MODEL = args.model
    MCPJUNGLE_API = args.api

    # Get tools
    if args.from_file:
        print(f"Loading tools from {args.from_file}")
        with open(args.from_file) as f:
            tools = json.load(f)
    else:
        print(f"Fetching tools from {MCPJUNGLE_API}")
        tools = fetch_tools_from_mcpjungle()

    if not tools:
        print("No tools found!", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(tools)} tools")

    # Extract taxonomy
    results = extract_all(tools, verbose=args.verbose)

    # Save
    save_metadata(results, args.output)


if __name__ == "__main__":
    main()
