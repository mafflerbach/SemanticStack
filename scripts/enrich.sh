#!/bin/bash
echo "🚀 Running Full Analysis Pipeline..."
echo "1. Parsing code..."
docker-compose --profile parser up parser

echo "2. Enriching with LLM..."
docker-compose --profile enrichment up enricher

echo "3. Starting API..."
docker-compose up api -d

echo "✅ Pipeline complete!"
