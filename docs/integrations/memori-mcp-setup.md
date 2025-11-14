# Memori MCP Server Setup Guide

This guide provides detailed instructions for setting up and using the Memori MCP Server integration in your Soleflip stack.

## What is Memori?

Memori is an open-source memory engine that provides human-like memory capabilities for LLMs, AI Agents, and Multi-Agent Systems. It uses:

- **Dual-Mode Retrieval**: Short-term and long-term memory with automatic transitions
- **Semantic Search**: Natural language queries to find relevant memories
- **Automatic Context Injection**: Seamlessly provide context to AI conversations
- **Namespace Isolation**: Organize memories by project, user, or domain

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                    Soleflip Stack                         │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────┐    ┌──────────────┐   ┌─────────────┐ │
│  │   n8n       │    │ Claude Code  │   │  Soleflip   │ │
│  │ Workflows   │    │   (MCP)      │   │    API      │ │
│  └──────┬──────┘    └──────┬───────┘   └─────────────┘ │
│         │                  │                             │
│         │    MCP Protocol  │                             │
│         └──────────┬───────┘                             │
│                    │                                     │
│         ┌──────────▼──────────┐                          │
│         │   Memori MCP Server │                          │
│         │   (Port: Internal)  │                          │
│         └──────────┬──────────┘                          │
│                    │                                     │
│         ┌──────────▼──────────┐                          │
│         │   PostgreSQL        │                          │
│         │   Database: memori  │                          │
│         └─────────────────────┘                          │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Docker and Docker Compose installed
- Soleflip stack running (`docker-compose up -d`)
- PostgreSQL database accessible
- (Optional) OpenAI API key for embeddings

### Step 1: Enable Memori Service

The Memori service is configured as an **optional profile** in `docker-compose.yml`. This means it won't start by default.

**Option A: Start with Memori enabled**
```bash
docker-compose --profile memori up -d
```

**Option B: Add to existing stack**
```bash
docker-compose --profile memori up -d memori-mcp
```

**Option C: Always enable (modify docker-compose)**
Remove the `profiles:` section from the `memori-mcp` service in `docker-compose.yml`.

### Step 2: Configure Environment Variables

Create or update your `.env` file:

```bash
# ==============================================
# Memori MCP Server Configuration (OPTIONAL)
# ==============================================

# Namespace for memory organization
MEMORI_NAMESPACE=soleflip

# AI-powered memory ingestion (requires OpenAI API key)
MEMORI_CONSCIOUS_INGEST=true
MEMORI_AUTO_INGEST=true

# Optional: OpenAI API Key for embeddings and conscious ingestion
# If not provided, falls back to simpler ingestion methods
MEMORI_OPENAI_API_KEY=sk-your-openai-key-here

# Logging
MEMORI_LOGGING_LEVEL=INFO
MEMORI_VERBOSE=false

# Performance tuning
MEMORI_MAX_MEMORIES_PER_QUERY=5
MEMORI_CONTEXT_LIMIT=3
```

### Step 3: Verify Installation

```bash
# Check if service is running
docker-compose ps memori-mcp

# View logs
docker-compose logs -f memori-mcp

# Check database
docker-compose exec postgres psql -U soleflip -d memori -c '\dt'
```

Expected output:
```
NAME                 IMAGE                         STATUS
soleflip-memori-mcp  soleflip-memori-mcp:latest   Up (healthy)
```

## Integration with n8n

### Step 1: Configure MCP Connection

1. Open n8n: `http://localhost:5678`
2. Go to **Settings** → **Credentials**
3. Click **Add Credential** → Search for "MCP"
4. Configure:
   - **Name**: `Memori Memory Engine`
   - **Server Type**: `HTTP`
   - **URL**: `http://memori-mcp:8080` (Docker internal)
   - Or `http://localhost:8080` (if exposed)

### Step 2: Create Memory-Enabled Workflow

Example workflow: **Customer Support with Memory**

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Webhook    │─────▶│  Search      │─────▶│   AI Agent   │
│   Trigger    │      │  Memory      │      │   Response   │
└──────────────┘      └──────────────┘      └───────┬──────┘
                                                     │
                                              ┌──────▼──────┐
                                              │    Store    │
                                              │   Memory    │
                                              └─────────────┘
