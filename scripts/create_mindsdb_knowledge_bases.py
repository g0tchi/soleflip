#!/usr/bin/env python3
"""
MindsDB Knowledge Base Creator for SoleFlipper Project (v2.0)

This script creates optimized domain-based knowledge bases in MindsDB using
the content from the context/ folder. Uses the recommended 5-KB structure
for optimal query performance.

Requirements:
    pip install requests

Usage:
    python create_mindsdb_knowledge_bases.py

Configuration:
    Update the MINDSDB_URL, USERNAME, PASSWORD, and OPENAI_API_KEY variables below.
"""

import os
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional, Set
import sys
from datetime import datetime


# ============================================================================
# CONFIGURATION - UPDATE THESE VALUES
# ============================================================================
MINDSDB_URL = "https://minds.netzhouse.synology.me"
USERNAME = "g0tchi"
PASSWORD = "iK3C9NX7czMQhXQ3"
PROJECT_NAME = "soleflipper"

# OpenAI API Key for embeddings (or set OPENAI_API_KEY environment variable)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Embedding Configuration
EMBEDDING_MODEL = "text-embedding-3-small"  # Fast, cheap, good for docs
RERANKING_MODEL = "gpt-4o"  # Best quality re-ranking

# Context folder path (relative to script location)
SCRIPT_DIR = Path(__file__).parent.parent
CONTEXT_DIR = SCRIPT_DIR / "context"

# Version
VERSION = "v2.5.1"


