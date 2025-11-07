# MCP Server Chat Application 🚀

Welcome! This chat application can discover, recommend, and integrate MCP (Model Context Protocol) servers to help you with various tasks.

## How to Use

### 1. **Ask a Question**
Simply describe what you need help with. The AI will analyze your query and recommend relevant MCP servers that could assist you.

### 2. **Connect MCP Servers**
When servers are recommended, connect them using:
```
connect <server_name>
```

For example: `connect time` or `connect filesystem`

### 3. **Use Connected Tools**
Once connected, the MCP server's tools become available to the AI agent, allowing it to help you with more advanced tasks!

## Available Commands
- `connect <server_name>` - Connect an MCP server
- `list servers` or `servers` - Show connected servers

## Example Workflows

**Time queries:**
- Ask: "What time is it in Tokyo?"
- System recommends: `time` server
- Connect: `connect time`
- Ask again: "What time is it in Tokyo?" (now uses the time server)

**File operations:**
- Ask: "List files in the current directory"
- System recommends: `filesystem` server
- Connect: `connect filesystem`
- Ask: "Read the README file"

Start by asking a question, and I'll recommend the best MCP servers to help you! 💬

