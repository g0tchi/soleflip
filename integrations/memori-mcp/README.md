# Memori MCP Server Integration

Memori is an open-source memory engine for LLMs, AI Agents, and Multi-Agent Systems. This integration provides memory capabilities via the Model Context Protocol (MCP) for n8n workflows and Claude Code.

## Features

- **Persistent Memory**: Store and retrieve information across agent interactions
- **Semantic Search**: Find relevant memories using natural language queries
- **Context Injection**: Automatically provide relevant context to AI agents
- **Multi-Namespace**: Organize memories by project, user, or domain
- **MCP Compatible**: Works with any MCP-aware tool (n8n, Claude Code, etc.)

## Quick Start

### For Portainer Users (Recommended)

See detailed guide: **[docs/integrations/portainer-memori-deployment.md](../../docs/integrations/portainer-memori-deployment.md)**

**Quick Steps:**
1. Open Portainer → Stacks → Your Soleflip Stack
2. Add Environment Variable: `COMPOSE_PROFILES=memori`
3. Update Stack
4. Done! Memori is running

### For Docker Compose CLI

```bash
# Start with Memori enabled
docker-compose --profile memori up -d

# Or add to existing stack
docker-compose --profile memori up -d memori-mcp
```

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# Optional: Memori Configuration
MEMORI_NAMESPACE=soleflip
MEMORI_OPENAI_API_KEY=sk-your-openai-key-here  # Optional: for embeddings
MEMORI_LOGGING_LEVEL=INFO
```

### 3. Verify Service is Running

```bash
# Check logs
docker-compose logs -f memori-mcp

# Check health
docker-compose ps memori-mcp
```

## Available MCP Tools

### 1. `store_memory`
Store information in memory for later retrieval.

**Parameters:**
- `content` (string, required): Content to store
- `namespace` (string, optional): Organization namespace
- `metadata` (object, optional): Additional tags/metadata

**Example:**
```json
{
  "content": "Customer John prefers email communication over phone",
  "namespace": "customer_preferences",
  "metadata": {"customer_id": "123", "priority": "high"}
}
```

### 2. `search_memory`
Search stored memories using semantic similarity.

**Parameters:**
- `query` (string, required): Search query
- `namespace` (string, optional): Namespace to search in
- `limit` (number, optional): Max results (default: 5)

**Example:**
```json
{
  "query": "What are John's communication preferences?",
  "namespace": "customer_preferences",
  "limit": 3
}
```

### 3. `get_context`
Get relevant context for a conversation or query.

**Parameters:**
- `query` (string, required): Query or conversation text
- `namespace` (string, optional): Namespace
- `max_memories` (number, optional): Max memories to include (default: 3)

**Example:**
```json
{
  "query": "I need to contact customer John",
  "namespace": "customer_preferences",
  "max_memories": 3
}
```

### 4. `list_namespaces`
List all available memory namespaces.

**Example:**
```json
{}
```

## Integration Examples

### n8n Workflow Integration

1. **Add MCP Server Connection** in n8n:
   - Go to Settings → Credentials
   - Add new "MCP Server" credential
   - Server URL: `http://memori-mcp:8080` (internal Docker network)

2. **Use in Workflow**:
   - Add "MCP Tool" node
   - Select tool: `store_memory`
   - Configure parameters
   - Connect to your AI Agent node

### Claude Code Integration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "memori": {
      "command": "docker",
      "args": ["exec", "-i", "soleflip-memori-mcp", "python", "server.py"]
    }
  }
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMORI_DATABASE_URL` | `postgresql://...` | PostgreSQL connection URL |
| `MEMORI_NAMESPACE` | `soleflip` | Default namespace for memories |
| `MEMORI_CONSCIOUS_INGEST` | `true` | Enable AI-powered ingestion |
| `MEMORI_AUTO_INGEST` | `true` | Auto-ingest conversations |
| `MEMORI_OPENAI_API_KEY` | - | OpenAI API key (optional) |
| `MEMORI_LOGGING_LEVEL` | `INFO` | Logging level |
| `MEMORI_VERBOSE` | `false` | Enable verbose logging |
| `MEMORI_MAX_MEMORIES_PER_QUERY` | `5` | Max search results |
| `MEMORI_CONTEXT_LIMIT` | `3` | Max memories in context |

### Database

Memori uses a dedicated PostgreSQL database (`memori`) in the shared PostgreSQL instance. The database is automatically created on first start.

**Connection Details:**
- Host: `postgres` (Docker network) or `localhost:5432` (external)
- Database: `memori`
- User: `soleflip`
- Password: Same as `POSTGRES_PASSWORD`

## Use Cases

### 1. Customer Support Memory
Store customer preferences, past issues, and solutions for context-aware support.

### 2. Multi-Agent Coordination
Share knowledge between different AI agents working on the same project.

### 3. Long-Term Project Context
Maintain project history, decisions, and context across multiple sessions.

### 4. Personalized AI Assistants
Build AI assistants that remember user preferences and past interactions.

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs memori-mcp

# Verify database connection
docker-compose exec postgres psql -U soleflip -d memori -c '\dt'
```

### Memory Not Persisting

1. Check database connection in logs
2. Verify `MEMORI_DATABASE_URL` is correct
3. Ensure PostgreSQL `memori` database exists

### Performance Issues

1. Reduce `MEMORI_MAX_MEMORIES_PER_QUERY`
2. Set `MEMORI_CONSCIOUS_INGEST=false` for faster ingestion
3. Increase resource limits in `docker-compose.yml`

## Development

### Local Development

```bash
# Navigate to integration directory
cd integrations/memori-mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run locally
export MEMORI_DATABASE_URL="postgresql://soleflip:password@localhost:5432/memori"
python server.py
```

### Testing

```bash
# Test MCP server
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python server.py
```

## Resources

- [Memori GitHub](https://github.com/GibsonAI/memori)
- [Memori Documentation](https://docs.memori.ai)
- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [n8n MCP Integration](https://docs.n8n.io/integrations/mcp/)

## Architecture

```
┌─────────────────┐
│   n8n Workflow  │
│  Claude Code    │
└────────┬────────┘
         │ MCP Protocol
         │
┌────────▼────────┐
│  Memori MCP     │
│     Server      │
└────────┬────────┘
         │
┌────────▼────────┐
│   PostgreSQL    │
│  (memori DB)    │
└─────────────────┘
```

## License

This integration follows the Soleflip project license. Memori itself is licensed under Apache 2.0.

## Support

For issues specific to this integration, open an issue in the Soleflip repository.
For Memori-specific questions, visit [GibsonAI/memori](https://github.com/GibsonAI/memori).
