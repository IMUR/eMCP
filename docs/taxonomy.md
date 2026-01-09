# Tool Taxonomy

**Status:** Active
**Last Updated:** 2026-01-09

---

## Overview

A universal taxonomy for MCP tool classification that enables systematic, context-aware tool selection. The taxonomy consists of universally extractable properties that apply to any tool regardless of domain.

---

## Schema

```json
{
  "name": "github__create_pull_request",
  "operations": ["write"],
  "domain": "development.vcs",
  "token_count": 150
}
```

### Fields

| Field         | Type     | Description                                                              |
|---------------|----------|--------------------------------------------------------------------------|
| `name`        | string   | Tool identifier. Server prefix implicit (e.g., `github__`, `mapbox__`)   |
| `operations`  | string[] | What the tool does. One or more operation categories.                    |
| `domain`      | string   | Functional area. Two-level hierarchy as `group.category`                 |
| `token_count` | integer  | Token cost for budget allocation                                         |

---

## Operation Categories

Six universal operations extractable from any tool's documentation:

| Operation     | Intent                      | Extraction Signals                              |
|---------------|-----------------------------|-------------------------------------------------|
| **research**  | Discover, search, explore   | "search", "find", "list", "query"               |
| **read**      | Retrieve specific resource  | "get", "fetch", "retrieve", "read"              |
| **write**     | Create, update, delete      | "create", "update", "delete", "push", "edit"    |
| **generate**  | Synthesize new artifact     | "generate", "compose", "synthesize", "render"   |
| **transform** | Convert between formats     | "convert", "transform", "parse", "encode"       |
| **control**   | Trigger external action     | "turn on", "send", "trigger", "execute", "call" |

### Multi-Operation Tools

A tool may have multiple operations (rare but valid):

```json
{
  "name": "some__search_and_transform",
  "operations": ["research", "transform"],
  "domain": "knowledge.search",
  "token_count": 250
}
```

---

## Domain Hierarchy

Two-level hierarchy: `group.category`

| Group              | Categories                              |
|--------------------|-----------------------------------------|
| **development**    | vcs, project, ci_cd, packages           |
| **infrastructure** | cloud, database, storage, monitoring    |
| **communication**  | messaging, email, social                |
| **knowledge**      | search, documentation                   |
| **media**          | audio, video, image                     |
| **physical**       | geospatial, iot, calendar               |
| **business**       | commerce, crm, analytics                |
| **identity**       | auth                                    |

### Examples

| Tool                              | Domain                 |
|-----------------------------------|------------------------|
| `github__create_pull_request`     | development.vcs        |
| `elevenlabs__text_to_speech`      | media.audio            |
| `mapbox__directions_tool`         | physical.geospatial    |
| `homeassistant__HassTurnOn`       | physical.iot           |
| `perplexity__perplexity_research` | knowledge.search       |
| `svelte__get-documentation`       | knowledge.documentation|
| `slack__send_message`             | communication.messaging|

---

## How Selection Uses Taxonomy

The selector model sees:

1. **Project context** - git remote, file structure, configs (via exploration)
2. **Tool metadata** - name, operations, domain, token_count (from taxonomy)

The model reasons:

- "This project is on GitHub (from git remote)"
- "This tool is `github__create_pull_request` with operations=write, domain=development.vcs"
- "Write operations to GitHub make sense for a GitHub project"
- "This tool is `gitea__create_issue` with operations=write, domain=development.vcs"
- "Write operations to Gitea don't make sense for a GitHub project"

The taxonomy provides the vocabulary. The model reasons from it.

---

## Design Principles

### 1. Systematic Over Specific

Solutions address the logical root, not symptoms. No "if GitHub then exclude Gitea" rules. The model understands what operations and domains mean, and reasons accordingly.

### 2. Universally Extractable Properties

Every field must be derivable from analyzing a tool's documentation, regardless of domain. If a property can't be extracted by reading docs for an arbitrary tool, it doesn't belong in the schema.

### 3. Derived Behavior, Not Encoded Rules

Selection behavior emerges from combining universal properties with project context - not from domain-specific fields or hardcoded logic. Adding a new platform requires only tool metadata, not algorithm changes.

### 4. Minimal Schema

If a concept can't be clearly defined and justified, it's vestigial. The schema contains only what's necessary:

- **operations** - What the tool does (universal verb)
- **domain** - What area it operates in (hierarchical noun)
- **token_count** - What it costs (budget constraint)

Server/platform is already encoded in the tool name.

---

## What Was Excluded

| Concept    | Reason for Exclusion                                         |
|------------|--------------------------------------------------------------|
| `platform` | Redundant - server is implicit in tool name prefix           |
| `binding`  | Not universally extractable - was VCS-specific framing       |
| `risk`     | Undefined, vestigial - no clear meaning for selection        |
| `scope`    | Captured by operation type                                   |
