# MindsDB Knowledge Base Setup via MCP (v3.0)

Complete guide for creating MindsDB Knowledge Bases using the MCP server.

## 🎯 Overview

This setup creates **5 domain-based Knowledge Bases** for the SoleFlipper project:

1. **kb_database_schema** - Database schema, migrations
2. **kb_integrations** - StockX, Metabase, Awin integrations
3. **kb_architecture_design** - System architecture, design patterns
4. **kb_code_quality_dev** - Development standards, testing, API docs
5. **kb_operations_history** - Notion integration, historical docs

## 📋 Prerequisites

- ✅ MCP MindsDB server configured in Claude Code
- ✅ PostgreSQL running (localhost:5432)
- ✅ Python 3.11+ with asyncpg installed
- ✅ OPENAI_API_KEY set (in MindsDB or environment)

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
pip install asyncpg python-dotenv
```

### Step 2: Populate PostgreSQL

```bash
python scripts/create_mindsdb_kbs_via_mcp.py
```

This script:
- Creates `context_documents` table in PostgreSQL
- Scans `context/` folder for markdown files
- Filters files based on KB definitions
- Inserts documents with metadata

**Expected Output:**
```
✅ Total documents inserted: ~70
📊 Documents per Knowledge Base:
   - kb_database_schema: 15 documents
   - kb_integrations: 12 documents
   - kb_architecture_design: 12 documents
   - kb_code_quality_dev: 14 documents
   - kb_operations_history: 18 documents
```

### Step 3: Generate SQL Commands

```bash
python scripts/create_kbs_mcp_automated.py
```

This creates: `scripts/mindsdb_kb_creation.sql`

### Step 4: Execute via MCP

In Claude Code, use the MCP tool to execute SQL:

#### 4a. Connect MindsDB to PostgreSQL

```sql
CREATE DATABASE soleflip_pg
WITH ENGINE = 'postgres',
PARAMETERS = {
    "host": "localhost",
    "port": 5432,
    "database": "soleflip",
    "user": "soleflip",
    "password": "SoleFlip2025SecureDB!"
};
```

Verify:
```sql
SELECT * FROM soleflip_pg.context_documents LIMIT 5;
```

#### 4b. Create Knowledge Bases (one at a time)

```sql
CREATE KNOWLEDGE_BASE soleflipper.kb_database_schema
FROM (
    SELECT id, file_path, file_name, content, category,
           file_size_kb, last_modified, version
    FROM soleflip_pg.context_documents
    WHERE kb_name = 'kb_database_schema'
)
USING
    embedding_model = {
        "provider": "openai",
        "model_name": "text-embedding-3-small",
    },
    reranking_model = {
        "provider": "openai",
        "model_name": "gpt-4o",
    },
    metadata_columns = ['file_path', 'category', 'file_size_kb', 'last_modified', 'version'],
    content_columns = ['content'],
    id_column = 'id';
```

Repeat for all 5 KBs (see generated SQL file).

#### 4c. Test Knowledge Bases

```sql
SELECT * FROM soleflipper.kb_database_schema
WHERE question = 'How is the database structured?'
LIMIT 3;
```

## 📊 Architecture

```
┌─────────────────────────────────────────┐
│  context/ folder (71 .md files)         │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Python Script (collect & filter)       │
│  - create_mindsdb_kbs_via_mcp.py       │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  PostgreSQL: context_documents table    │
│  - kb_name, file_path, content, etc.   │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  MindsDB (via MCP)                      │
│  - CREATE DATABASE soleflip_pg         │
│  - CREATE KNOWLEDGE_BASE ...           │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  5 Knowledge Bases ready for queries!   │
│  - OpenAI embeddings                    │
│  - GPT-4o reranking                     │
└─────────────────────────────────────────┘
```

## 🔄 Updating Knowledge Bases

When documentation changes:

### Option 1: Manual Update
```bash
# Re-run Step 2 to update PostgreSQL
python scripts/create_mindsdb_kbs_via_mcp.py

# Knowledge Bases automatically reflect new data
```

### Option 2: Recreate KB
```sql
-- Drop old KB
DROP KNOWLEDGE_BASE soleflipper.kb_database_schema;

-- Recreate from updated data
CREATE KNOWLEDGE_BASE soleflipper.kb_database_schema FROM ...;
```

## 🤖 Future: n8n Automation (Coming Soon)

Planned workflow for automatic updates:

```
GitHub Webhook (docs changed)
    ↓
n8n Workflow triggers
    ↓
1. Detect changed .md files
2. Update PostgreSQL table
3. Trigger MindsDB KB refresh
4. Send Slack notification
```

This keeps KBs always in sync with latest docs!

## 📝 Example Queries

### Database Schema
```sql
SELECT file_path, content
FROM soleflipper.kb_database_schema
WHERE question = 'What migrations were performed for multi-platform orders?'
LIMIT 5;
```

### Integrations
```sql
SELECT category, file_path, content
FROM soleflipper.kb_integrations
WHERE question = 'How do I authenticate with StockX API?'
AND category = 'integrations'
LIMIT 3;
```

### Architecture
```sql
SELECT file_path, content
FROM soleflipper.kb_architecture_design
WHERE question = 'Explain the pricing engine architecture'
LIMIT 3;
```

### Code Quality
```sql
SELECT content
FROM soleflipper.kb_code_quality_dev
WHERE question = 'What are the linting standards and make commands?'
LIMIT 5;
```

### Operations
```sql
SELECT file_path, last_modified, content
FROM soleflipper.kb_operations_history
WHERE question = 'How does Notion sync work?'
ORDER BY last_modified DESC
LIMIT 3;
```

## 🛠️ Troubleshooting

### Issue: "Database not found"
```sql
-- Check if PostgreSQL connection exists
SHOW DATABASES;

-- Should see 'soleflip_pg' in list
```

### Issue: "No documents in KB"
```bash
# Check PostgreSQL data
psql -U soleflip -d soleflip -c "SELECT kb_name, COUNT(*) FROM context_documents GROUP BY kb_name;"
```

### Issue: "OpenAI API error"
```bash
# Set API key in environment
export OPENAI_API_KEY="sk-..."

# Or pass explicitly in CREATE KNOWLEDGE_BASE
```

### Issue: "Query too slow"
- Reduce `LIMIT` in queries
- Check metadata filters (speed up queries)
- Consider splitting large KBs

## 📚 Related Files

- `create_mindsdb_kbs_via_mcp.py` - Main setup script
- `create_kbs_mcp_automated.py` - SQL generator
- `mindsdb_kb_creation.sql` - Generated SQL commands
- `MINDSDB_KNOWLEDGE_BASE_STRATEGY.md` - Design rationale
- `MINDSDB_CREATE_KB_SYNTAX.md` - SQL syntax reference
- `MINDSDB_SQL_EXAMPLES.sql` - Copy-paste examples

## ✅ Success Criteria

After setup, you should be able to:
- ✅ Query any KB with natural language questions
- ✅ Get relevant markdown file content with metadata
- ✅ Filter by category, date, file size
- ✅ See 3-5 second response times for queries
- ✅ Get contextually relevant answers with proper ranking

## 🎉 Next Steps

1. **Test all 5 KBs** with sample queries
2. **Document common queries** for team use
3. **Set up n8n workflow** for automatic updates (optional)
4. **Monitor performance** and optimize as needed

---

**Version:** v3.0
**Last Updated:** 2025-11-07
**Maintained by:** SoleFlipper Team
