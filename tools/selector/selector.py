#!/usr/bin/env python3
"""
eMCP Tool Selector

Agentic tool selection using Ollama with the emcp-selector model.
The model explores a project and selects relevant tools from the inventory.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import ollama

# Configuration
MODEL = os.getenv("EMCP_SELECTOR_MODEL", "emcp-selector")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Resolve paths relative to eMCP root (two levels up from script)
EMCP_ROOT = Path(__file__).parent.parent.parent
METADATA_PATH = os.getenv("EMCP_METADATA_PATH", str(EMCP_ROOT / "data" / "tool_metadata.json"))


# Tool functions - these are what the model can call

def read_file(path: str) -> str:
    """Read contents of a file.

    Args:
        path: Path to the file to read

    Returns:
        str: The file contents, or an error message
    """
    try:
        with open(path, 'r') as f:
            content = f.read()
            # Truncate very large files
            if len(content) > 10000:
                return content[:10000] + "\n... (truncated)"
            return content
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error reading file: {e}"


def list_directory(path: str) -> str:
    """List contents of a directory.

    Args:
        path: Path to the directory to list

    Returns:
        str: Directory listing, or an error message
    """
    try:
        p = Path(path)
        if not p.exists():
            return f"Error: Directory not found: {path}"
        if not p.is_dir():
            return f"Error: Not a directory: {path}"

        entries = []
        for entry in sorted(p.iterdir()):
            if entry.name.startswith('.'):
                continue  # Skip hidden files
            prefix = "d " if entry.is_dir() else "f "
            entries.append(prefix + entry.name)

        return "\n".join(entries[:100])  # Limit to 100 entries
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error listing directory: {e}"


def run_command(cmd: str) -> str:
    """Run a shell command and return output.

    Args:
        cmd: The command to run

    Returns:
        str: Command output (stdout + stderr), or an error message
    """
    # Safety: only allow certain commands
    allowed_prefixes = ['git ', 'ls ', 'cat ', 'head ', 'tree ']
    if not any(cmd.startswith(p) for p in allowed_prefixes):
        return f"Error: Command not allowed. Only git, ls, cat, head, tree are permitted."

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=PROJECT_PATH  # Run in project directory
        )
        output = result.stdout + result.stderr
        if len(output) > 5000:
            return output[:5000] + "\n... (truncated)"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        return f"Error running command: {e}"


def read_tool_metadata() -> str:
    """Load the tool inventory with taxonomy metadata.

    Returns:
        str: JSON string of all tools with their taxonomy
    """
    try:
        with open(METADATA_PATH, 'r') as f:
            tools = json.load(f)

        return json.dumps(tools, indent=2)
    except FileNotFoundError:
        return f"Error: Metadata file not found: {METADATA_PATH}"
    except json.JSONDecodeError as e:
        return f"Error parsing metadata: {e}"
    except Exception as e:
        return f"Error loading metadata: {e}"


# Available tools for the model
TOOLS = [read_file, list_directory, run_command, read_tool_metadata]

AVAILABLE_FUNCTIONS = {
    'read_file': read_file,
    'list_directory': list_directory,
    'run_command': run_command,
    'read_tool_metadata': read_tool_metadata,
}

# Global project path (set by main)
PROJECT_PATH = "."


def select_tools(project_path: str, verbose: bool = False) -> dict:
    """
    Run the agentic tool selection for a project.

    Args:
        project_path: Path to the project to analyze
        verbose: If True, print the model's reasoning

    Returns:
        dict: Selection result with 'selected_tools' and 'reasoning'
    """
    global PROJECT_PATH
    PROJECT_PATH = os.path.abspath(project_path)

    if not os.path.isdir(PROJECT_PATH):
        return {"error": f"Not a directory: {PROJECT_PATH}"}

    # Initial message
    messages = [{
        'role': 'user',
        'content': f'Analyze the project at {PROJECT_PATH} and select the most relevant tools. '
                   f'Start by exploring the project structure, then read the tool metadata, '
                   f'then make your selection.'
    }]

    if verbose:
        print(f"Analyzing project: {PROJECT_PATH}")
        print("-" * 50)

    # Agentic loop
    max_iterations = 20
    for i in range(max_iterations):
        response = ollama.chat(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
        )

        # Check if model made tool calls
        if not response.message.tool_calls:
            # Model provided final answer
            content = response.message.content
            if verbose:
                print(f"\nFinal response:\n{content}")

            # Try to parse as JSON
            try:
                # Find JSON in the response
                start = content.find('{')
                end = content.rfind('}') + 1
                if start >= 0 and end > start:
                    result = json.loads(content[start:end])
                    return result
                else:
                    return {"error": "No JSON found in response", "raw": content}
            except json.JSONDecodeError:
                return {"error": "Failed to parse response", "raw": content}

        # Process tool calls
        for tool_call in response.message.tool_calls:
            func_name = tool_call.function.name
            func_args = tool_call.function.arguments

            if verbose:
                print(f"Tool call: {func_name}({func_args})")

            function = AVAILABLE_FUNCTIONS.get(func_name)
            if function:
                result = function(**func_args)
                if verbose:
                    preview = result[:200] + "..." if len(result) > 200 else result
                    print(f"Result: {preview}\n")
            else:
                result = f"Error: Unknown function {func_name}"

            # Add to conversation
            messages.append(response.message)
            messages.append({
                'role': 'tool',
                'content': result,
            })

    return {"error": "Max iterations reached without final answer"}


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="eMCP Tool Selector")
    parser.add_argument("project_path", help="Path to project to analyze")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--model", default=MODEL, help=f"Ollama model (default: {MODEL})")

    args = parser.parse_args()

    global MODEL
    MODEL = args.model

    result = select_tools(args.project_path, verbose=args.verbose)

    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        if "raw" in result:
            print(f"Raw response: {result['raw']}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