# ============================================================================
# MindsDB API Client
# ============================================================================
class MindsDBClient:
    """Client for interacting with MindsDB API"""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.token: Optional[str] = None

    def login(self) -> bool:
        """Authenticate and get session token"""
        print(f"🔐 Authenticating with MindsDB at {self.base_url}...")

        # Try different login endpoints
        login_endpoints = [
            f"{self.base_url}/api/login",
            f"{self.base_url}/cloud/login",
        ]

        for endpoint in login_endpoints:
            try:
                # Try with username
                response = self.session.post(
                    endpoint,
                    json={"username": self.username, "password": self.password},
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    if 'token' in data:
                        self.token = data['token']
                        self.session.headers.update({
                            'Authorization': f'Bearer {self.token}'
                        })
                        print(f"✅ Successfully authenticated!")
                        return True
                    print(f"✅ Login successful (session-based)")
                    return True

                # Try with email
                response = self.session.post(
                    endpoint,
                    json={"email": self.username, "password": self.password},
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    if 'token' in data:
                        self.token = data['token']
                        self.session.headers.update({
                            'Authorization': f'Bearer {self.token}'
                        })
                        print(f"✅ Successfully authenticated!")
                        return True
                    print(f"✅ Login successful (session-based)")
                    return True

            except Exception as e:
                print(f"⚠️  Endpoint {endpoint} failed: {e}")
                continue

        # Try HTTP Basic Auth as fallback
        try:
            self.session.auth = (self.username, self.password)
            response = self.session.get(f"{self.base_url}/api/status", timeout=10)
            if response.status_code == 200:
                print(f"✅ Using HTTP Basic Authentication")
                return True
        except Exception as e:
            print(f"⚠️  Basic auth failed: {e}")

        print(f"❌ Authentication failed. Please check credentials.")
        return False

    def execute_sql(self, query: str) -> Dict:
        """Execute SQL query via MindsDB API"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/sql/query",
                json={"query": query},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ SQL execution failed: {e}")
            return {}

    def create_project(self, project_name: str) -> bool:
        """Create a new project in MindsDB"""
        print(f"📁 Creating project '{project_name}'...")

        # Check if project exists
        result = self.execute_sql(f"SHOW DATABASES")
        if result and 'data' in result:
            projects = [row[0] for row in result.get('data', [])]
            if project_name in projects:
                print(f"ℹ️  Project '{project_name}' already exists")
                return True

        # Create project
        query = f"CREATE DATABASE {project_name}"
        result = self.execute_sql(query)

        if result:
            print(f"✅ Project '{project_name}' created successfully")
            return True

        print(f"❌ Failed to create project '{project_name}'")
        return False

    def create_knowledge_base(
        self,
        project_name: str,
        kb_name: str,
        content: str,
        metadata: Dict[str, any] = None,
        embedding_model: str = EMBEDDING_MODEL,
        reranking_model: str = RERANKING_MODEL,
        api_key: str = OPENAI_API_KEY
    ) -> bool:
        """Create a knowledge base with the given content and metadata"""
        print(f"📚 Creating knowledge base '{kb_name}'...")

        if metadata is None:
            metadata = {}

        # Escape single quotes in content
        content_escaped = content.replace("'", "''")

        # Build embedding model config
        embedding_config = {
            "provider": "openai",
            "model_name": embedding_model
        }
        if api_key:
            embedding_config["api_key"] = api_key

        # Build reranking model config (optional)
        reranking_config = {
            "provider": "openai",
            "model_name": reranking_model
        }
        if api_key:
            reranking_config["api_key"] = api_key

        # Create knowledge base using SQL with full syntax
        # Note: No trailing comma after last parameter
        query = f"""
        CREATE KNOWLEDGE_BASE {project_name}.{kb_name}
        USING
            embedding_model = {json.dumps(embedding_config)},
            reranking_model = {json.dumps(reranking_config)}
        """

        try:
            result = self.execute_sql(query)
            if result:
                print(f"✅ Knowledge base '{kb_name}' created successfully")
                print(f"   - Embedding: {embedding_model}")
                print(f"   - Reranking: {reranking_model}")
                print(f"   - Content size: {len(content)} chars")
                return True
        except Exception as e:
            print(f"❌ Failed to create knowledge base '{kb_name}': {e}")

        print(f"❌ Failed to create knowledge base '{kb_name}'")
        return False


# ============================================================================
# Content Processing Functions
# ============================================================================
def read_file_content(file_path: Path) -> Optional[str]:
    """Read file content, handling different file types"""
    try:
        # Skip binary files
        if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.pdf', '.csv', '.gz']:
            print(f"⏭️  Skipping binary file: {file_path.name}")
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"⚠️  Could not read {file_path}: {e}")
        return None


def collect_folder_content(folder_path: Path) -> Dict[str, str]:
    """Collect all markdown files from a folder"""
    content_map = {}

    for file_path in folder_path.rglob('*.md'):
        content = read_file_content(file_path)
        if content:
            # Use relative path as key
            rel_path = file_path.relative_to(folder_path)
            content_map[str(rel_path)] = content

    return content_map


def create_combined_content(content_map: Dict[str, str], category: str) -> str:
    """Combine multiple files into a single knowledge base content"""
    combined = f"# SoleFlipper Documentation - {category}\n\n"

    for file_path, content in content_map.items():
        combined += f"## File: {file_path}\n\n"
        combined += content
        combined += "\n\n---\n\n"

    return combined


# ============================================================================
# Domain-Based Knowledge Base Definitions (Optimized Structure)
# ============================================================================
KB_DEFINITIONS = {
    "database_schema": {
        "name": "kb_database_schema",
        "title": "Database Schema & Migrations",
        "description": "Database schema, migrations, and data architecture",
        "paths": [
            CONTEXT_DIR / "migrations",
            CONTEXT_DIR / "database",
        ],
        "include_patterns": ["*.md"],
        "exclude_patterns": [],
        "architecture_filters": ["database-*.md", "schema-*.md", "transactions-*.md"],
        "use_cases": [
            "How is the database structured?",
            "What migrations were performed?",
            "Multi-platform order system architecture"
        ]
    },
    "integrations": {
        "name": "kb_integrations",
        "title": "External Integrations & APIs",
        "description": "StockX, Metabase, Awin integrations and API documentation",
        "paths": [
            CONTEXT_DIR / "integrations",
        ],
        "include_patterns": ["*.md"],
        "exclude_patterns": ["*.pdf", "*.csv", "*.gz", "*.png", "*.jpg"],
        "use_cases": [
            "How does StockX integration work?",
            "What Metabase dashboards exist?",
            "How to import Awin feeds?"
        ]
    },
    "architecture_design": {
        "name": "kb_architecture_design",
        "title": "Architecture & Design Patterns",
        "description": "System architecture, design patterns, and business logic",
        "paths": [
            CONTEXT_DIR / "architecture",
        ],
        "include_patterns": ["*.md"],
        "exclude_patterns": ["database-*.md", "schema-*.md", "transactions-*.md"],
        "use_cases": [
            "How does the pricing engine work?",
            "What is the DDD structure?",
            "ROI calculation implementation"
        ]
    },
    "code_quality_dev": {
        "name": "kb_code_quality_dev",
        "title": "Code Quality & Development",
        "description": "Development standards, code quality, testing, and API documentation",
        "paths": [
            CONTEXT_DIR / "refactoring",
            SCRIPT_DIR / "CLAUDE.md",
            SCRIPT_DIR / "README.md",
        ],
        "include_patterns": ["*.md"],
        "exclude_patterns": [],
        "use_cases": [
            "What linting standards apply?",
            "How to run tests?",
            "What are the make commands?"
        ]
    },
    "operations_history": {
        "name": "kb_operations_history",
        "title": "Operations & Historical Context",
        "description": "Notion integration, archived documentation, and historical decisions",
        "paths": [
            CONTEXT_DIR / "notion",
            CONTEXT_DIR / "archived",
        ],
        "include_patterns": ["*.md"],
        "exclude_patterns": [],
        "use_cases": [
            "How does Notion sync work?",
            "What happened in the refactoring sprint?",
            "Historical architectural decisions"
        ]
    }
}


def collect_kb_content(kb_def: Dict) -> Dict[str, str]:
    """Collect content for a specific knowledge base based on its definition"""
    content_map = {}

    for base_path in kb_def["paths"]:
        if not base_path.exists():
            print(f"⚠️  Path does not exist: {base_path}")
            continue

        # If it's a file, add it directly
        if base_path.is_file():
            content = read_file_content(base_path)
            if content:
                content_map[str(base_path.name)] = content
            continue

        # If it's a directory, collect all matching files
        for pattern in kb_def["include_patterns"]:
            for file_path in base_path.rglob(pattern):
                # Check if file should be excluded
                should_exclude = False
                for exclude_pattern in kb_def["exclude_patterns"]:
                    if exclude_pattern.startswith("*"):
                        # Pattern like "*.pdf"
                        if file_path.suffix == exclude_pattern[1:]:
                            should_exclude = True
                            break
                    else:
                        # Pattern like "database-*.md"
                        if file_path.match(exclude_pattern):
                            should_exclude = True
                            break

                # Special handling for architecture filters
                if "architecture_filters" in kb_def and "architecture" in str(base_path):
                    # Only include files matching architecture filters
                    matches_filter = False
                    for arch_filter in kb_def["architecture_filters"]:
                        if file_path.match(arch_filter):
                            matches_filter = True
                            break
                    if not matches_filter:
                        should_exclude = True

                if should_exclude:
                    continue

                content = read_file_content(file_path)
                if content:
                    rel_path = file_path.relative_to(CONTEXT_DIR if CONTEXT_DIR in file_path.parents else SCRIPT_DIR)
                    content_map[str(rel_path)] = content

    return content_map


def create_kb_content_with_metadata(kb_def: Dict, content_map: Dict[str, str]) -> str:
    """Create knowledge base content with rich metadata"""
    content = f"""# {kb_def['title']}

**Knowledge Base:** `{kb_def['name']}`
**Version:** {VERSION}
**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}
**Description:** {kb_def['description']}

---

## Purpose & Use Cases

This knowledge base answers questions like:
"""

    for use_case in kb_def["use_cases"]:
        content += f"- {use_case}\n"

    content += f"\n---\n\n## Content Sources\n\n"
    content += f"Total files: {len(content_map)}\n\n"

    for file_path in sorted(content_map.keys()):
        content += f"- `{file_path}`\n"

    content += f"\n---\n\n## Documentation Content\n\n"

    # Add all file contents
    for file_path, file_content in sorted(content_map.items()):
        content += f"### Source: `{file_path}`\n\n"
        content += file_content
        content += "\n\n---\n\n"

    return content


# ============================================================================
# Knowledge Base Creation Strategy
# ============================================================================
def create_knowledge_bases(client: MindsDBClient, project_name: str):
    """Create all knowledge bases for the SoleFlipper project"""

    if not CONTEXT_DIR.exists():
        print(f"❌ Context directory not found: {CONTEXT_DIR}")
        return

    print(f"\n📂 Processing context folder: {CONTEXT_DIR}\n")
    print(f"🎯 Strategy: Domain-based knowledge bases (5 KBs)\n")

    # Track success/failure
    results = {"success": [], "failed": []}
    stats = {}

    # Create knowledge base for each domain
    for kb_id, kb_def in KB_DEFINITIONS.items():
        print(f"\n{'='*60}")
        print(f"Processing: {kb_def['title']}")
        print(f"{'='*60}\n")

        # Collect content
        print(f"📂 Scanning paths:")
        for path in kb_def["paths"]:
            print(f"   - {path}")

        content_map = collect_kb_content(kb_def)

        if not content_map:
            print(f"⚠️  No files found for {kb_def['name']}")
            results["failed"].append(kb_def['name'])
            continue

        print(f"📄 Found {len(content_map)} files")

        # Calculate size
        total_size = sum(len(content) for content in content_map.values())
        size_kb = total_size / 1024
        print(f"📊 Total content size: {size_kb:.1f} KB")

        # Warn if too large
        if size_kb > 500:
            print(f"⚠️  WARNING: Knowledge base is large ({size_kb:.1f} KB)")
            print(f"   Consider splitting or removing large files")

        # Create combined content with metadata
        combined_content = create_kb_content_with_metadata(kb_def, content_map)

        # Create knowledge base
        print(f"🚀 Creating knowledge base...")
        metadata = {
            "kb_id": kb_id,
            "title": kb_def["title"],
            "description": kb_def["description"],
            "file_count": len(content_map),
            "size_kb": size_kb,
            "version": VERSION
        }

        success = client.create_knowledge_base(
            project_name=project_name,
            kb_name=kb_def['name'],
            content=combined_content,
            metadata=metadata
        )

        if success:
            results["success"].append(kb_def['name'])
            stats[kb_def['name']] = {
                "files": len(content_map),
                "size_kb": size_kb
            }
        else:
            results["failed"].append(kb_def['name'])

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successfully created: {len(results['success'])} knowledge bases")

    total_files = 0
    total_size = 0

    for kb in results['success']:
        if kb in stats:
            files = stats[kb]['files']
            size_kb = stats[kb]['size_kb']
            total_files += files
            total_size += size_kb
            print(f"   - {kb}: {files} files, {size_kb:.1f} KB")
        else:
            print(f"   - {kb}")

    if results['failed']:
        print(f"\n❌ Failed to create: {len(results['failed'])} knowledge bases")
        for kb in results['failed']:
            print(f"   - {kb}")

    print(f"\n📊 Total Statistics:")
    print(f"   - Knowledge Bases: {len(results['success'])}")
    print(f"   - Total Files: {total_files}")
    print(f"   - Total Size: {total_size:.1f} KB ({total_size/1024:.2f} MB)")

    if OPENAI_API_KEY:
        print(f"\n✅ OpenAI API key is configured")
    else:
        print(f"\n⚠️  WARNING: OpenAI API key not set!")
        print(f"   Set OPENAI_API_KEY environment variable or update script config")


# ============================================================================
# Main Execution
# ============================================================================
def main():
    """Main execution function"""
    print("=" * 60)
    print("MindsDB Knowledge Base Creator for SoleFlipper")
    print("=" * 60)
    print()

    # Create client
    client = MindsDBClient(MINDSDB_URL, USERNAME, PASSWORD)

    # Authenticate
    if not client.login():
        print("\n❌ Authentication failed. Please check your credentials and network access.")
        sys.exit(1)

    # Create project
    if not client.create_project(PROJECT_NAME):
        print(f"\n❌ Failed to create project '{PROJECT_NAME}'")
        sys.exit(1)

    # Create knowledge bases
    create_knowledge_bases(client, PROJECT_NAME)

    print("\n" + "=" * 60)
    print("✅ Knowledge base creation completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
