# MindsDB CREATE KNOWLEDGE_BASE - Vollständige Syntax für SoleFlipper

## 📖 Basis-Syntax (VERIFIED WORKING ✅)

```sql
CREATE KNOWLEDGE_BASE [project_name.]kb_name
FROM (
    SELECT * FROM data_source
)
USING
    embedding_model = {
        "provider": "openai",              -- openai | azure_openai | custom_openai | huggingface
        "model_name": "text-embedding-3-small",  -- Embedding-Modell
        "api_key": "sk-...",               -- Optional, falls nicht in ENV
    },
    reranking_model = {
        "provider": "openai",              -- openai | azure_openai | custom_openai
        "model_name": "gpt-4o",           -- Reranking-Modell
        "api_key": "sk-...",               -- Optional, falls nicht in ENV
    },
    storage = my_vector_store.storage_table,  -- Optional: Vektor-DB (ChromaDB default)
    metadata_columns = ['date', 'creator', 'version'],  -- Optional: Metadaten-Spalten
    content_columns = ['content', 'description'],        -- Optional: Content-Spalten
    id_column = 'id';                      -- Semikolon am Ende!
```

**Syntax-Hinweise:**
- ✅ **Trailing commas** in JSON-Objekten sind **erlaubt** (und empfohlen für bessere Lesbarkeit)
- ✅ Komma zwischen USING-Parametern
- ✅ Semikolon am Ende des Statements

---

## 🎯 Konkrete Beispiele für SoleFlipper

### Beispiel 1: kb_database_schema (Minimal - nur Embedding)

```sql
CREATE KNOWLEDGE_BASE soleflipper.kb_database_schema
USING
    embedding_model = {
        "provider": "openai",
        "model_name": "text-embedding-3-small",
    };
```

✅ **Korrekt:** Trailing comma in JSON-Objekt ist erlaubt

---

### Beispiel 1b: Mit Embedding + Reranking (EMPFOHLEN ⭐)

```sql
CREATE KNOWLEDGE_BASE soleflipper.kb_database_schema
USING
    embedding_model = {
        "provider": "openai",
        "model_name": "text-embedding-3-small",
    },
    reranking_model = {
        "provider": "openai",
        "model_name": "gpt-4o",
    };
```

✅ **VERIFIED WORKING** - Diese Syntax wurde erfolgreich getestet!

**Syntax-Details:**
- Trailing commas nach letztem Property in JSON-Objekten: **erlaubt** ✅
- Komma zwischen embedding_model und reranking_model: **erforderlich** ✅
- Semikolon am Ende: **erforderlich** ✅

**Hinweis:** Content wird direkt im CREATE-Statement übergeben (siehe Python-Script).

---

### Beispiel 2: kb_database_schema (Mit Metadaten)

```sql
CREATE KNOWLEDGE_BASE soleflipper.kb_database_schema
FROM (
    SELECT
        id,
        file_path,
        content,
        category,
        last_updated,
        file_size,
        version
    FROM context_files
    WHERE category IN ('migrations', 'database', 'schema')
)
USING
    embedding_model = {
        "provider": "openai",
        "model_name": "text-embedding-3-small",
        "dimensions": 1536
    },
    reranking_model = {
        "provider": "openai",
        "model_name": "gpt-4o"
    },
    metadata_columns = ['file_path', 'category', 'last_updated', 'version'],
    content_columns = ['content'],
    id_column = 'id';
```

---

### Beispiel 3: kb_integrations (Mit Custom Vector Store)

```sql
-- Schritt 1: Vector Store erstellen (optional)
CREATE DATABASE my_vector_db
WITH ENGINE = 'chromadb',
PARAMETERS = {
    "persist_directory": "/path/to/chroma/db"
};

-- Schritt 2: Knowledge Base erstellen
CREATE KNOWLEDGE_BASE soleflipper.kb_integrations
FROM (
    SELECT
        md5(file_path) as id,
        file_path,
        content,
        'integrations' as category,
        NOW() as created_at
    FROM integration_docs
    WHERE file_extension = '.md'
)
USING
    embedding_model = {
        "provider": "openai",
        "model_name": "text-embedding-3-small"
    },
    reranking_model = {
        "provider": "openai",
        "model_name": "gpt-4o"
    },
    storage = my_vector_db.knowledge_embeddings,
    metadata_columns = ['file_path', 'category', 'created_at'],
    content_columns = ['content'],
    id_column = 'id';
```

---

## 🔧 Parameter-Referenz

### `embedding_model` (Erforderlich)

**Zweck:** Konvertiert Text in Vektor-Embeddings für semantische Suche

**Optionen:**

| Provider | Model Name | Dimensions | Use Case |
|----------|-----------|------------|----------|
| `openai` | `text-embedding-3-small` | 1536 | Schnell, günstig, gut für Docs |
| `openai` | `text-embedding-3-large` | 3072 | Bessere Qualität, langsamer |
| `openai` | `text-embedding-ada-002` | 1536 | Legacy, stabil |
| `azure_openai` | `text-embedding-ada-002` | 1536 | Für Azure-Deployments |
| `huggingface` | `sentence-transformers/all-MiniLM-L6-v2` | 384 | Open Source, lokal |