```

**Workflow Configuration:**

1. **Webhook Node**: Receives customer inquiry
2. **MCP Tool Node** (`search_memory`):
   ```json
   {
     "tool": "search_memory",
     "parameters": {
       "query": "{{ $json.message }}",
       "namespace": "customer_support",
       "limit": 3
     }
   }
   ```
3. **AI Agent Node**: Process with context from memories
4. **MCP Tool Node** (`store_memory`):
   ```json
   {
     "tool": "store_memory",
     "parameters": {
       "content": "Customer: {{ $json.message }}\nResponse: {{ $json.ai_response }}",
       "namespace": "customer_support",
       "metadata": {
         "customer_id": "{{ $json.customer_id }}",
         "timestamp": "{{ $now }}"
       }
     }
   }
   ```

## Integration with Claude Code

### Configuration

Add to your Claude Code MCP configuration file:

**For Docker:**
```json
{
  "mcpServers": {
    "memori": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "soleflip-memori-mcp",
        "python",
        "server.py"
      ],
      "env": {}
    }
  }
}
```

**For Direct Connection (if exposed):**
```json
{
  "mcpServers": {
    "memori": {
      "command": "python",
      "args": [
        "/path/to/soleflip/integrations/memori-mcp/server.py"
      ],
      "env": {
        "MEMORI_DATABASE_URL": "postgresql://soleflip:password@localhost:5432/memori"
      }
    }
  }
}
```

### Usage in Claude Code

Once configured, Claude Code will have access to Memori tools:

```
User: Remember that we decided to use FastAPI for the API layer

Claude: [Uses store_memory tool]
Stored: "Project architecture decision: Using FastAPI for API layer"

---

User: What framework are we using for the API?

Claude: [Uses search_memory tool]
Retrieved: "Project architecture decision: Using FastAPI for API layer"
Response: "We're using FastAPI for the API layer."
```

## Use Cases

### 1. Multi-Session Project Context

**Problem**: AI agents lose context between sessions.

**Solution**: Store project decisions, architecture notes, and context.

```python
# Store project decision
{
  "tool": "store_memory",
  "parameters": {
    "content": "We decided to use PostgreSQL instead of MongoDB because of complex relational queries",
    "namespace": "soleflip_architecture",
    "metadata": {"type": "decision", "component": "database"}
  }
}

# Later session - retrieve context
{
  "tool": "get_context",
  "parameters": {
    "query": "Why did we choose PostgreSQL?",
    "namespace": "soleflip_architecture"
  }
}
```

### 2. Customer Interaction History

**Problem**: Customer support lacks context from previous interactions.

**Solution**: Store and retrieve customer communication history.

```python
# Store customer preference
{
  "tool": "store_memory",
  "parameters": {
    "content": "Customer John (ID: 12345) prefers evening deliveries and email notifications",
    "namespace": "customers",
    "metadata": {"customer_id": "12345", "type": "preference"}
  }
}

# Retrieve when customer contacts support
{
  "tool": "search_memory",
  "parameters": {
    "query": "customer 12345 delivery preferences",
    "namespace": "customers"
  }
}
```

### 3. Multi-Agent Coordination

**Problem**: Multiple AI agents working on same task don't share knowledge.

**Solution**: Shared memory namespace for agent coordination.

```python
# Agent 1: Research Agent stores findings
{
  "tool": "store_memory",
  "parameters": {
    "content": "Market research shows 60% preference for sustainable materials",
    "namespace": "product_development",
    "metadata": {"agent": "research", "phase": "discovery"}
  }
}

# Agent 2: Design Agent retrieves research
{
  "tool": "get_context",
  "parameters": {
    "query": "sustainable materials market research",
    "namespace": "product_development"
  }
}
```

### 4. Workflow State Management

**Problem**: Complex n8n workflows need to maintain state across runs.

**Solution**: Store workflow state and intermediate results.

```python
# Store intermediate processing results
{
  "tool": "store_memory",
  "parameters": {
    "content": "Processed 1000 inventory items. Next batch starts at ID: 1001",
    "namespace": "inventory_import",
    "metadata": {"workflow": "daily_sync", "batch": 1}
  }
}

# Resume workflow from last state
{
  "tool": "search_memory",
  "parameters": {
    "query": "inventory import last batch",
    "namespace": "inventory_import",
    "limit": 1
  }
}
```

## Advanced Configuration

### Custom Memory Retention

Modify `integrations/memori-mcp/config.py` to add custom retention policies:

```python
class MemoriMCPSettings(BaseSettings):
    # Add custom retention
    retention_days: int = Field(default=90, description="Days to retain memories")
    importance_threshold: float = Field(default=0.5, description="Min importance score")
