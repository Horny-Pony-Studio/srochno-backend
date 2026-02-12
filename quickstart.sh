#!/bin/bash

# Срочные Услуги - Quick Start Script
# Usage: ./quickstart.sh

set -e

echo "🚀 Срочные Услуги Backend - Quick Start"
echo "========================================"
echo ""

# Check Python version
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11+ required. Install it first:"
    echo "   Ubuntu: sudo apt install python3.11 python3.11-venv"
    echo "   macOS: brew install python@3.11"
    exit 1
fi

echo "✓ Python 3.11+ found"

# Check PostgreSQL
if ! command -v psql &> /dev/null; then
    echo "⚠️  PostgreSQL not found. Install it:"
    echo "   Ubuntu: sudo apt install postgresql postgresql-contrib"
    echo "   macOS: brew install postgresql"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install Poetry if not present
if ! command -v poetry &> /dev/null; then
    echo "📦 Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "✓ Poetry found"

# Install dependencies
echo "📦 Installing dependencies..."
poetry install

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file with your values:"
    echo "   - TELEGRAM_BOT_TOKEN (get from @BotFather)"
    echo "   - DATABASE_URL (PostgreSQL connection)"
    echo "   - SECRET_KEY (generate with: openssl rand -hex 32)"
    echo ""
    read -p "Press Enter to edit .env now..." -r
    ${EDITOR:-nano} .env
fi

echo "✓ Environment configured"

# Database setup
echo "🗄️  Setting up database..."
read -p "Database name [srochno]: " dbname
dbname=${dbname:-srochno}

read -p "Database user [srochno]: " dbuser
dbuser=${dbuser:-srochno}

read -sp "Database password: " dbpass
echo ""

# Try to create database
if command -v psql &> /dev/null; then
    echo "Creating database..."
    sudo -u postgres psql -c "CREATE DATABASE $dbname;" 2>/dev/null || echo "Database already exists"
    sudo -u postgres psql -c "CREATE USER $dbuser WITH PASSWORD '$dbpass';" 2>/dev/null || echo "User already exists"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $dbname TO $dbuser;" 2>/dev/null

    # Update .env with database URL
    sed -i "s|DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://$dbuser:$dbpass@localhost:5432/$dbname|" .env
    echo "✓ Database configured"
else
    echo "⚠️  Skipping database creation (psql not found)"
fi

# Run migrations
echo "🔄 Running migrations..."
poetry run alembic upgrade head
echo "✓ Migrations applied"

# Start server
echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Starting development server..."
echo "   API: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

poetry run uvicorn app.main:app --reload --port 8000
