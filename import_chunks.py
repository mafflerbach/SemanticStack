#!/usr/bin/env python3
import json
import psycopg2
from datetime import datetime

# Database connection
conn = psycopg2.connect(
    host="localhost",
    port="5432", 
    database="codeanalysis",
    user="analyzer",
    password="secure_password_change_me"
)
cursor = conn.cursor()

# Load JSON data
print("Loading chunks.json...")
with open('output/chunks.json', 'r') as f:
    chunks = json.load(f)

print(f"Found {len(chunks)} chunks to import")

# Group chunks by function
functions = {}
for chunk in chunks:
    func_key = (chunk['filename'], chunk['function'])
    if func_key not in functions:
        functions[func_key] = {
            'filename': chunk['filename'],
            'function': chunk['function'],
            'namespace': chunk['namespace'],
            'class': chunk['class'],
            'visibility': chunk['visibility'],
            'is_static': chunk['is_static'],
            'return_type': chunk['return_type'],
            'params': chunk['params'],
            'start_line': chunk['start_line'],
            'end_line': chunk['end_line'],
            'chunks': []
        }
    functions[func_key]['chunks'].append(chunk)

print(f"Found {len(functions)} unique functions")

# Insert functions and chunks
for func_key, func_data in functions.items():
    # Insert function
    cursor.execute("""
        INSERT INTO functions 
        (filename, function_name, namespace, class_name, visibility, 
         is_static, return_type, parameters, start_line, end_line)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (filename, function_name) 
        DO UPDATE SET 
            end_line = EXCLUDED.end_line,
            parameters = EXCLUDED.parameters
        RETURNING id
    """, (
        func_data['filename'],
        func_data['function'],
        func_data['namespace'],
        func_data['class'],
        func_data['visibility'],
        func_data['is_static'],
        func_data['return_type'],
        json.dumps(func_data['params']),
        func_data['start_line'],
        func_data['end_line']
    ))
    
    function_id = cursor.fetchone()[0]
    
    # Insert chunks for this function
    for chunk in func_data['chunks']:
        cursor.execute("""
            INSERT INTO code_chunks 
            (function_id, chunk_index, start_byte, end_byte, code)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (function_id, chunk_index) 
            DO UPDATE SET 
                code = EXCLUDED.code,
                start_byte = EXCLUDED.start_byte,
                end_byte = EXCLUDED.end_byte
        """, (
            function_id,
            chunk['chunk_index'],
            chunk['start_byte'],
            chunk['end_byte'],
            chunk['code']
        ))
    
    print(f"✅ Imported {func_data['function']} ({len(func_data['chunks'])} chunks)")

conn.commit()
print(f"🎉 Successfully imported {len(chunks)} chunks from {len(functions)} functions!")

# Quick stats
cursor.execute("SELECT COUNT(*) FROM functions")
func_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM code_chunks")
chunk_count = cursor.fetchone()[0]

print(f"📊 Database now has {func_count} functions and {chunk_count} chunks")

cursor.close()
conn.close()
