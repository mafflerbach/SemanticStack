#!/bin/bash
# setup.sh - Initialize the project structure

set -e

echo "🚀 Setting up PHP AST Dumper v2 project structure..."

# Create directory structure
mkdir -p {rust-parser,python-enricher/src,api/src,frontend/src,sql,code-corpus,models,output,scripts}

# Create placeholder Dockerfiles
cat > rust-parser/Dockerfile << 'EOF'
FROM rust:1.70

WORKDIR /app

# Copy Cargo files
COPY Cargo.toml Cargo.lock ./

# Install dependencies
RUN cargo fetch

# Copy source code
COPY src/ ./src/

# Build the application
RUN cargo build --release

# Install PostgreSQL client for healthchecks
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

CMD ["./target/release/php-ast-parser"]
EOF

cat > python-enricher/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import psycopg2; print('OK')" || exit 1

CMD ["python", "src/enricher.py"]
EOF

cat > api/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
EOF

cat > frontend/Dockerfile << 'EOF'
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Use npm install instead of npm ci to handle version conflicts
RUN npm install

# Copy source code
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
EOF

# Create placeholder requirements files
cat > python-enricher/requirements.txt << 'EOF'
psycopg2-binary==2.9.7
sentence-transformers==2.2.2
requests==2.31.0
numpy==1.24.3
torch==2.0.1
transformers==4.32.1
scikit-learn==1.3.0
EOF

cat > api/requirements.txt << 'EOF'
fastapi==0.103.1
uvicorn[standard]==0.23.2
psycopg2-binary==2.9.7
sentence-transformers==2.2.2
pydantic==2.3.0
python-multipart==0.0.6
numpy==1.24.3
torch==2.0.1
transformers==4.32.1
EOF

# Create basic frontend package.json
cat > frontend/package.json << 'EOF'
{
  "name": "codeanalysis-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@shoelace-style/shoelace": "^2.15.0"
  },
  "devDependencies": {
    "vite": "^4.4.9"
  }
}
EOF

# Create basic frontend files
cat > frontend/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Analysis Dashboard</title>
    <script type="module" src="https://cdn.jsdelivr.net/npm/@shoelace-style/shoelace@2.15.0/cdn/shoelace.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@shoelace-style/shoelace@2.15.0/cdn/themes/light.css" />
    <script type="module" src="/src/main.js"></script>
</head>
<body>
    <div id="app">
        <sl-card>
            <h1>🧠 Code Analysis Dashboard v2</h1>
            <p>PostgreSQL + Vector Search powered code intelligence</p>
        </sl-card>
    </div>
</body>
</html>
EOF

cat > frontend/src/main.js << 'EOF'
console.log('Code Analysis Dashboard v2 loading...');

// Basic API configuration
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard ready!');
});
EOF

cat > frontend/vite.config.js << 'EOF'
import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    host: '0.0.0.0',
    port: 5173
  }
})
EOF

# Create placeholder Rust Cargo.toml
cat > rust-parser/Cargo.toml << 'EOF'
[package]
name = "php-ast-parser"
version = "0.2.0"
edition = "2021"

[dependencies]
anyhow = "1.0"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
tree-sitter = "0.20"
tree-sitter-php = "0.21"
walkdir = "2.3"
rayon = "1.7"
tokio = { version = "1.0", features = ["full"] }
tokio-postgres = { version = "0.7", features = ["with-serde_json-1"] }
EOF

# Create .env file for local development
cat > .env << 'EOF'
# Database Configuration
DATABASE_URL=postgresql://analyzer:secure_password_change_me@localhost:5432/codeanalysis

# LLM Configuration (LM Studio running on Mac host)
LLM_ENDPOINT=http://host.docker.internal:1234/v1/chat/completions

# Model Paths
EMBED_MODEL_PATH=./models

# API Configuration  
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Processing Configuration
BATCH_SIZE=50
RUST_LOG=info
PYTHONUNBUFFERED=1
EOF

# Create .gitignore
cat > .gitignore << 'EOF'
# Environment files
.env
.env.local

# Database
postgres_data/
redis_data/
pgadmin_data/

# Models (too large for git)
models/
*.bin
*.safetensors

# Output files
output/
*.json

# Code corpus (project specific)
code-corpus/

# Dependencies
node_modules/
target/
__pycache__/
*.pyc
.pytest_cache/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
model_raw_output.log

# Build artifacts
dist/
build/
EOF

# Create development helper scripts
cat > scripts/dev.sh << 'EOF'
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
EOF

cat > scripts/prod.sh << 'EOF'
#!/bin/bash
# Production environment startup

echo "🚀 Starting production environment..."

# Start all services except development tools
docker-compose --profile production up -d

echo "✅ Production environment ready!"
echo "🌐 API: http://localhost:8000"
echo "💻 Frontend: http://localhost:5173"
EOF

cat > scripts/reset.sh << 'EOF'
#!/bin/bash
# Reset everything - useful during development

echo "🧹 Resetting environment..."

docker-compose down -v
docker-compose build
docker system prune -f

echo "✅ Environment reset complete!"
EOF

chmod +x scripts/*.sh

echo "✅ Project structure created!"
echo ""
echo "Next steps:"
echo "1. Copy your existing code:"
echo "   - Rust parser code → rust-parser/src/"
echo "   - Python enricher → python-enricher/src/"
echo "   - Your models → models/"
echo "   - Test PHP code → code-corpus/"
echo ""
echo "2. Start development environment:"
echo "   ./scripts/dev.sh"
echo ""
echo "3. Start full system:"
echo "   docker-compose up"
echo ""
echo "📊 PgAdmin will be at: http://localhost:8080"
echo "🌐 API will be at: http://localhost:8000"
echo "💻 Frontend will be at: http://localhost:5173"
EOF