**Beispiel:**
```sql
embedding_model = {
    "provider": "openai",
    "model_name": "text-embedding-3-small",
    "dimensions": 1536,  -- Optional
    "api_key": "sk-..."   -- Optional, falls nicht in OPENAI_API_KEY ENV
}
```

---

### `reranking_model` (Optional, aber empfohlen)

**Zweck:** Re-rankt die Top-K Ergebnisse für bessere Relevanz

**Optionen:**

| Provider | Model Name | Use Case |
|----------|-----------|----------|
| `openai` | `gpt-4o` | Beste Qualität |
| `openai` | `gpt-4-turbo` | Schneller |
| `openai` | `gpt-3.5-turbo` | Günstig |

**Beispiel:**
```sql
reranking_model = {
    "provider": "openai",
    "model_name": "gpt-4o",
    "api_key": "sk-..."  -- Optional
}
```

---

### `storage` (Optional)

**Zweck:** Definiert, wo die Vektor-Embeddings gespeichert werden

**Standard:** ChromaDB (in-memory oder persistent)

**Alternativen:**
- ChromaDB (persistent)
- Pinecone
- Weaviate
- Qdrant
- Milvus

**Beispiel:**
```sql
storage = my_chroma_db.embeddings_table
```

**Ohne storage:** MindsDB verwendet Standard-ChromaDB
```sql
-- Kein storage-Parameter = ChromaDB default
CREATE KNOWLEDGE_BASE kb_test
USING embedding_model = {...};
```

---

### `metadata_columns` (Optional)

**Zweck:** Zusätzliche Metadaten für Filterung und Kontext

**Use Cases:**
- Zeitbasierte Filterung: `WHERE last_updated > '2024-01-01'`
- Kategorisierung: `WHERE category = 'migrations'`
- Versionierung: `WHERE version = 'v2.5.1'`

**Beispiel:**
```sql
metadata_columns = ['file_path', 'category', 'last_updated', 'version', 'author']
```

**In Queries verwenden:**
```sql
SELECT *
FROM soleflipper.kb_database_schema
WHERE question = 'How is the orders table structured?'
  AND category = 'migrations'
  AND last_updated > '2024-10-01';
```

---

### `content_columns` (Optional)

**Zweck:** Definiert, welche Spalten als Content indexiert werden

**Standard:** Spalte mit Name `content`

**Use Cases:**
- Mehrere Content-Felder: `['content', 'description', 'summary']`
- Custom Column Names: `['markdown_text', 'code_snippet']`

**Beispiel:**
```sql
content_columns = ['content', 'code_examples', 'description']
```

---

### `id_column` (Optional)

**Zweck:** Eindeutiger Identifier für jeden Eintrag

**Standard:** Auto-generierte UUID

**Use Cases:**
- Existing IDs: `id_column = 'document_id'`
- Custom IDs: `id_column = md5(file_path)`

**Beispiel:**
```sql
id_column = 'doc_id'
```

---

## 📝 Vollständiges Beispiel für SoleFlipper

### kb_database_schema (Production-Ready)

```sql
CREATE KNOWLEDGE_BASE soleflipper.kb_database_schema
FROM (
    SELECT
        md5(CONCAT(category, '/', file_name)) as id,
        file_name,
        file_path,
        content,
        category,
        file_size_kb,
        last_modified,
        'v2.5.1' as version,
        CASE
            WHEN category = 'migrations' THEN 'high'
            WHEN category = 'database' THEN 'high'
            ELSE 'medium'
        END as priority
    FROM (
        -- Subquery mit allen Dateien
        VALUES
            ('MIGRATION_INDEX.md', 'context/migrations/MIGRATION_INDEX.md', '<content...>', 'migrations', 15, '2025-10-01'),
            ('database-analysis.md', 'context/database/database-analysis.md', '<content...>', 'database', 18, '2025-09-15'),
            -- ... weitere Dateien
    ) AS files(file_name, file_path, content, category, file_size_kb, last_modified)
)
USING
    embedding_model = {
        "provider": "openai",
        "model_name": "text-embedding-3-small",
        "dimensions": 1536
    },
    reranking_model = {
        "provider": "openai",
        "model_name": "gpt-4o"
    },
    metadata_columns = [
        'file_name',
        'file_path',
        'category',
        'file_size_kb',
        'last_modified',
        'version',
        'priority'
    ],
    content_columns = ['content'],
    id_column = 'id';
```

---

## 🔍 Queries auf Knowledge Bases

### Basis-Query

```sql
SELECT *
FROM soleflipper.kb_database_schema
WHERE question = 'Wie ist die orders-Tabelle strukturiert?';
```

### Query mit Metadaten-Filtern

```sql
SELECT
    file_name,
    file_path,
    content,
    category,
    last_modified
FROM soleflipper.kb_database_schema
WHERE question = 'Welche Migrationen wurden durchgeführt?'
  AND category = 'migrations'
  AND last_modified > '2024-09-01'
LIMIT 5;
```

### Query mit Re-Ranking

