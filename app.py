from typing import Any
import chainlit as cl
from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp, MCPServerStdio
import asyncio
import shlex
import httpx
import json
from datetime import datetime, timedelta

# --- In-memory MCP registry per Chainlit user session ---
mcp_registry = {}

# --- Cache for MCP server list ---
_mcp_servers_cache = None
_cache_timestamp = None
_cache_ttl = timedelta(hours=24)  # Cache for 24 hours

# --- Local curated list of popular MCP servers (fallback) ---
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
            "command": "mcp-filesystem-server ."
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
            "name": "postgres",
            "description": "Query and manage PostgreSQL databases.",
            "type": "stdio",
            "command": "uvx mcp-server-postgres"
        },
        {
            "name": "slack",
            "description": "Interact with Slack workspaces, channels, and messages.",
            "type": "stdio",
            "command": "uvx mcp-server-slack"
        }
    ]


async def fetch_mcp_servers_from_web() -> list[dict]:
    """Attempts to fetch MCP servers from various online sources."""
    servers = []
    
    # Try fetching from various sources
    sources = [
        # You can add API endpoints here if they become available
        # {"url": "https://api.mcplist.ai/servers", "parser": parse_mcplist_response},
        # {"url": "https://api.openmcpdirectory.com/servers", "parser": parse_openmcp_response},
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for source in sources:
            try:
                response = await client.get(source["url"])
                if response.status_code == 200:
                    parsed = source["parser"](response.json())
                    servers.extend(parsed)
            except Exception as e:
                # Silently fail and try next source
                continue
    
    return servers


async def discover_mcp_servers_from_npm() -> list[dict]:
    """Attempts to discover MCP servers from npm registry."""
    servers = []
    
    # Common npm package pattern for MCP servers
    npm_packages = [
        "mcp-server-fetch",
        "mcp-server-sqlite",
        "mcp-server-time",
        "mcp-server-github",
        "mcp-server-brave-search",
        "mcp-server-postgres",
        "mcp-server-slack",
        "mcp-server-filesystem",
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for package in npm_packages:
            try:
                # Try to get package info from npm registry
                url = f"https://registry.npmjs.org/{package}"
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    latest = data.get("dist-tags", {}).get("latest")
                    if latest:
                        version_data = data.get("versions", {}).get(latest, {})
                        description = version_data.get("description", "")
                        
                        servers.append({
                            "name": package.replace("mcp-server-", ""),
                            "description": description or f"MCP server: {package}",
                            "type": "stdio",
                            "command": f"uvx {package}"
                        })
            except Exception:
                continue
    
    return servers


async def get_mcp_servers(use_cache: bool = True, include_web: bool = False, include_npm: bool = True) -> list[dict]:
    """
    Get a comprehensive list of MCP servers.
    
    Args:
        use_cache: Whether to use cached results
        include_web: Whether to attempt fetching from web sources (slower)
        include_npm: Whether to attempt discovering from npm registry (slower)
    
    Returns:
        List of MCP server dictionaries
    """
    global _mcp_servers_cache, _cache_timestamp
    
    # Check cache
    if use_cache and _mcp_servers_cache and _cache_timestamp:
        if datetime.now() - _cache_timestamp < _cache_ttl:
            return _mcp_servers_cache
    
    # Start with local curated list
    servers = get_local_mcp_servers()
    
    # Optionally fetch from web sources
    if include_web:
        try:
            web_servers = await fetch_mcp_servers_from_web()
            servers.extend(web_servers)
        except Exception:
            pass
    
    # Try to discover from npm (only if requested)
    if include_npm:
        try:
            npm_servers = await discover_mcp_servers_from_npm()
            # Merge with existing, avoiding duplicates
            existing_names = {s["name"].lower() for s in servers}
            for server in npm_servers:
                if server["name"].lower() not in existing_names:
                    servers.append(server)
        except Exception:
            pass
    
    # Update cache
    _mcp_servers_cache = servers
    _cache_timestamp = datetime.now()
    
    return servers


# --- Backward compatibility ---
def get_mcp_servers_sync() -> list[dict]:
    """Synchronous version that returns cached or local servers."""
    if _mcp_servers_cache:
        return _mcp_servers_cache
    return get_local_mcp_servers()


# --- Intelligent recommender using agent ---
async def recommend_servers_intelligent(user_query: str) -> list[dict]:
    """Use an agent to intelligently recommend MCP servers based on user query."""
    # Skip npm discovery for recommendations - use local list + cache only
    servers = await get_mcp_servers(use_cache=True, include_web=False, include_npm=False)
    
    # Create a prompt for the agent to analyze the query
    server_list = "\n".join([
        f"- {s['name']}: {s['description']}" 
        for s in servers
    ])
    
    prompt = f"""Analyze the following user query and recommend the most relevant MCP servers that could help.

Available MCP servers:
{server_list}

User query: "{user_query}"

Based on the user's query, which MCP servers would be most helpful? 
Return ONLY a comma-separated list of server names (e.g., "fetch, filesystem").
If no servers are relevant, return "none".
Do not include explanations, just the server names."""
    
    # Use a lightweight agent for recommendations
    recommender_agent = Agent[Any](
        name="mcp_recommender",
        model="gpt-4o-mini"
    )
    
    try:
        result = await Runner.run(recommender_agent, prompt)
        recommendation_text = getattr(result, "final_output", None) or getattr(result, "output_text", str(result))
        
        # Parse the recommendation
        if "none" in recommendation_text.lower() or not recommendation_text.strip():
            return []
        
        # Extract server names
        recommended_names = [name.strip().lower() for name in recommendation_text.split(",")]
        recommended_servers = [
            s for s in servers 
            if s["name"].lower() in recommended_names
        ]
        
        return recommended_servers[:3]  # Limit to 3
    except Exception as e:
        # Fallback to simple keyword matching if agent fails
        query_lower = user_query.lower()
        return [s for s in servers if query_lower in s["description"].lower() or query_lower in s["name"].lower()][:3]


# --- Connect to MCP server ---
async def connect_mcp_server(session_id: str, server_name: str):
    # Skip npm discovery when connecting - use local list + cache only
    servers = await get_mcp_servers(use_cache=True, include_web=False, include_npm=False)
    target = next((s for s in servers if s["name"] == server_name), None)
    if not target:
        return f"❌ Server '{server_name}' not found."

    try:
        if target["type"] == "http":
            # (HTTP servers still use StreamableHttp)
            server = MCPServerStreamableHttp(name=target["name"], url=target["url"])
            await server.connect()
            mcp_registry.setdefault(session_id, []).append(server)

        else:
            # ✅ new style: pass command/args via params
            cmd_parts = target["command"].split()
            server = MCPServerStdio(
                name=target["name"],
                params={
                    "command": cmd_parts[0],
                    "args": cmd_parts[1:]
                },
            )
            await server.connect()
            mcp_registry.setdefault(session_id, []).append(server)

        # For simplicity, just list tools to verify the connection
        tools = await server.list_tools()
        tool_names = [t.name for t in tools]
        return f"✅ Connected to `{server_name}` MCP.\nTools available: {', '.join(tool_names)}"

    except Exception as e:
        return f"⚠️ Failed to connect to `{server_name}` MCP: {e}"


# --- Main Chat handler ---
@cl.on_message
async def on_message(message: cl.Message):
    session_id = cl.user_session.get("id")
    user_text = message.content.strip().lower()

    if session_id not in mcp_registry:
        mcp_registry[session_id] = []

    # Connect
    if user_text.startswith("connect "):
        server_name = user_text.split(" ", 1)[1].strip()
        msg = await connect_mcp_server(session_id, server_name)
        await cl.Message(content=msg).send()
        return

    # Normal chat - with intelligent MCP server recommendations
    agent = cl.user_session.get("agent")
    if not agent:
        agent = Agent[Any](
            name="mcp_chat_agent",
            model="gpt-4o-mini",
            mcp_servers=mcp_registry.get(session_id, [])
        )
        cl.user_session.set("agent", agent)

    # Check if we should recommend MCP servers based on the query
    # Only recommend if user doesn't already have servers connected
    if not mcp_registry.get(session_id):
        recommended_servers = await recommend_servers_intelligent(message.content)
        
        if recommended_servers:
            server_names = [s["name"] for s in recommended_servers]
            server_descriptions = "\n".join([
                f"• **{s['name']}**: {s['description']}" 
                for s in recommended_servers
            ])
            
            recommendation_msg = f"""💡 I think these MCP servers could help with your query:

{server_descriptions}

Type `connect <server_name>` to connect one of them (e.g., `connect {server_names[0]}`)."""
            
            await cl.Message(content=recommendation_msg).send()
            return

    msg = cl.Message(content="⏳ Thinking...")
    await msg.send()

    # Small delay to make the UI feel natural
    await asyncio.sleep(0.5)

    # Replace "thinking" with an empty message for streaming
    msg.content = ""
    await msg.update()

    result = await Runner.run(agent, message.content)

    # Extract final text (depending on SDK version)
    reply = getattr(result, "final_output", None) or getattr(result, "output_text", str(result))

    # --- Stream tokens manually to simulate live typing ---
    for token in reply.split():
        await msg.stream_token(token + " ")
        await asyncio.sleep(0.02)  # small delay for effect

    # Mark the message as complete
    await msg.update()
