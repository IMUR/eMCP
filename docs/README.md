# eMCP Documentation

eMCP is a Tool Access Broker for MCP (Model Context Protocol) systems.

---

## Documents

| Document                        | Description                                    |
|---------------------------------|------------------------------------------------|
| [architecture.md](architecture.md) | System architecture and components          |
| [taxonomy.md](taxonomy.md)         | Tool taxonomy schema and classification     |

---

## Quick Summary

**Problem:** AI agents with access to too many tools suffer from context overload. Every tool costs tokens.

**Solution:** eMCP filters which tools are exposed based on project context.

**How it works:**

1. **Taxonomy Extraction** - Analyze tools, classify by operations and domain
2. **Tool Selection** - Agentic model explores project, selects relevant tools

**Key insight:** The model does the analysis. No pre-packaged inputs, no intermediate schemas, no hardcoded rules.
