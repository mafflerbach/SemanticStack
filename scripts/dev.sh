#!/bin/bash
# Development environment startup

echo "🚀 Starting development environment..."

# Start core services
docker-compose --profile development up -d postgres pgadmin

echo "⏳ Waiting for database to be ready..."
sleep 10

echo "✅ Development environment ready!"
echo "📊 PgAdmin: http://localhost:8080 (admin@codeanalysis.local / admin)"
echo "🗄️  Database: localhost:5432 (analyzer / secure_password_change_me)"
