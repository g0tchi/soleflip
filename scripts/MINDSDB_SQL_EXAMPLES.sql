-- ============================================================================
-- MindsDB Knowledge Base - COPY-PASTE Ready SQL Examples
-- SoleFlipper Project
-- ============================================================================

-- ✅ VERIFIED WORKING SYNTAX
-- Trailing commas in JSON objects are allowed and recommended
-- Commas between USING parameters are required

-- ============================================================================
-- 1. Projekt erstellen
-- ============================================================================
CREATE DATABASE soleflipper;

-- ============================================================================
-- 2. Knowledge Bases erstellen (5 domain-basierte KBs)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- KB 1: Database Schema & Migrations
-- ----------------------------------------------------------------------------
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
-- ✅ Trailing commas in JSON objects sind erlaubt und empfohlen!

-- ----------------------------------------------------------------------------
-- KB 2: External Integrations & APIs
-- ----------------------------------------------------------------------------
CREATE KNOWLEDGE_BASE soleflipper.kb_integrations
USING
    embedding_model = {
        "provider": "openai",
        "model_name": "text-embedding-3-small",
    },
    reranking_model = {
        "provider": "openai",
        "model_name": "gpt-4o",
    };

-- ----------------------------------------------------------------------------
-- KB 3: Architecture & Design Patterns
-- ----------------------------------------------------------------------------
CREATE KNOWLEDGE_BASE soleflipper.kb_architecture_design
USING
    embedding_model = {
        "provider": "openai",
        "model_name": "text-embedding-3-small",
    },
    reranking_model = {
        "provider": "openai",
        "model_name": "gpt-4o",
    };

-- ----------------------------------------------------------------------------
-- KB 4: Code Quality & Development
-- ----------------------------------------------------------------------------
CREATE KNOWLEDGE_BASE soleflipper.kb_code_quality_dev
USING
    embedding_model = {
        "provider": "openai",
        "model_name": "text-embedding-3-small",
    },
    reranking_model = {
        "provider": "openai",
        "model_name": "gpt-4o",
    };

-- ----------------------------------------------------------------------------
-- KB 5: Operations & Historical Context
-- ----------------------------------------------------------------------------
CREATE KNOWLEDGE_BASE soleflipper.kb_operations_history
USING
    embedding_model = {
        "provider": "openai",
        "model_name": "text-embedding-3-small",
    },
    reranking_model = {
        "provider": "openai",
        "model_name": "gpt-4o",
    };

-- ============================================================================
-- 3. Mit API Key (falls nicht in Environment Variable)
-- ============================================================================

-- Variante mit explizitem API Key:
CREATE KNOWLEDGE_BASE soleflipper.kb_database_schema
USING
    embedding_model = {
        "provider": "openai",
        "model_name": "text-embedding-3-small",
        "api_key": "sk-..."
    },
    reranking_model = {
        "provider": "openai",
        "model_name": "gpt-4o",
        "api_key": "sk-..."
    };

-- ============================================================================
-- 4. Test-Queries (nach KB-Erstellung)
-- ============================================================================

-- Test KB 1: Database Schema
SELECT *
FROM soleflipper.kb_database_schema
WHERE question = 'Wie ist die Datenbankstruktur?'
LIMIT 3;

-- Test KB 2: Integrations
SELECT *
FROM soleflipper.kb_integrations
WHERE question = 'Wie funktioniert die StockX-Integration?'
LIMIT 3;

-- Test KB 3: Architecture
SELECT *
FROM soleflipper.kb_architecture_design
WHERE question = 'Wie funktioniert die Pricing-Engine?'
LIMIT 3;

-- Test KB 4: Code Quality
SELECT *
FROM soleflipper.kb_code_quality_dev
WHERE question = 'Welche Linting-Standards gelten?'
LIMIT 3;

-- Test KB 5: Operations
SELECT *
FROM soleflipper.kb_operations_history
WHERE question = 'Wie funktioniert die Notion-Synchronisation?'
LIMIT 3;

-- ============================================================================
-- 5. Knowledge Base Management
-- ============================================================================

-- Alle Knowledge Bases anzeigen
SHOW KNOWLEDGE_BASES FROM soleflipper;

-- Knowledge Base löschen (falls neu erstellen)
DROP KNOWLEDGE_BASE soleflipper.kb_database_schema;

-- Projekt löschen (löscht auch alle KBs)
DROP DATABASE soleflipper;

-- ============================================================================
-- Syntax-Hinweise (VERIFIED ✅)
-- ============================================================================

-- ✅ RICHTIG - Trailing commas in JSON sind erlaubt:
CREATE KNOWLEDGE_BASE soleflipper.kb_test
USING
    embedding_model = {
        "provider": "openai",
        "model_name": "text-embedding-3-small",  -- Trailing comma OK!
    },
    reranking_model = {
        "provider": "openai",
        "model_name": "gpt-4o",  -- Trailing comma OK!
    };  -- <-- Semikolon am Ende

-- ❌ Häufiger Fehler - Fehlendes Semikolon:
/*
CREATE KNOWLEDGE_BASE soleflipper.kb_test
USING
    embedding_model = {...}
-- Fehlt das Semikolon!

Fehler: Query nicht vollständig
*/

-- ✅ RICHTIG - Mit Semikolon:
CREATE KNOWLEDGE_BASE soleflipper.kb_test
USING
    embedding_model = {
        "provider": "openai",
        "model_name": "text-embedding-3-small",
    };  -- <-- Semikolon erforderlich

-- ============================================================================
-- Advanced: Mit allen Parametern
-- ============================================================================

-- Nur verwenden, wenn du eigene Datenbank-Tabelle als Source hast:
CREATE KNOWLEDGE_BASE soleflipper.kb_advanced
FROM (
    SELECT
        id,
        file_path,
        content,
        category,
        last_updated
    FROM my_docs_table
    WHERE category = 'migrations'
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
    metadata_columns = ['file_path', 'category', 'last_updated'],
    content_columns = ['content'],
    id_column = 'id';
-- Beachte: Kommas zwischen Parametern, kein Komma vor Semikolon!

-- ============================================================================
-- Ende der SQL-Beispiele
-- ============================================================================