```sql
SELECT *
FROM soleflipper.kb_database_schema
WHERE question = 'Multi-platform order architecture'
  AND category IN ('migrations', 'database', 'architecture')
ORDER BY relevance_score DESC
LIMIT 3;
```

---

## 🚀 Für SoleFlipper: Vereinfachte Variante

**Wenn du keine Datenbank-Tabelle als Source hast**, kannst du Content direkt übergeben:

### Variante A: Inline Content (Python Script)

```python
# Im Python-Script
content = """
# SoleFlipper Database Schema Knowledge Base

## File: migrations/MIGRATION_INDEX.md
<content hier>

## File: database/database-analysis.md
<content hier>

...
"""

query = f"""
CREATE KNOWLEDGE_BASE soleflipper.kb_database_schema
USING
    embedding_model = {{
        "provider": "openai",
        "model_name": "text-embedding-3-small"
    }},
    content = '{content.replace("'", "''")}'
"""
```

### Variante B: File Upload (MindsDB Cloud)

```sql
-- Upload file first
CREATE KNOWLEDGE_BASE soleflipper.kb_database_schema
FROM FILES (
    '/path/to/database_schema_combined.md',
    '/path/to/migrations_combined.md'
)
USING
    embedding_model = {
        "provider": "openai",
        "model_name": "text-embedding-3-small"
    };
```

---

## 🎨 Best Practices für SoleFlipper

### 1. **Metadaten strukturieren**

```sql
metadata_columns = [
    'file_path',        -- Für Quellenangabe
    'category',         -- Für Filterung (migrations, integrations, etc.)
    'last_updated',     -- Für Aktualität
    'version',          -- Projekt-Version (v2.5.1)
    'importance'        -- high | medium | low
]
```

### 2. **Optimale Embedding-Modelle**

Für Dokumentation (SoleFlipper):
```sql
embedding_model = {
    "provider": "openai",
    "model_name": "text-embedding-3-small"  -- ✅ Perfekt für Docs
}
```

Für Code-Snippets:
```sql
embedding_model = {
    "provider": "openai",
    "model_name": "text-embedding-3-large"  -- Besser für komplexe Code-Semantik
}
```

### 3. **Re-Ranking immer verwenden**

```sql
reranking_model = {
    "provider": "openai",
    "model_name": "gpt-4o"  -- Verbessert Relevanz um ~20-30%
}
```

### 4. **Content-Struktur**

Strukturiere Content mit klaren Headings:
```markdown
# Knowledge Base: Database Schema

## Metadata
- Category: migrations, database
- Version: v2.5.1
- Last Updated: 2025-11-05

## Source: migrations/MIGRATION_INDEX.md
<content>

## Source: database/database-analysis.md
<content>
```

---

## 📋 Checkliste: Knowledge Base erstellen

- [ ] **API Keys gesetzt** (OPENAI_API_KEY)
- [ ] **Content vorbereitet** (Markdown-Dateien kombiniert)
- [ ] **Metadaten definiert** (file_path, category, etc.)
- [ ] **Embedding-Modell gewählt** (text-embedding-3-small empfohlen)
- [ ] **Re-Ranking aktiviert** (gpt-4o empfohlen)
- [ ] **Test-Query vorbereitet** (um KB zu validieren)
- [ ] **Storage entschieden** (ChromaDB default oder custom)

---

## ⚡ Quick Start für SoleFlipper

### Minimal-Variante (einfachste Methode)

```sql
CREATE KNOWLEDGE_BASE soleflipper.kb_database_schema
USING
    embedding_model = {
        "provider": "openai",
        "model_name": "text-embedding-3-small"
    };
```

**Dann Content via Python-Script hochladen** (siehe `create_mindsdb_knowledge_bases.py`)

---

## 🆘 Troubleshooting

### Problem: "OPENAI_API_KEY not found"
```sql
-- Lösung: API Key explizit angeben
embedding_model = {
    "provider": "openai",
    "model_name": "text-embedding-3-small",
    "api_key": "sk-..."
}
```

### Problem: "Content too large"
```sql
-- Lösung: Content aufteilen in mehrere KBs
-- Oder: Große Dateien (PDFs) separat verarbeiten
```

### Problem: "Invalid metadata column"
```sql
-- Lösung: Sicherstellen, dass Spalte in FROM-Clause existiert
metadata_columns = ['existing_column']  -- Nicht 'non_existing_column'
```

---

**Zusammenfassung für SoleFlipper:**

```sql
-- 1. Projekt erstellen
CREATE DATABASE soleflipper;

-- 2. Knowledge Base erstellen (einfachste Variante)
CREATE KNOWLEDGE_BASE soleflipper.kb_database_schema
USING
    embedding_model = {
        "provider": "openai",
        "model_name": "text-embedding-3-small"
    },
    reranking_model = {
        "provider": "openai",
        "model_name": "gpt-4o"
    };

-- 3. Testen
SELECT *
FROM soleflipper.kb_database_schema
WHERE question = 'Wie ist die Datenbankstruktur?'
LIMIT 3;
```

Content wird via Python-Script hochgeladen! 🚀