```

### Performance Tuning

For high-throughput scenarios:

```yaml
# docker-compose.yml - Increase resources
memori-mcp:
  deploy:
    resources:
      limits:
        memory: 1G
        cpus: '1.0'
  environment:
    MEMORI_MAX_MEMORIES_PER_QUERY: 10
    MEMORI_CONTEXT_LIMIT: 5
```

### Multiple Namespaces

Organize memories by domain:

```bash
# Separate namespaces for different concerns
MEMORI_NAMESPACE=default                    # General memories
# Then in n8n workflows, use namespace parameter:
# - "customer_support"
# - "product_development"
# - "internal_operations"
```

## Monitoring & Maintenance

### Health Checks

```bash
# Check service health
docker-compose ps memori-mcp

# View metrics in logs
docker-compose logs memori-mcp | grep -E "(memory_stored|memory_search)"
```

### Database Maintenance

```bash
# Check database size
docker-compose exec postgres psql -U soleflip -d memori -c \
  "SELECT pg_size_pretty(pg_database_size('memori'));"

# View memory count
docker-compose exec postgres psql -U soleflip -d memori -c \
  "SELECT COUNT(*) FROM memories;"
```

### Backup Memories

```bash
# Backup memori database
docker-compose exec postgres pg_dump -U soleflip memori > memori_backup_$(date +%Y%m%d).sql

# Restore
docker-compose exec -T postgres psql -U soleflip memori < memori_backup_20250113.sql
```

## Troubleshooting

### Service Won't Start

**Symptom**: `memori-mcp` container exits immediately

**Solutions**:
```bash
# 1. Check logs for errors
docker-compose logs memori-mcp

# 2. Verify Python dependencies
docker-compose exec memori-mcp pip list

# 3. Test database connection
docker-compose exec memori-mcp python -c "import asyncpg; print('OK')"

# 4. Rebuild container
docker-compose build --no-cache memori-mcp
docker-compose up -d memori-mcp
```

### Memory Not Persisting

**Symptom**: Stored memories don't appear in searches

**Solutions**:
```bash
# 1. Check database connection
docker-compose exec postgres psql -U soleflip -d memori -c '\dt'

# 2. Verify writes are succeeding (check logs)
docker-compose logs memori-mcp | grep "memory_stored"

# 3. Check namespace configuration
# Ensure search and store use same namespace
```

### Performance Issues

**Symptom**: Slow memory searches or context retrieval

**Solutions**:
1. Reduce `MEMORI_MAX_MEMORIES_PER_QUERY` to 3
2. Set `MEMORI_CONSCIOUS_INGEST=false` for faster ingestion
3. Add database indexes (if using heavily)
4. Increase container resources

### OpenAI API Errors

**Symptom**: Errors related to embeddings or ingestion

**Solutions**:
```bash
# Option 1: Provide valid API key
export MEMORI_OPENAI_API_KEY=sk-your-key

# Option 2: Disable conscious ingestion
export MEMORI_CONSCIOUS_INGEST=false
export MEMORI_AUTO_INGEST=false
```

## Security Considerations

### API Key Protection

```bash
# Never commit API keys to Git
# Use .env file (already in .gitignore)
echo "MEMORI_OPENAI_API_KEY=sk-xxx" >> .env

# Or use Docker secrets (production)
echo "sk-xxx" | docker secret create memori_openai_key -
```

### Network Isolation

The Memori service runs on the internal Docker network and is not exposed externally by default.

For production deployments:
- Keep Memori on internal network only
- Use reverse proxy with authentication if external access needed
- Enable PostgreSQL SSL for database connections

### Data Privacy

Memories may contain sensitive information:
- Use namespace isolation for different security levels
- Implement retention policies for PII data
- Consider encrypting sensitive memory content

## Roadmap

Future enhancements planned:
- [ ] REST API endpoint for non-MCP clients
- [ ] Memory importance scoring and auto-cleanup
- [ ] Vector embeddings for improved semantic search
- [ ] Memory visualization dashboard
- [ ] Integration with Metabase for memory analytics

## Resources

- [Memori Official Documentation](https://github.com/GibsonAI/memori)
- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [n8n MCP Integration Guide](https://docs.n8n.io/integrations/mcp/)
- [FastAPI Documentation](https://fastapi.tiangolo.com)

## Support

For issues or questions:
1. Check this documentation
2. Review Memori logs: `docker-compose logs memori-mcp`
3. Consult [Memori GitHub Issues](https://github.com/GibsonAI/memori/issues)
4. Open issue in Soleflip repository with `[Memori]` tag
