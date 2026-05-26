#!/bin/bash
# Startup script for Red Agent

echo "================================"
echo "Caught U! - Red Agent Startup"
echo "================================"
echo ""

# Check Python
echo "Checking Python installation..."
python --version
if [ $? -ne 0 ]; then
    echo "❌ Python not found. Please install Python 3.9+";
    exit 1
fi

# Check .env file
echo ""
echo "Checking environment configuration..."
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.example .env
    echo "✓ Created .env (please fill in your credentials)"
    echo ""
    echo "Edit .env and add:"
    echo "  - NEO4J_URI"
    echo "  - NEO4J_USERNAME"
    echo "  - NEO4J_PASSWORD"
    echo "  - CLAUDE_API_KEY"
    echo ""
    exit 1
fi

echo "✓ .env file found"

# Create data directory
echo ""
echo "Creating data directory..."
mkdir -p data
echo "✓ data/ directory ready"

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✓ Dependencies installed"

# Test Neo4j connection
echo ""
echo "Testing Neo4j connection..."
python -c "
from neo4j_client import Neo4jClient
import sys
try:
    client = Neo4jClient()
    if client.check_connection():
        print('✓ Neo4j connection successful')
        client.close()
    else:
        print('❌ Neo4j connection failed')
        sys.exit(1)
except Exception as e:
    print(f'❌ Error: {str(e)}')
    sys.exit(1)
"
if [ $? -ne 0 ]; then
    echo "❌ Neo4j connection test failed"
    exit 1
fi

echo ""
echo "================================"
echo "✓ All checks passed!"
echo "================================"
echo ""
echo "To start the API server, run:"
echo "  python -m uvicorn main:app --reload"
echo ""
echo "Or to run examples, run:"
echo "  python example_usage.py"
echo ""
