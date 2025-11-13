#!/bin/bash
# Setup script for local Memori MCP Server (for Claude Code)

set -e

echo "🔧 Setting up Memori MCP Server for Claude Code..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2 | cut -d '.' -f 1,2)
echo "✅ Found Python $PYTHON_VERSION"

# Create virtual environment if not exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet mcp asyncpg python-dotenv structlog

# Create .env file if not exists
if [ ! -f ".env.local" ]; then
    echo "📝 Creating .env.local file..."
    cat > .env.local << 'EOF'
# Memori MCP Server Local Configuration
MEMORI_DATABASE_URL=postgresql://soleflip:SoleFlip2025SecureDB!@localhost:5432/memori
MEMORI_NAMESPACE=soleflip
MEMORI_LOGGING_LEVEL=INFO
EOF
    echo "⚠️  Please update .env.local with your database credentials"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To use with Claude Code, add this to your MCP config:"
echo ""
echo "  {"
echo "    \"mcpServers\": {"
echo "      \"memori\": {"
echo "        \"command\": \"$(pwd)/.venv/bin/python\","
echo "        \"args\": [\"$(pwd)/server.py\"],"
echo "        \"env\": {"
echo "          \"MEMORI_DATABASE_URL\": \"postgresql://soleflip:YOUR_PASSWORD@localhost:5432/memori\","
echo "          \"MEMORI_NAMESPACE\": \"soleflip\""
echo "        }"
echo "      }"
echo "    }"
echo "  }"
echo ""
echo "Or run manually:"
echo "  source .venv/bin/activate"
echo "  python server.py"
