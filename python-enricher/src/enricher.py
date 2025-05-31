#!/usr/bin/env python3
"""
Enhanced LLM Code Enricher Service with LM Studio Embeddings
Uses LM Studio for both LLM and embedding generation
"""

import os
import sys
import json
import time
import asyncio
import asyncpg
import httpx
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Add the src directory to the path so we can import config
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import EnricherConfig, PromptTemplates

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class CodeChunk:
    id: int
    function_id: int
    chunk_index: int
    chunk_type: str
    nesting_level: int
    code: str
    function_name: str
    class_name: Optional[str]
    filepath: str

@dataclass
class EnrichmentResult:
    summary: str
    complexity_score: float
    business_impact_score: float
    embedding: List[float]
    tags: List[str]

class LMStudioEnricher:
    def __init__(self):
        # Validate configuration
        EnricherConfig.validate()
        EnricherConfig.print_config()
        
        # HTTP client for both LLM and embedding requests
        self.http_client = httpx.AsyncClient(timeout=EnricherConfig.LLM_TIMEOUT)
        
        # LM Studio endpoints
        self.llm_endpoint = EnricherConfig.LLM_ENDPOINT
        self.embedding_endpoint = os.getenv('EMBEDDING_ENDPOINT', 
                                          'http://host.docker.internal:1234/v1/embeddings')
        
        # Embedding model configuration
        self.embedding_model_name = os.getenv('EMBEDDING_MODEL_NAME', 
                                            'text-embedding-all-minilm-l12-v2')
        
        # Determine embedding dimension based on model
        self.embedding_dimension = self._get_embedding_dimension()
        
        logger.info(f"🔧 LM Studio Configuration:")
        logger.info(f"   LLM Endpoint: {self.llm_endpoint}")
        logger.info(f"   Embedding Endpoint: {self.embedding_endpoint}")
        logger.info(f"   Embedding Model: {self.embedding_model_name}")
        logger.info(f"   Embedding Dimension: {self.embedding_dimension}")
    
    def _get_embedding_dimension(self) -> int:
        """Determine embedding dimension based on model name"""
        model_dimensions = {
            'text-embedding-gguf-multi-qa-minilm-l6-cos-v1': 384,
            'text-embedding-all-minilm-l12-v2': 384,
            'all-minilm-l6-v2': 384,
            'all-minilm-l12-v2': 384,
            'all-mpnet-base-v2': 768,
            'all-distilroberta-v1': 768
        }
        
        # Check if model name matches known models
        for model, dim in model_dimensions.items():
            if model in self.embedding_model_name.lower():
                return dim
        
        # Default fallback
        logger.warning(f"Unknown embedding model: {self.embedding_model_name}, assuming 384 dimensions")
        return 384
    
    async def test_connections(self):
        """Test both LLM and embedding endpoints"""
        logger.info("🔍 Testing LM Studio connections...")
        
        # Test LLM endpoint
        try:
            response = await self.http_client.get(f"{self.llm_endpoint.replace('/chat/completions', '/models')}")
            if response.status_code == 200:
                models = response.json()
                logger.info(f"✅ LLM endpoint accessible, found {len(models.get('data', []))} models")
            else:
                logger.warning(f"⚠️  LLM endpoint returned status {response.status_code}")
        except Exception as e:
            logger.error(f"❌ LLM endpoint test failed: {e}")
        
        # Test embedding endpoint
        try:
            test_payload = {
                "model": self.embedding_model_name,
                "input": "test embedding"
            }
            response = await self.http_client.post(
                self.embedding_endpoint,
                json=test_payload,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                result = response.json()
                embedding = result['data'][0]['embedding']
                actual_dim = len(embedding)
                logger.info(f"✅ Embedding endpoint accessible, dimension: {actual_dim}")
                
                # Update dimension if different
                if actual_dim != self.embedding_dimension:
                    logger.info(f"📏 Updating embedding dimension from {self.embedding_dimension} to {actual_dim}")
                    self.embedding_dimension = actual_dim
            else:
                logger.warning(f"⚠️  Embedding endpoint returned status {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"❌ Embedding endpoint test failed: {e}")
    
    async def connect_db(self) -> asyncpg.Connection:
        """Connect to PostgreSQL database"""
        try:
            conn = await asyncpg.connect(EnricherConfig.DATABASE_URL)
            logger.info("✅ Connected to database")
            return conn
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise

    async def get_pending_chunks(self, conn: asyncpg.Connection, limit: int = None) -> List[CodeChunk]:
        """Fetch code chunks that haven't been enriched yet"""
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        query = f"""
        SELECT 
            cc.id,
            cc.function_id,
            cc.chunk_index,
            cc.chunk_type,
            cc.nesting_level,
            cc.code,
            f.function_name,
            f.class_name,
            files.filepath
        FROM code_chunks cc
        JOIN functions f ON cc.function_id = f.id
        JOIN files ON f.file_id = files.id
        WHERE cc.enriched_at IS NULL
        ORDER BY cc.id
        {limit_clause}
        """
        
        rows = await conn.fetch(query)
        
        chunks = []
        for row in rows:
            chunks.append(CodeChunk(
                id=row['id'],
                function_id=row['function_id'],
                chunk_index=row['chunk_index'],
                chunk_type=row['chunk_type'],
                nesting_level=row['nesting_level'],
                code=row['code'][:EnricherConfig.MAX_CODE_LENGTH],
                function_name=row['function_name'],
                class_name=row['class_name'],
                filepath=row['filepath']
            ))
        
        return chunks

    async def call_llm(self, prompt: str, max_tokens: int = None) -> Optional[str]:
        """Call the LM Studio LLM endpoint"""
        if max_tokens is None:
            max_tokens = EnricherConfig.LLM_MAX_TOKENS
            
        payload = {
            "model": EnricherConfig.LLM_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a code analysis expert. Provide concise, accurate analysis."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": EnricherConfig.LLM_TEMPERATURE
        }
        
        for attempt in range(EnricherConfig.MAX_RETRIES):
            try:
                response = await self.http_client.post(
                    self.llm_endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content'].strip()
                else:
                    logger.warning(f"LLM request failed with status {response.status_code}: {response.text}")
                    
            except Exception as e:
                logger.warning(f"LLM request attempt {attempt + 1} failed: {e}")
                
            if attempt < EnricherConfig.MAX_RETRIES - 1:
                await asyncio.sleep(EnricherConfig.RETRY_DELAY * (attempt + 1))
        
        return None

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using LM Studio embedding endpoint"""
        if not EnricherConfig.ENABLE_EMBEDDINGS:
            return [0.0] * self.embedding_dimension
        
        try:
            # Truncate text if too long
            max_length = 8000  # LM Studio can handle longer texts
            if len(text) > max_length:
                text = text[:max_length] + "..."
            
            payload = {
                "model": self.embedding_model_name,
                "input": text
            }
            
            for attempt in range(EnricherConfig.MAX_RETRIES):
                try:
                    response = await self.http_client.post(
                        self.embedding_endpoint,
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        embedding = result['data'][0]['embedding']
                        
                        # Verify dimension
                        if len(embedding) != self.embedding_dimension:
                            logger.warning(f"Embedding dimension mismatch: expected {self.embedding_dimension}, got {len(embedding)}")
                            # Update our expected dimension
                            self.embedding_dimension = len(embedding)
                        
                        return embedding
                    else:
                        logger.warning(f"Embedding request failed with status {response.status_code}: {response.text}")
                        
                except Exception as e:
                    logger.warning(f"Embedding request attempt {attempt + 1} failed: {e}")
                    
                if attempt < EnricherConfig.MAX_RETRIES - 1:
                    await asyncio.sleep(EnricherConfig.RETRY_DELAY * (attempt + 1))
            
            # Return zero vector as fallback
            return [0.0] * self.embedding_dimension
        
        except Exception as e:
            logger.warning(f"❌ Failed to generate embedding: {e}")
            return [0.0] * self.embedding_dimension

    def get_context_string(self, chunk: CodeChunk) -> str:
        """Generate context string for prompts"""
        context = f"File: {chunk.filepath}"
        if chunk.class_name:
            context += f", Class: {chunk.class_name}"
        context += f", Function: {chunk.function_name}"
        return context

    async def generate_summary(self, chunk: CodeChunk) -> str:
        """Generate summary for a code chunk"""
        context = self.get_context_string(chunk)
        prompt = PromptTemplates.SUMMARY_TEMPLATE.format(
            context=context,
            chunk_type=chunk.chunk_type,
            nesting_level=chunk.nesting_level,
            code=chunk.code
        )
        
        summary = await self.call_llm(prompt, EnricherConfig.MAX_SUMMARY_LENGTH)
        
        if not summary:
            return f"Code chunk in {chunk.function_name} ({chunk.chunk_type})"
        
        return summary

    async def assess_complexity(self, chunk: CodeChunk) -> float:
        """Assess complexity score for a code chunk"""
        if not EnricherConfig.ENABLE_COMPLEXITY_SCORING:
            return 0.5
            
        prompt = PromptTemplates.COMPLEXITY_TEMPLATE.format(code=chunk.code)
        response = await self.call_llm(prompt, max_tokens=10)
        
        try:
            score = float(response) if response else 0.5
            return max(0.1, min(1.0, score))
        except (ValueError, TypeError):
            logger.warning(f"❌ Invalid complexity score for chunk {chunk.id}: {response}")
            return 0.5

    async def assess_business_impact(self, chunk: CodeChunk) -> float:
        """Assess business impact score for a code chunk"""
        if not EnricherConfig.ENABLE_BUSINESS_IMPACT:
            return 0.5
            
        context = self.get_context_string(chunk)
        prompt = PromptTemplates.BUSINESS_IMPACT_TEMPLATE.format(
            context=context,
            code=chunk.code
        )
        
        response = await self.call_llm(prompt, max_tokens=10)
        
        try:
            score = float(response) if response else 0.5
            return max(0.1, min(1.0, score))
        except (ValueError, TypeError):
            logger.warning(f"❌ Invalid business impact score for chunk {chunk.id}: {response}")
            return 0.5

    async def detect_tags(self, chunk: CodeChunk) -> List[str]:
        """Detect business/technical tags for a code chunk"""
        context = self.get_context_string(chunk)
        prompt = PromptTemplates.TAG_DETECTION_TEMPLATE.format(
            context=context,
            code=chunk.code
        )
        
        response = await self.call_llm(prompt, max_tokens=100)
        
        try:
            if response:
                # Clean up response - extract JSON from potentially verbose response
                cleaned_response = response.strip()
                
                # Look for JSON array in the response
                import re
                json_pattern = r'\[[\s\S]*?\]'
                json_match = re.search(json_pattern, cleaned_response)
                
                if json_match:
                    json_str = json_match.group(0)
                    tags = json.loads(json_str)
                    if isinstance(tags, list):
                        return [str(tag) for tag in tags]
                
                # Fallback: try to clean markdown and parse
                if cleaned_response.startswith('```json'):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.startswith('```'):
                    cleaned_response = cleaned_response[3:]
                if cleaned_response.endswith('```'):
                    cleaned_response = cleaned_response[:-3]
                
                # Find the first complete JSON array
                lines = cleaned_response.split('\n')
                json_lines = []
                in_array = False
                
                for line in lines:
                    if '[' in line:
                        in_array = True
                    if in_array:
                        json_lines.append(line)
                    if ']' in line and in_array:
                        break
                
                if json_lines:
                    json_str = '\n'.join(json_lines).strip()
                    tags = json.loads(json_str)
                    if isinstance(tags, list):
                        return [str(tag) for tag in tags]
                        
        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            # Don't log as warning anymore since the LLM is actually working well
            logger.debug(f"Could not parse tags for chunk {chunk.id}, LLM gave detailed response")
        
        return []

    async def enrich_chunk(self, chunk: CodeChunk) -> EnrichmentResult:
        """Enrich a single chunk with all analysis"""
        logger.info(f"🔄 Enriching chunk {chunk.id}: {chunk.filepath}::{chunk.function_name}")
        
        # Choose between comprehensive analysis (1 LLM call) or separate calls
        if EnricherConfig.USE_COMPREHENSIVE_ANALYSIS:
            # Single comprehensive analysis call
            analysis = await self.comprehensive_analysis(chunk)
            
            summary = analysis.get('summary', f"Code chunk in {chunk.function_name} ({chunk.chunk_type})")
            complexity_score = float(analysis.get('complexity_score', 0.5))
            business_impact_score = float(analysis.get('business_impact_score', 0.5))
            tags = analysis.get('tags', [])
            
        else:
            # Separate calls (current approach)
            summary = await self.generate_summary(chunk)
            
            # Generate all other enrichments concurrently
            tasks = []
            
            if EnricherConfig.ENABLE_COMPLEXITY_SCORING:
                tasks.append(self.assess_complexity(chunk))
            else:
                tasks.append(self._return_default_score(0.5))
            
            if EnricherConfig.ENABLE_BUSINESS_IMPACT:
                tasks.append(self.assess_business_impact(chunk))
            else:
                tasks.append(self._return_default_score(0.5))
            
            # Tags detection
            tasks.append(self.detect_tags(chunk))
            
            # Wait for LLM tasks
            results = await asyncio.gather(*tasks)
            complexity_score = results[0] if len(results) > 0 else 0.5
            business_impact_score = results[1] if len(results) > 1 else 0.5
            tags = results[2] if len(results) > 2 else []
        
        # Generate embedding from summary + code
        embed_text = f"{summary}\n\nCode: {chunk.code}"
        embedding = await self.generate_embedding(embed_text)
        
        logger.info(f"✅ Enriched chunk {chunk.id}: complexity={complexity_score:.2f}, impact={business_impact_score:.2f}, tags={len(tags)}, embedding_dim={len(embedding)}")
        
        return EnrichmentResult(
            summary=summary,
            complexity_score=complexity_score,
            business_impact_score=business_impact_score,
            embedding=embedding,
            tags=tags
        )
    
    async def _return_default_score(self, score: float) -> float:
        """Helper method for default scores"""
        return score

    async def update_chunk_enrichment(self, conn: asyncpg.Connection, chunk_id: int, 
                                    result: EnrichmentResult):
        """Update the database with enrichment results"""
        # Convert embedding list to pgvector format
        embedding_str = f"[{','.join(map(str, result.embedding))}]"
        
        query = """
        UPDATE code_chunks 
        SET summary = $1,
            complexity_score = $2,
            business_impact_score = $3,
            embedding = $4,
            enriched_at = NOW()
        WHERE id = $5
        """
        
        await conn.execute(query, 
                          result.summary, 
                          result.complexity_score, 
                          result.business_impact_score, 
                          embedding_str, 
                          chunk_id)

    async def process_chunks_batch(self, conn: asyncpg.Connection, chunks: List[CodeChunk]):
        """Process a batch of chunks"""
        logger.info(f"🔄 Processing batch of {len(chunks)} chunks")
        
        for chunk in chunks:
            try:
                result = await self.enrich_chunk(chunk)
                await self.update_chunk_enrichment(conn, chunk.id, result)
                
                # Delay to avoid overwhelming LM Studio
                if EnricherConfig.CHUNK_DELAY > 0:
                    await asyncio.sleep(EnricherConfig.CHUNK_DELAY)
                
            except Exception as e:
                logger.error(f"❌ Failed to process chunk {chunk.id}: {e}")
                continue

    async def get_enrichment_stats(self, conn: asyncpg.Connection) -> Dict:
        """Get statistics about enrichment progress"""
        stats_query = """
        SELECT 
            COUNT(*) as total_chunks,
            COUNT(enriched_at) as enriched_chunks,
            COUNT(*) - COUNT(enriched_at) as pending_chunks,
            ROUND(AVG(complexity_score)::numeric, 2) as avg_complexity,
            ROUND(AVG(business_impact_score)::numeric, 2) as avg_business_impact
        FROM code_chunks
        """
        
        row = await conn.fetchrow(stats_query)
        return dict(row)

    async def run(self):
        """Main enrichment loop"""
        logger.info("🚀 Starting LM Studio Enricher Service")
        
        # Test connections first
        await self.test_connections()
        
        conn = await self.connect_db()
        
        try:
            # Show initial stats
            stats = await self.get_enrichment_stats(conn)
            logger.info(f"📊 Initial stats: {stats['pending_chunks']} pending out of {stats['total_chunks']} total chunks")
            
            if stats['pending_chunks'] == 0:
                logger.info("✅ All chunks already enriched!")
                return
            
            # Process chunks in batches
            processed_total = 0
            start_time = time.time()
            
            while True:
                chunks = await self.get_pending_chunks(conn, EnricherConfig.BATCH_SIZE)
                
                if not chunks:
                    break
                
                await self.process_chunks_batch(conn, chunks)
                processed_total += len(chunks)
                
                elapsed = time.time() - start_time
                rate = processed_total / elapsed if elapsed > 0 else 0
                
                logger.info(f"📈 Processed {processed_total} chunks ({rate:.1f}/sec)")
                
                # Update stats
                stats = await self.get_enrichment_stats(conn)
                remaining = stats['pending_chunks']
                
                if remaining == 0:
                    break
                    
                logger.info(f"📊 {remaining} chunks remaining")
            
            # Final stats
            final_stats = await self.get_enrichment_stats(conn)
            elapsed = time.time() - start_time
            
            logger.info(f"🎉 Enrichment completed!")
            logger.info(f"📊 Final stats: {final_stats}")
            logger.info(f"⏱️  Total time: {elapsed:.1f}s, Rate: {processed_total/elapsed:.1f} chunks/sec")
            
        except Exception as e:
            logger.error(f"❌ Enrichment failed: {e}")
            raise
        finally:
            await conn.close()
            await self.http_client.aclose()

if __name__ == "__main__":
    enricher = LMStudioEnricher()
    asyncio.run(enricher.run())
