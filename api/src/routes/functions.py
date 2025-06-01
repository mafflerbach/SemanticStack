from fastapi import APIRouter
import asyncpg
import os
import psycopg2

router = APIRouter()

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://analyzer:secure_password_change_me@postgres:5432/codeanalysis')

def get_db():
    """Synchronous database connection"""
    return psycopg2.connect(os.getenv("DATABASE_URL"))

async def get_async_db():
    """Asynchronous database connection"""
    return await asyncpg.connect(DATABASE_URL)
