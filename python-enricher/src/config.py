"""
Configuration for the LLM Enricher Service
Simple text prompts - no JSON schema parsing
"""

import os
from typing import Dict, Any

class EnricherConfig:
    """Configuration settings for the enricher"""
    
    # Database settings
    DATABASE_URL = os.getenv('DATABASE_URL', 
                            'postgresql://analyzer:secure_password_change_me@postgres:5432/codeanalysis')
    
    # LLM settings
    LLM_ENDPOINT = os.getenv('LLM_ENDPOINT', 
                            'http://host.docker.internal:1234/v1/chat/completions')
    LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-3.5-turbo')
    LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.2'))
    LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', '100'))      # Much smaller for simple responses
    LLM_TIMEOUT = int(os.getenv('LLM_TIMEOUT', '60'))
    
    # LM Studio Embedding settings
    EMBEDDING_ENDPOINT = os.getenv('EMBEDDING_ENDPOINT', 
                                  'http://host.docker.internal:1234/v1/embeddings')
    EMBEDDING_MODEL_NAME = os.getenv('EMBEDDING_MODEL_NAME', 
                                   'text-embedding-all-minilm-l12-v2')
    
    # Processing settings
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', '20'))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', '2'))
    CHUNK_DELAY = float(os.getenv('CHUNK_DELAY', '0.5'))
    
    # Embedding settings
    EMBED_MODEL_PATH = os.getenv('EMBED_MODEL_PATH', '/app/models')
    EMBED_MODEL_NAME = os.getenv('EMBED_MODEL_NAME', 'text-embedding-all-minilm-l12-v2')
    EMBED_DIMENSION = int(os.getenv('EMBED_DIMENSION', '384'))
    
    # Feature flags
    ENABLE_EMBEDDINGS = os.getenv('ENABLE_EMBEDDINGS', 'true').lower() == 'true'
    ENABLE_COMPLEXITY_SCORING = os.getenv('ENABLE_COMPLEXITY_SCORING', 'true').lower() == 'true'
    ENABLE_BUSINESS_IMPACT = os.getenv('ENABLE_BUSINESS_IMPACT', 'true').lower() == 'true'
    USE_COMPREHENSIVE_ANALYSIS = os.getenv('USE_COMPREHENSIVE_ANALYSIS', 'false').lower() == 'true'
    
    # Advanced settings
    MAX_CODE_LENGTH = int(os.getenv('MAX_CODE_LENGTH', '2000'))
    MAX_SUMMARY_LENGTH = int(os.getenv('MAX_SUMMARY_LENGTH', '500'))  # Reduced for simple prompts
    
    @classmethod
    def get_llm_payload_template(cls) -> Dict[str, Any]:
        """Get base LLM request payload"""
        return {
            "model": cls.LLM_MODEL,
            "temperature": cls.LLM_TEMPERATURE,
            "max_tokens": cls.LLM_MAX_TOKENS
        }
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        errors = []
        
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is required")
        
        if not cls.LLM_ENDPOINT:
            errors.append("LLM_ENDPOINT is required")
        
        if cls.BATCH_SIZE <= 0:
            errors.append("BATCH_SIZE must be positive")
        
        if cls.MAX_RETRIES < 0:
            errors.append("MAX_RETRIES must be non-negative")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    @classmethod
    def print_config(cls):
        """Print current configuration (hiding sensitive data)"""
        print("🔧 Enricher Configuration:")
        print(f"  Database: {cls.DATABASE_URL.split('@')[-1] if '@' in cls.DATABASE_URL else cls.DATABASE_URL}")
        print(f"  LLM Endpoint: {cls.LLM_ENDPOINT}")
        print(f"  LLM Model: {cls.LLM_MODEL}")
        print(f"  LLM Temperature: {cls.LLM_TEMPERATURE}")
        print(f"  LLM Max Tokens: {cls.LLM_MAX_TOKENS}")
        print(f"  Embedding Endpoint: {cls.EMBEDDING_ENDPOINT}")
        print(f"  Embedding Model: {cls.EMBEDDING_MODEL_NAME}")
        print(f"  Embedding Dimension: {cls.EMBED_DIMENSION}")
        print(f"  Batch Size: {cls.BATCH_SIZE}")
        print(f"  Features: Embeddings={cls.ENABLE_EMBEDDINGS}, Complexity={cls.ENABLE_COMPLEXITY_SCORING}, Business={cls.ENABLE_BUSINESS_IMPACT}")


# Simple text prompts - no JSON, no complex parsing
class PromptTemplates:
    """Super simple text prompts that just work"""
    
    # Minimal system prompt
    SYSTEM_PROMPT = """You are a helpful code analysis assistant."""
    
    # Simple summary prompt
    SUMMARY_TEMPLATE = """You're a senior PHP developer reviewing code for clarity and documentation.

Summarize the **intent and effect** of the following code in **1-2 clear, technical sentences**.
Use the context and code type to guide your phrasing and level of detail.

Context: {context}
Chunk Type: {chunk_type}

```php
{code}
```

Summary:"""

    # Super simple complexity - just ask for a number
    COMPLEXITY_TEMPLATE = """Rate this PHP code complexity from 0.1 to 1.0 (0.1=very simple, 1.0=very complex).
Respond with ONLY the number.

```php
{code}
```

Complexity score:"""

    # Simple business impact - just ask for a number
    BUSINESS_IMPACT_TEMPLATE = """Rate the business criticality of this PHP code from 0.1 to 1.0 (0.1=low impact, 1.0=mission critical).
Respond with ONLY the number.

Context: {context}
```php
{code}
```

Business impact score:"""

    # Simple tags - just ask for a comma-separated list
    TAG_DETECTION_TEMPLATE = """List 1-3 relevant tags for this PHP code. Choose from:
authentication, payment, user-management, reporting, integration, data-processing, validation, notification, api-endpoint, security-sensitive, performance-critical, legacy-code, external-dependency, error-prone

Context: {context}
```php
{code}
```

Tags (comma separated):"""

    # Optional: Simple comprehensive analysis
    COMPREHENSIVE_ANALYSIS_TEMPLATE = """Analyze this PHP code:

Context: {context}
Type: {chunk_type}

```php
{code}
```

Please provide:
1. Summary (1-2 sentences):
2. Complexity (0.1-1.0):
3. Business impact (0.1-1.0):
4. Tags (comma separated):"""
