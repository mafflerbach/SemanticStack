#!/bin/bash
# Reset everything - useful during development

echo "🧹 Resetting environment..."

docker-compose down -v
docker-compose build
docker system prune -f

echo "✅ Environment reset complete!"
