# Memori MCP Integration - GibsonAI Memory System

Production-ready AI memory system for SoleFlip, powered by the official [GibsonAI Memori](https://github.com/GibsonAI/memori) library.

## 🎯 Overview

This integration provides **two complementary memory interfaces**:

1. **MCP Server** (Local) - For Claude Code via Model Context Protocol
2. **HTTP API Server** (Docker) - For n8n workflows and external integrations

Both servers use the same PostgreSQL database and share memory across all services.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   SoleFlip System                        │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────┐         ┌──────────────────┐      │
│  │  Claude Code    │◄────────┤  MCP Server      │      │
│  │  (Local)        │  MCP    │  (Local Process) │      │
│  └─────────────────┘         └──────────────────┘      │
│                                       │                  │
│                                       │                  │
│                                       ▼                  │
│                          ┌─────────────────────────┐    │
│  ┌─────────────────┐    │   PostgreSQL 17         │    │
│  │  n8n Workflows  │───▶│   + pgvector            │    │
│  │  (Docker)       │    │   (memori database)     │    │
│  └─────────────────┘    └─────────────────────────┘    │
│           │                         ▲                   │
│           │                         │                   │
│           ▼                         │                   │
│  ┌─────────────────┐                │                   │
│  │  HTTP API       │────────────────┘                   │
│  │  (Docker:8090)  │    PostgreSQL Connection          │
│  └─────────────────┘                                    │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## ✨ Features

### Core Capabilities
- ✅ **Intelligent Content Analysis** - Uses OpenAI to analyze, categorize, and transform memories
- ✅ **Dual-Mode Retrieval** - Conscious Ingest (working memory) + Auto Ingest (dynamic search)
- ✅ **PostgreSQL Full-Text Search** - Keyword and entity-based search
- ✅ **Persistent Storage** - All memories stored in PostgreSQL
- ✅ **Namespace Isolation** - Multi-tenant support via namespaces
- ✅ **MCP Protocol Support** - Native Claude Code integration
- ✅ **REST API** - HTTP endpoints for external integrations

### Current Limitations
- ❌ **No Semantic Vector Search** - GitHub version doesn't support embeddings yet
  - Library uses PostgreSQL text search instead of vector similarity
  - pgvector extension is installed and ready for future updates
  - For most use cases, text search is sufficient

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- PostgreSQL 17 with pgvector (automatically configured)
- OpenAI API Key

### Installation

1. **Environment Configuration**

Already configured in root `.env`:
\`\`\`bash
# OpenAI API Key (required for content analysis)
MEMORI_OPENAI_API_KEY=sk-proj-...

# Memori Configuration
MEMORI_NAMESPACE=soleflip
MEMORI_CONSCIOUS_INGEST=true
MEMORI_AUTO_INGEST=true
\`\`\`

2. **Start Services**

\`\`\`bash
# Start PostgreSQL with pgvector
docker compose up -d postgres

# Start Memori HTTP API
docker compose up -d memori-mcp
\`\`\`

3. **Verify Installation**

\`\`\`bash
curl http://localhost:8090/health
\`\`\`

## 📖 Usage

### HTTP API Examples

\`\`\`bash
# Store memory
curl -X POST http://localhost:8090/api/memory/store \\
  -H "Content-Type: application/json" \\
  -d '{"content": "Important project info", "metadata": {"category": "test"}}'

# Search memories
curl -X POST http://localhost:8090/api/memory/search \\
  -H "Content-Type: application/json" \\
  -d '{"query": "project", "limit": 5}'
\`\`\`

## 🔧 Troubleshooting

### OpenAI API Key Issues
If using Portainer, update key in Portainer UI (not just .env file):
- Containers → soleflip-memori-api → Duplicate/Edit → Environment Variables
- Change MEMORI_OPENAI_API_KEY value
- Deploy container

### Database Checks
\`\`\`bash
# Check memory count
docker exec soleflip-postgres psql -U soleflip -d memori -c "SELECT COUNT(*) FROM long_term_memory;"

# View recent memories
docker exec soleflip-postgres psql -U soleflip -d memori -c "SELECT processed_data->>'content', created_at FROM long_term_memory ORDER BY created_at DESC LIMIT 5;"
\`\`\`

## 📊 Database Schema

Memories are stored in **4 tables**:
- `long_term_memory` - Primary storage with AI-processed content
- `short_term_memory` - Working memory for current context
- `chat_history` - Full conversation tracking
- `memories` - Legacy table (not used by GitHub version)

## 🔮 Future Enhancements

When Memori library adds embedding support:
- Semantic vector search with pgvector
- Similarity-based retrieval
- Hybrid search (text + vector)

**Note**: pgvector extension is already installed and ready for future updates!

---

**Version**: 1.0.0 (First Production Release)
**Backend**: GibsonAI Memori (GitHub main)
**Status**: Production Ready ✅
