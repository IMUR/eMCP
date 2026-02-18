# Groups

Groups control which tools are exposed to your AI agent. Each group defines a subset of available tools.

## How Groups Work

When your AI agent connects to eMCP, it connects to a **group endpoint**:

```
http://localhost:8090/v0/groups/{group-name}/mcp
```

The group filters the available tools so the agent only sees what you've enabled.

## Default Group

eMCP ships with a default group called `emcp-global`. This is the group used when no specific group is specified.

## Managing Groups via Web UI

1. Open **<http://localhost:5010>**
2. Toggle tools on/off to add/remove them from the active group
3. Changes persist immediately to the group JSON file

## Group File Format

Groups are stored as JSON files in the `groups/` directory:

```json
{
    "name": "my-workflow",
    "description": "Tools for my specific workflow",
    "included_tools": [
        "filesystem__read_file",
        "filesystem__write_file",
        "filesystem__list_directory"
    ]
}
```

Tool names follow the pattern `{server}__{tool}`.

## Managing Groups via API

### List tools in current group

```bash
curl http://localhost:5010/api/current
```

### Toggle a tool

```bash
curl -X POST http://localhost:5010/api/tools/toggle \
  -H "Content-Type: application/json" \
  -d '{"tool": "filesystem__read_file"}'
```

### Get all available tools

```bash
curl http://localhost:5010/api/tools
```

## Creating Custom Groups

Create a new JSON file in `groups/`:

```bash
cat > groups/minimal.json << 'EOF'
{
    "name": "minimal",
    "description": "Read-only filesystem access",
    "included_tools": [
        "filesystem__read_file",
        "filesystem__list_directory"
    ]
}
EOF
```

Then connect your agent to:

```
http://localhost:8090/v0/groups/minimal/mcp
```
