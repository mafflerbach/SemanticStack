#!/bin/bash
# Production environment startup

echo "🚀 Starting production environment..."

# Start all services except development tools
docker-compose --profile production up -d

echo "✅ Production environment ready!"
echo "🌐 API: http://localhost:8000"
echo "💻 Frontend: http://localhost:5173"
