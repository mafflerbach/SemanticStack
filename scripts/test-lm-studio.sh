#!/opt/homebrew/bin/bash

# Test script for LM Studio connectivity and functionality

echo "🧪 Testing LM Studio Setup"
echo "=========================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

LM_STUDIO_HOST="localhost:1234"

echo -e "\n${BLUE}🔍 Testing LM Studio endpoints...${NC}"

# Test if LM Studio is running
echo -n "Testing base endpoint... "
if curl -s http://${LM_STUDIO_HOST}/health > /dev/null 2>&1 || curl -s http://${LM_STUDIO_HOST}/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ LM Studio is running${NC}"
else
    echo -e "${RED}❌ LM Studio not accessible at http://${LM_STUDIO_HOST}${NC}"
    echo "Please start LM Studio and ensure the server is running on port 1234"
    exit 1
fi

# Test models endpoint
echo -n "Testing models endpoint... "
MODELS_RESPONSE=$(curl -s http://${LM_STUDIO_HOST}/v1/models)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Models endpoint accessible${NC}"
    echo "Available models:"
    echo "$MODELS_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for model in data.get('data', []):
        print(f'  • {model.get(\"id\", \"unknown\")}')
except:
    print('  (Could not parse models response)')
" 2>/dev/null || echo "  (Could not parse models list)"
else
    echo -e "${RED}❌ Models endpoint failed${NC}"
fi

# Test chat completion
echo -e "\n${BLUE}🤖 Testing LLM chat completion...${NC}"
CHAT_PAYLOAD='{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello, respond with just: Working"}],
    "max_tokens": 10
}'

CHAT_RESPONSE=$(curl -s -X POST http://${LM_STUDIO_HOST}/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d "$CHAT_PAYLOAD")

if [ $? -eq 0 ] && echo "$CHAT_RESPONSE" | grep -q "Working\|choices"; then
    echo -e "${GREEN}✅ LLM chat completion working${NC}"
    RESPONSE_TEXT=$(echo "$CHAT_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data['choices'][0]['message']['content'].strip())
except:
    print('(Could not parse response)')
" 2>/dev/null)
    echo "  Response: $RESPONSE_TEXT"
else
    echo -e "${RED}❌ LLM chat completion failed${NC}"
    echo "  Response: $CHAT_RESPONSE"
fi

# Test embedding models
echo -e "\n${BLUE}🔍 Testing embedding models...${NC}"

# Test your specific models
EMBEDDING_MODELS=(
    "text-embedding-all-minilm-l12-v2"
    "text-embedding-gguf-multi-qa-minilm-l6-cos-v1"
)

for model in "${EMBEDDING_MODELS[@]}"; do
    echo -n "Testing $model... "
    
    EMBED_PAYLOAD="{
        \"model\": \"$model\",
        \"input\": \"test embedding for code analysis\"
    }"
    
    EMBED_RESPONSE=$(curl -s -X POST http://${LM_STUDIO_HOST}/v1/embeddings \
        -H "Content-Type: application/json" \
        -d "$EMBED_PAYLOAD")
    
    if [ $? -eq 0 ] && echo "$EMBED_RESPONSE" | grep -q "embedding\|data"; then
        # Get embedding dimension
        DIMENSION=$(echo "$EMBED_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    embedding = data['data'][0]['embedding']
    print(len(embedding))
except:
    print('unknown')
" 2>/dev/null)
        echo -e "${GREEN}✅ Working (${DIMENSION}D)${NC}"
    else
        echo -e "${RED}❌ Failed${NC}"
        if echo "$EMBED_RESPONSE" | grep -q "not found\|error"; then
            echo "    Model may not be loaded in LM Studio"
        fi
    fi
done

# Test database connection
echo -e "\n${BLUE}💾 Testing database connection...${NC}"
if docker-compose exec postgres pg_isready -U analyzer -d codeanalysis -q 2>/dev/null; then
    echo -e "${GREEN}✅ Database accessible${NC}"
    
    # Check vector extension
    VECTOR_CHECK=$(docker-compose exec postgres psql -U analyzer -d codeanalysis -t -c "SELECT 1 FROM pg_extension WHERE extname = 'vector';" 2>/dev/null | tr -d ' ')
    if [ "$VECTOR_CHECK" = "1" ]; then
        echo -e "${GREEN}✅ pgvector extension installed${NC}"
    else
        echo -e "${RED}❌ pgvector extension missing${NC}"
    fi
    
    # Check embedding column
    EMBED_COLUMN=$(docker-compose exec postgres psql -U analyzer -d codeanalysis -t -c "
    SELECT udt_name FROM information_schema.columns 
    WHERE table_name = 'code_chunks' AND column_name = 'embedding';" 2>/dev/null | tr -d ' ')
    
    if [ "$EMBED_COLUMN" = "vector" ]; then
        echo -e "${GREEN}✅ Embedding column configured${NC}"
    else
        echo -e "${YELLOW}⚠️  Embedding column needs setup${NC}"
        echo "    Run: ./scripts/setup-lm-studio.sh"
    fi
else
    echo -e "${RED}❌ Database not accessible${NC}"
    echo "    Run: docker-compose up postgres -d"
fi

# Summary
echo -e "\n${BLUE}📋 Setup Summary:${NC}"
echo "========================"
echo "LM Studio Models to use in your .env:"
echo "  EMBEDDING_MODEL_NAME=text-embedding-all-minilm-l12-v2  (recommended)"
echo "  # or"
echo "  EMBEDDING_MODEL_NAME=text-embedding-gguf-multi-qa-minilm-l6-cos-v1"
echo ""
echo "Expected vector dimension: 384"
echo ""
echo "Ready to run enrichment? Use:"
echo "  docker-compose --profile enrichment up enricher"
