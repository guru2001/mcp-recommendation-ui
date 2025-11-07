"""Local curated list of popular MCP servers that can be run locally."""


def get_local_mcp_servers():
    """Returns a curated list of popular MCP servers that can be run locally."""
    return [
        {
            "name": "fetch",
            "description": "Fetch webpages and return Markdown, HTML, or plain text.",
            "type": "stdio",
            "command": "uvx mcp-server-fetch"
        },
        {
            "name": "sqlite",
            "description": "Query and manage SQLite databases.",
            "type": "stdio",
            "command": "uvx mcp-server-sqlite --db-path ./db.sqlite"
        },
        {
            "name": "time",
            "description": "Get current time and convert time zones.",
            "type": "stdio",
            "command": "uvx mcp-server-time"
        },
        {
            "name": "filesystem",
            "description": "Browse and edit local files (limited to project directory).",
            "type": "stdio",
            "command": "npx --yes @modelcontextprotocol/server-filesystem ."
        },
        {
            "name": "github",
            "description": "Interact with GitHub repositories, issues, and pull requests.",
            "type": "stdio",
            "command": "uvx mcp-server-github"
        },
        {
            "name": "brave-search",
            "description": "Search the web using Brave Search API.",
            "type": "stdio",
            "command": "uvx mcp-server-brave-search"
        },
        {
            "name": "slack",
            "description": "Interact with Slack workspaces, channels, and messages.",
            "type": "stdio",
            "command": "uvx mcp-server-slack"
        },
        {
            "name": "chargebee",
            "description": "Interact with Chargebee billing and subscription management platform.",
            "type": "stdio",
            "command": "npx -y @chargebee/mcp@latest"
        },
        {
            "name": "puppeteer",
            "description": "Control a headless browser to interact with web pages, take screenshots, and scrape content.",
            "type": "stdio",
            "command": "npx --yes @modelcontextprotocol/server-puppeteer"
        },
        {
            "name": "memory",
            "description": "Store and retrieve information across conversations using vector search.",
            "type": "stdio",
            "command": "npx --yes @modelcontextprotocol/server-memory"
        },
        {
            "name": "dollhousemcpofficial",
            "description": "MCP server: DollhouseMCPofficial",
            "type": "stdio",
            "command": "npx --yes @dollhousemcp/mcp-server"
        },
        {
            "name": "postgresql mcp",
            "description": "MCP server: PostgreSQL MCP",
            "type": "stdio",
            "command": "npx --yes mcp-server-postgresql"
        }
    ]

