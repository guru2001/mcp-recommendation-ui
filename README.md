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

## Installation

### Prerequisites

- **Python 3.12 or higher**
- **uv** package manager ([install uv](https://github.com/astral-sh/uv))
- **OpenAI API Key** ([get one here](https://platform.openai.com/api-keys))
- **Node.js and npm** (for MCP servers that use `npx`)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd mcp-recommendation-ui
```

### Step 2: Install Dependencies

Using `uv` (recommended):

```bash
uv sync
```

This will install all Python dependencies specified in `pyproject.toml`.

### Step 3: Set Up Environment Variables

Create a `.env` file in the project root (or export the environment variable):

```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

Or create a `.env` file:

```bash
echo "OPENAI_API_KEY=your-openai-api-key-here" > .env
```

### Step 4: (Optional) Populate Vector Database

The application uses a vector database for semantic search of MCP servers. By default, it uses a local curated list. To populate the vector database with additional servers:

```bash
# The vector database will be automatically populated when you first run the application
# or you can manually populate it by running the application and using the search features
```

The vector database is stored in `./vector_db` and will be created automatically on first use.

## Running the Application

### Start the Chat Application

From the project root directory:

```bash
uv run chainlit run src/app.py
```

Or if you've activated the virtual environment:

```bash
chainlit run src/app.py
```

The application will start and you'll see output like:

```
Chainlit app is running at http://localhost:8000
```

Open your browser and navigate to the URL shown (typically `http://localhost:8000`).

### Running in Development Mode

For development with auto-reload:

```bash
uv run chainlit run src/app.py --watch
```
