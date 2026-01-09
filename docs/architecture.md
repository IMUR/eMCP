# eMCP Architecture

**Status:** Active
**Last Updated:** 2026-01-09

---

## Overview

eMCP is a Tool Access Broker that filters which MCP tools AI agents can access. The core mission is **resource conservation**: every enabled tool consumes tokens and adds cognitive overhead.

---

## Two Parts

The broker system has exactly two parts:

| Part                    | Purpose                                              | Trigger                       |
|-------------------------|------------------------------------------------------|-------------------------------|
| **Taxonomy Extraction** | Analyze tools, extract operations/domain/token_count | When tool inventory changes   |
| **Tool Selection**      | Analyze project, select best tools                   | When tools need to be selected |

There is no third part. No profiler. No intermediate analysis step.

---

## The Model Performs Analysis

Both parts follow the same pattern: **the model analyzes, the model outputs**.

### Taxonomy Extraction

- Model analyzes tool descriptions
- Model outputs: operations, domain, token_count per tool
- Result stored in `data/tool_metadata.json`

### Tool Selection

- Model explores project (using tools for file access)
- Model reads tool metadata
- Model reasons from taxonomy + project context
- Model outputs: selected tools

No external "agent" gathering info. No pre-packaged input. The model does the analysis.

---

## The Selector Model is Agentic

The selector model has tools to explore the project:

- `read_file(path)` - Read file contents
- `list_directory(path)` - List directory contents
- `run_command(cmd)` - Run shell commands (git remote, etc.)
- `read_tool_metadata()` - Load the taxonomy data

The model decides what to look at. The model explores. The model reasons. The model outputs.

---

## The Taxonomy Provides Logical Markers

The tool taxonomy provides everything needed for selection:

- **operations**: research, read, write, generate, transform, control
- **domain**: development.vcs, media.audio, physical.geospatial, etc.
- **name**: Server prefix (github__, gitea__, mapbox__)
- **token_count**: Cost for budget allocation

The model sees these markers. The model sees the project context (git remote, file structure, configs). The model reasons about what tools fit.

No separate "rules" needed. The taxonomy IS the vocabulary for reasoning.

---

## The Modelfile Explains the Taxonomy

The Modelfile does NOT encode selection rules. It explains what the taxonomy fields mean:

- What does "operations: research" mean?
- What does "operations: write" mean?
- What does "domain: development.vcs" mean?
- How do these relate to project context?

The model uses this understanding to reason. The model is not following pre-encoded rules - it's reasoning from understood concepts.

---

## System Components

```text
┌─────────────────────────────────────────────────────────────┐
│                        OLLAMA                               │
│                                                             │
│  emcp-extractor model:                                      │
│    - Analyzes tool descriptions                             │
│    - Understands: what is an operation? what is a domain?   │
│    - Outputs: operations, domain, token_count per tool      │
│    - Result stored in data/tool_metadata.json               │
│                                                             │
│  emcp-selector model (agentic):                             │
│    - Tools: read_file, list_directory, run_command          │
│    - Explores project using tools                           │
│    - Reads tool_metadata.json                               │
│    - Reasons from taxonomy + project context                │
│    - Outputs: selected tools                                │
│                                                             │
│  Base: qwen2.5-coder:1.5b                                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    MCPJungle Gateway                        │
│                                                             │
│  - Aggregates MCP servers into unified endpoint             │
│  - Routes tool calls to appropriate servers                 │
│  - Manages groups and tool filtering                        │
│  - Endpoint: /v0/groups/{group}/mcp                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    eMCP Manager                             │
│                                                             │
│  - Web UI for manual tool selection                         │
│  - Browse available tools by server                         │
│  - Enable/disable tools via checkboxes                      │
│  - Save/load presets                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## What This Architecture Avoids

| Avoided                  | Reason                                          |
|--------------------------|-------------------------------------------------|
| Sophistication profiler  | Selector reasons directly from project context  |
| Intermediate schemas     | No project schema, no pre-analyzed input        |
| Pre-encoded rules        | Model reasons from taxonomy understanding       |
| FAISS / embeddings       | Taxonomy + LLM reasoning is sufficient          |
| External agent handoff   | Model explores and selects in one process       |

---

## Directory Structure

```text
eMCP/
├── configs/              # MCP server configurations
├── data/                 # Tool metadata (taxonomy output)
├── docs/                 # Documentation
├── emcp-manager/         # Web UI for manual selection
├── groups/               # Tool group definitions
├── modelfiles/           # Extractor and selector Modelfiles
└── tools/                # Agentic tool definitions
    ├── extractor/
    └── selector/
```
