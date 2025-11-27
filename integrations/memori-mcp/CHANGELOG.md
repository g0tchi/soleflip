# Changelog - Memori MCP Integration

All notable changes to the Memori integration will be documented in this file.

## [1.0.0] - 2025-11-26

### 🎉 First Production Release - Official GibsonAI Memori Integration

Production-ready release of Memori integration using the official GibsonAI Memori library from GitHub.
Complete rebuild of both Memori servers (HTTP API + MCP) with enterprise-grade memory management.

#### Added
- **Official Memori SDK Integration** - Migrated from custom implementation to official library
- **Intelligent Content Analysis** - OpenAI-powered content transformation and metadata extraction
- **Dual-Server Architecture**:
  - HTTP API Server (Docker, Port 8090) for n8n and external integrations
  - MCP Server (Local) for Claude Code integration
- **Advanced Memory Processing**:
  - Automatic entity extraction
  - Keyword identification
  - Importance scoring (0.0-1.0)
  - Category classification
  - AI-generated summaries
- **Database Schema Migration** - New tables for enhanced memory management:
  - `long_term_memory` - Primary storage with AI-processed content
  - `short_term_memory` - Working memory for current context
  - `chat_history` - Complete conversation tracking
- **pgvector Extension** - Installed and ready for future semantic search features
- **Comprehensive Documentation**:
  - Architecture diagrams
  - API examples
  - Troubleshooting guides
  - Database schema documentation

#### Changed
- **PostgreSQL Image** - Switched from `postgres:17-alpine` to `pgvector/pgvector:pg17`
- **Memory Storage Location** - Moved from `memories` table to `long_term_memory` table
- **API Methods** - Updated to use official Memori SDK methods:
  - `add_memory()` → `add(text, metadata)`
  - `retrieve_context(query, limit)` - Dual-mode retrieval
  - `search(query, limit)` - Advanced search with ranking
- **Content Processing** - Memories now transformed and enriched by OpenAI before storage
- **Search Strategy** - Enhanced PostgreSQL full-text search with relevance ranking

#### Fixed
- **OpenAI API Key Loading** - Discovered and fixed Portainer environment variable caching issue
  - Root cause: Portainer stores env vars in its own database, not from docker-compose.yml
  - Solution: Update keys directly in Portainer UI when needed
- **Database Connection** - Proper SQLAlchemy connection string format (`postgresql+psycopg2://`)
- **Method Naming** - Corrected API method names to match official library
- **Cleanup Method** - Changed from `.close()` to `.cleanup()` per official API

#### Technical Details

**Before (Development/Internal)**:
```python
# Custom implementation (never released)
memory_system.store(content, category, labels)
```

**After (v1.0.0 - First Release)**:
```python
# Official Memori SDK
from memori import Memori

memori = Memori(
    database_connect="postgresql+psycopg2://...",
    openai_api_key="sk-proj-...",
    namespace="soleflip",
    conscious_ingest=True,
    auto_ingest=True
)
memori.enable()
memori.add(text="Important info", metadata={"category": "test"})
```

#### Known Limitations
- ❌ **Semantic Vector Search Not Available** - GitHub version doesn't support embeddings yet
  - Library uses PostgreSQL text search instead of vector similarity
  - pgvector extension installed and ready for future updates
  - Search works well for keyword and entity-based queries

#### Performance Improvements
- **Content Analysis** - LLM-powered processing provides better searchability
- **Search Relevance** - Composite scoring combines multiple relevance signals
- **Database Indexing** - Optimized indexes on searchable_content and summary fields

#### Breaking Changes
- Storage moved from `memories` to `long_term_memory` table
- API method signatures changed to match official library
- Metadata structure updated to support richer AI-processed data

#### Migration Notes
- Existing data in `memories` table is preserved but not actively used
- New memories stored in `long_term_memory` with enhanced metadata
- Both tables coexist for compatibility

#### Dependencies Updated
- Added: `git+https://github.com/GibsonAI/memori.git` (official library from GitHub)
- Added: `psycopg2-binary>=2.9.0` (required for PostgreSQL with Memori)
- Kept: `pgvector>=0.2.0`, `openai>=1.0.0`, `fastapi`, `mcp`

#### Configuration Changes
```bash
# Required environment variables
MEMORI_OPENAI_API_KEY=sk-proj-...  # OpenAI API key for content analysis
MEMORI_NAMESPACE=soleflip          # Memory namespace
MEMORI_CONSCIOUS_INGEST=true       # Enable working memory
MEMORI_AUTO_INGEST=true            # Enable dynamic search
```

#### Deployment
- Docker Compose service: `memori-mcp`
- HTTP API: http://localhost:8090
- Health check: http://localhost:8090/health
- Database: `memori` (PostgreSQL 17 + pgvector)

---

## [0.x] - Development (Before 2025-11-26)

### Internal Custom Implementation (Never Released)
- Basic memory storage in `memories` table
- Simple text-based retrieval
- No AI processing
- Manual metadata management
- Development/testing only - not production-ready

---

## Future Roadmap

### Planned Features (Waiting for Upstream)
- **Semantic Vector Search** - When Memori library adds embedding support
  - Vector embeddings in database schema
  - Similarity-based retrieval with pgvector
  - Hybrid search (vector + text)
- **Memory Consolidation** - Automatic deduplication and summarization
- **Advanced Analytics** - Memory usage patterns and insights
- **Real-time Embedding Generation** - As content is stored

### Under Consideration
- Multi-tenant enhanced isolation
- Memory lifecycle management (archival, retention policies)
- Integration with additional AI models
- Memory versioning and history

---

## Version Format
This project follows [Semantic Versioning](https://semver.org/):
- MAJOR version: Incompatible API changes
- MINOR version: Backward-compatible functionality additions
- PATCH version: Backward-compatible bug fixes

## Links
- [GibsonAI Memori GitHub](https://github.com/GibsonAI/memori)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [Model Context Protocol](https://modelcontextprotocol.io/)
