#!/bin/bash
# Quick test script for MCP server

cd "$(dirname "$0")"

echo "🧪 Testing Memori MCP Server..."

if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Run ./setup_local_mcp.sh first"
    exit 1
fi

source .venv/bin/activate

echo "📝 Testing server startup..."
timeout 2s python server.py <<< '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' 2>/dev/null || true

if [ $? -eq 124 ]; then
    echo "✅ MCP Server starts successfully"
else
    echo "⚠️  Check server logs for errors"
fi

echo ""
echo "To use with Claude Code, add config from: claude_code_config.json"
