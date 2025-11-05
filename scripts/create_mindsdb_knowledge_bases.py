#!/usr/bin/env python3
"""
MindsDB Knowledge Base Creator for SoleFlipper Project

This script creates knowledge bases in MindsDB using the content from the context/ folder.
It should be run on a machine that has access to the MindsDB instance.

Requirements:
    pip install requests

Usage:
    python create_mindsdb_knowledge_bases.py

Configuration:
    Update the MINDSDB_URL, USERNAME, and PASSWORD variables below.
"""

import os
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional
import sys


# ============================================================================
# CONFIGURATION - UPDATE THESE VALUES
# ============================================================================
MINDSDB_URL = "https://minds.netzhouse.synology.me"
USERNAME = "g0tchi"
PASSWORD = "iK3C9NX7czMQhXQ3"
PROJECT_NAME = "soleflipper"

# Context folder path (relative to script location)
SCRIPT_DIR = Path(__file__).parent.parent
CONTEXT_DIR = SCRIPT_DIR / "context"


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
        model: str = "gpt-4"
    ) -> bool:
        """Create a knowledge base with the given content"""
        print(f"📚 Creating knowledge base '{kb_name}'...")

        # Escape single quotes in content
        content_escaped = content.replace("'", "''")

        # Create knowledge base using SQL
        query = f"""
        CREATE KNOWLEDGE_BASE {project_name}.{kb_name}
        USING
            engine = 'openai',
            model = '{model}',
            content = '{content_escaped}'
        """

        result = self.execute_sql(query)

        if result:
            print(f"✅ Knowledge base '{kb_name}' created successfully")
            return True

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
# Knowledge Base Creation Strategy
# ============================================================================
def create_knowledge_bases(client: MindsDBClient, project_name: str):
    """Create all knowledge bases for the SoleFlipper project"""

    if not CONTEXT_DIR.exists():
        print(f"❌ Context directory not found: {CONTEXT_DIR}")
        return

    print(f"\n📂 Processing context folder: {CONTEXT_DIR}\n")

    # Define knowledge base categories
    categories = {
        "migrations": CONTEXT_DIR / "migrations",
        "integrations": CONTEXT_DIR / "integrations",
        "architecture": CONTEXT_DIR / "architecture",
        "refactoring": CONTEXT_DIR / "refactoring",
        "notion": CONTEXT_DIR / "notion",
        "archived": CONTEXT_DIR / "archived",
    }

    # Track success/failure
    results = {"success": [], "failed": []}

    # Create knowledge base for each category
    for category_name, category_path in categories.items():
        if not category_path.exists():
            print(f"⏭️  Skipping non-existent category: {category_name}")
            continue

        print(f"\n{'='*60}")
        print(f"Processing category: {category_name}")
        print(f"{'='*60}\n")

        # Collect content from this category
        content_map = collect_folder_content(category_path)

        if not content_map:
            print(f"⚠️  No markdown files found in {category_name}")
            continue

        print(f"📄 Found {len(content_map)} files in {category_name}")

        # Create combined content
        combined_content = create_combined_content(content_map, category_name.title())

        # Create knowledge base
        kb_name = f"kb_{category_name}"
        success = client.create_knowledge_base(
            project_name=project_name,
            kb_name=kb_name,
            content=combined_content
        )

        if success:
            results["success"].append(kb_name)
        else:
            results["failed"].append(kb_name)

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successfully created: {len(results['success'])} knowledge bases")
    for kb in results['success']:
        print(f"   - {kb}")

    if results['failed']:
        print(f"\n❌ Failed to create: {len(results['failed'])} knowledge bases")
        for kb in results['failed']:
            print(f"   - {kb}")


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
