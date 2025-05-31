use anyhow::Result;
use serde::Serialize;
use std::{path::PathBuf, env, fs};
use tree_sitter::{Parser, Node};
use tree_sitter_php as php;
use walkdir::WalkDir;
use tokio_postgres::{NoTls, Client};
use sha2::{Sha256, Digest};
use serde_json::Value as JsonValue;

#[derive(Serialize, Clone)]
struct Parameter {
    name: String,
    default: Option<String>,
}

#[derive(Clone)]
struct FileData {
    filepath: String,
    file_hash: String,
    file_size: i32,
    lines_of_code: i32,
    functions: Vec<FunctionData>,
}

#[derive(Clone)]
struct FunctionData {
    function_name: String,
    namespace: Option<String>,
    class_name: Option<String>,
    visibility: Option<String>,
    is_static: bool,
    is_abstract: bool,
    is_final: bool,
    return_type: Option<String>,
    params: Vec<Parameter>,
    start_line: i32,
    end_line: i32,
    start_byte: i32,
    end_byte: i32,
    cyclomatic_complexity: i32,
    parameter_count: i32,
    lines_of_code: i32,
    chunks: Vec<ChunkData>,
}

#[derive(Clone)]
struct ChunkData {
    chunk_index: i32,
    chunk_type: String,
    nesting_level: i32,
    start_byte: i32,
    end_byte: i32,
    start_line: i32,
    end_line: i32,
    code: String,
    code_hash: String,
}

struct DatabaseWriter {
    client: Client,
}

impl DatabaseWriter {
    async fn connect() -> Result<Self> {
        let database_url = env::var("DATABASE_URL")
            .unwrap_or_else(|_| "postgresql://analyzer:secure_password_change_me@postgres:5432/codeanalysis".to_string());
        
        let (client, connection) = tokio_postgres::connect(&database_url, NoTls).await?;
        
        tokio::spawn(async move {
            if let Err(e) = connection.await {
                eprintln!("Database connection error: {}", e);
            }
        });
        
        Ok(DatabaseWriter { client })
    }
    
    async fn insert_file_with_functions(&mut self, file_data: &FileData) -> Result<()> {
        let transaction = self.client.transaction().await?;
        
        // Insert file record
        let file_id: i32 = transaction.query_one(
            "INSERT INTO files 
             (filepath, file_hash, file_size, lines_of_code, language, parsed_at)
             VALUES ($1, $2, $3, $4, $5, NOW())
             ON CONFLICT (filepath) 
             DO UPDATE SET 
                file_hash = EXCLUDED.file_hash,
                file_size = EXCLUDED.file_size,
                lines_of_code = EXCLUDED.lines_of_code,
                parsed_at = NOW()
             RETURNING id",
            &[
                &file_data.filepath,
                &file_data.file_hash,
                &file_data.file_size,
                &file_data.lines_of_code,
                &"php",
            ],
        ).await?.get(0);
        
        // Insert functions for this file
        for func_data in &file_data.functions {
            let params_json: JsonValue = serde_json::to_value(&func_data.params)?;
            
            let function_id: i32 = transaction.query_one(
                "INSERT INTO functions 
                 (file_id, function_name, namespace, class_name, visibility, 
                  is_static, is_abstract, is_final, return_type, parameters,
                  start_line, end_line, start_byte, end_byte,
                  cyclomatic_complexity, parameter_count, lines_of_code)
                 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                 ON CONFLICT (file_id, function_name) 
                 DO UPDATE SET 
                    namespace = EXCLUDED.namespace,
                    class_name = EXCLUDED.class_name,
                    visibility = EXCLUDED.visibility,
                    parameters = EXCLUDED.parameters,
                    cyclomatic_complexity = EXCLUDED.cyclomatic_complexity,
                    updated_at = NOW()
                 RETURNING id",
                &[
                    &file_id,
                    &func_data.function_name,
                    &func_data.namespace,
                    &func_data.class_name,
                    &func_data.visibility,
                    &func_data.is_static,
                    &func_data.is_abstract,
                    &func_data.is_final,
                    &func_data.return_type,
                    &params_json,
                    &func_data.start_line,
                    &func_data.end_line,
                    &func_data.start_byte,
                    &func_data.end_byte,
                    &func_data.cyclomatic_complexity,
                    &func_data.parameter_count,
                    &func_data.lines_of_code,
                ],
            ).await?.get(0);
            
            // Delete existing chunks for this function
            transaction.execute(
                "DELETE FROM code_chunks WHERE function_id = $1",
                &[&function_id],
            ).await?;
            
            // Insert chunks for this function
            for chunk in &func_data.chunks {
                transaction.execute(
                    "INSERT INTO code_chunks 
                     (function_id, chunk_index, chunk_type, nesting_level,
                      start_byte, end_byte, start_line, end_line, code, code_hash)
                     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)",
                    &[
                        &function_id,
                        &chunk.chunk_index,
                        &chunk.chunk_type,
                        &chunk.nesting_level,
                        &chunk.start_byte,
                        &chunk.end_byte,
                        &chunk.start_line,
                        &chunk.end_line,
                        &chunk.code,
                        &chunk.code_hash,
                    ],
                ).await?;
            }
            
            println!("✅ Stored function: {}::{} (complexity:{}, {} chunks)", 
                     file_data.filepath, func_data.function_name, func_data.cyclomatic_complexity, func_data.chunks.len());
        }
        
        transaction.commit().await?;
        Ok(())
    }
}

fn calculate_file_hash(content: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(content);
    format!("{:x}", hasher.finalize())
}

fn count_lines(content: &[u8]) -> i32 {
    content.iter().filter(|&&b| b == b'\n').count() as i32 + 1
}

fn detect_chunk_type(node: Node) -> String {
    match node.kind() {
        "if_statement" => "if".to_string(),
        "elseif_clause" => "elseif".to_string(),
        "else_clause" => "else".to_string(),
        "for_statement" => "for".to_string(),
        "foreach_statement" => "foreach".to_string(),
        "while_statement" => "while".to_string(),
        "do_statement" => "do".to_string(),
        "switch_statement" => "switch".to_string(),
        "case_block" | "switch_case" => "case".to_string(),
        "try_statement" => "try".to_string(),
        "catch_clause" => "catch".to_string(),
        "finally_clause" => "finally".to_string(),
        "compound_statement" => "block".to_string(),
        _ => "main".to_string(),
    }
}

fn calculate_nesting_level(node: Node, root: Node) -> i32 {
    let mut level = 0;
    let mut current = node;
    
    while let Some(parent) = current.parent() {
        if parent == root {
            break;
        }
        match parent.kind() {
            "if_statement" | "elseif_clause" | "else_clause" | "foreach_statement" | 
            "for_statement" | "while_statement" | "do_statement" |
            "switch_statement" | "try_statement" | "catch_clause" => {
                level += 1;
            }
            _ => {}
        }
        current = parent;
    }
    
    level
}

// FIXED: Proper cyclomatic complexity calculation
fn calculate_cyclomatic_complexity(node: Node) -> i32 {
    let mut complexity = 1; // Base complexity
    
    fn count_decision_points(node: Node) -> i32 {
        let mut count = 0;
        let mut cursor = node.walk();
        
        // Count decision points in current node
        match node.kind() {
            "if_statement" | "elseif_clause" | "case_block" | "foreach_statement" |
            "for_statement" | "while_statement" | "do_statement" |
            "catch_clause" | "conditional_expression" | "switch_case" |
            "ternary_expression" => {
                count += 1;
            }
            _ => {}
        }
        
        // Recursively count in all children
        for child in node.children(&mut cursor) {
            count += count_decision_points(child);
        }
        
        count
    }
    
    complexity + count_decision_points(node)
}

#[tokio::main]
async fn main() -> Result<()> {
    let src_dir = PathBuf::from("/workspace/code");
    
    println!("🔄 Connecting to database...");
    let mut db_writer = DatabaseWriter::connect().await?;
    println!("✅ Database connected");

    println!("🔍 Looking for PHP files in: {:?}", &src_dir);

    let files: Vec<PathBuf> = WalkDir::new(&src_dir)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| {
            e.path().is_file()
            && e.path().extension().and_then(|s| s.to_str()) == Some("php")
        })
        .map(|e| e.into_path())
        .collect();

    println!("📁 Found {} PHP files", files.len());

    let mut total_functions = 0;
    let mut total_chunks = 0;
    
    for path in &files {
        match process_file(path).await {
            Ok(file_data) => {
                total_functions += file_data.functions.len();
                total_chunks += file_data.functions.iter().map(|f| f.chunks.len()).sum::<usize>();
                db_writer.insert_file_with_functions(&file_data).await?;
                println!("📄 Processed: {} ({} functions)", file_data.filepath, file_data.functions.len());
            },
            Err(e) => {
                eprintln!("❌ Failed {}: {}", path.display(), e);
            }
        }
    }

    println!("🎉 Successfully processed {} functions with {} chunks", total_functions, total_chunks);
    Ok(())
}

async fn process_file(path: &PathBuf) -> Result<FileData> {
    let code = fs::read(path)?;
    let mut parser = Parser::new();
    parser.set_language(php::language())?;
    let tree = parser.parse(&code, None)
        .ok_or_else(|| anyhow::anyhow!("Parse failed for {}", path.display()))?;
    let root = tree.root_node();

    let rel_path = path.strip_prefix("/workspace/code")
        .unwrap_or(path)
        .to_string_lossy()
        .to_string();
    
    let file_hash = calculate_file_hash(&code);
    let file_size = code.len() as i32;
    let lines_of_code = count_lines(&code);
    
    let mut functions = Vec::new();

    for func_node in find_nodes_by_kind(root, &["function_definition", "method_declaration"]) {
        let func_name = extract_function_name(func_node, &code)
                            .unwrap_or_else(|| "<anonymous>".to_string());
        let visibility = extract_visibility(func_node, &code);
        let is_static = has_modifier(func_node, &code, "static");
        let is_abstract = has_modifier(func_node, &code, "abstract");
        let is_final = has_modifier(func_node, &code, "final");
        let return_type = extract_return_type(func_node, &code);
        let params = extract_parameters(func_node, &code);
        let parameter_count = params.len() as i32;

        let func_start_line = func_node.start_position().row as i32 + 1;
        let func_end_line = func_node.end_position().row as i32 + 1;
        let func_start_byte = func_node.start_byte() as i32;
        let func_end_byte = func_node.end_byte() as i32;
        let func_lines_of_code = func_end_line - func_start_line + 1;
        
        // FIXED: Calculate complexity on the entire function node
        let cyclomatic_complexity = calculate_cyclomatic_complexity(func_node);

        let mut method_cursor = func_node.walk();
        let body_opt = func_node
            .children(&mut method_cursor)
            .find(|c| c.kind() == "compound_statement");
        
        let mut chunks = Vec::new();
        
        if let Some(body) = body_opt {
            let start = body.start_byte() as usize;
            let end = body.end_byte() as usize;

            let mut spans = vec![(start, end, body, "main".to_string())];
            spans.extend(collect_nested_spans_with_types(body));

            spans.sort_by_key(|(s, _, _, _)| *s);
            
            let mut unique_spans = Vec::new();
            for span in spans {
                if !unique_spans.iter().any(|(s, e, _, _)| *s == span.0 && *e == span.1) {
                    unique_spans.push(span);
                }
            }

            for (i, (s, e, node, chunk_type)) in unique_spans.into_iter().enumerate() {
                let snippet = String::from_utf8_lossy(&code[s..e]).to_string();
                if snippet.trim().is_empty() { continue; }
                
                let nesting_level = calculate_nesting_level(node, body);
                let code_hash = calculate_file_hash(snippet.as_bytes());
                
                chunks.push(ChunkData {
                    chunk_index: i as i32,
                    chunk_type,
                    nesting_level,
                    start_byte: s as i32,
                    end_byte: e as i32,
                    start_line: node.start_position().row as i32 + 1,
                    end_line: node.end_position().row as i32 + 1,
                    code: snippet,
                    code_hash,
                });
            }
        }

        if !chunks.is_empty() {
            functions.push(FunctionData {
                function_name: func_name,
                namespace: None,
                class_name: None,
                visibility,
                is_static,
                is_abstract,
                is_final,
                return_type,
                params,
                start_line: func_start_line,
                end_line: func_end_line,
                start_byte: func_start_byte,
                end_byte: func_end_byte,
                cyclomatic_complexity,
                parameter_count,
                lines_of_code: func_lines_of_code,
                chunks,
            });
        }
    }

    Ok(FileData {
        filepath: rel_path,
        file_hash,
        file_size,
        lines_of_code,
        functions,
    })
}

fn collect_nested_spans_with_types(node: Node) -> Vec<(usize, usize, Node, String)> {
    let mut spans = Vec::new();
    let mut cur = node.walk();
    
    for child in node.named_children(&mut cur) {
        let chunk_type = detect_chunk_type(child);
        match child.kind() {
            "if_statement" | "elseif_clause" | "else_clause" | "foreach_statement" | 
            "switch_statement" | "case_block" | "switch_case" |
            "for_statement" | "while_statement" | "do_statement" |
            "compound_statement" | "try_statement" | "catch_clause" |
            "finally_clause" => {
                spans.push((
                    child.start_byte() as usize,
                    child.end_byte() as usize,
                    child,
                    chunk_type,
                ));
                spans.extend(collect_nested_spans_with_types(child));
            }
            _ => {}
        }
    }
    spans
}

fn find_nodes_by_kind<'a>(root: Node<'a>, kinds: &[&str]) -> Vec<Node<'a>> {
    let mut results = Vec::new();
    let mut stack = vec![root];
    while let Some(node) = stack.pop() {
        if kinds.contains(&node.kind()) {
            results.push(node);
        }
        let mut cur = node.walk();
        for child in node.children(&mut cur) {
            stack.push(child);
        }
    }
    results
}

fn extract_function_name<'a>(node: Node<'a>, source: &[u8]) -> Option<String> {
    node.child_by_field_name("name")
        .and_then(|n| n.utf8_text(source).ok())
        .map(|s| s.to_string())
}

fn extract_visibility<'a>(node: Node<'a>, source: &[u8]) -> Option<String> {
    let mut cur = node.walk();
    for child in node.children(&mut cur) {
        match child.kind() {
            "public" | "protected" | "private" => {
                return child.utf8_text(source).ok().map(|s| s.to_string())
            }
            _ => {}
        }
    }
    None
}

fn has_modifier<'a>(node: Node<'a>, _source: &[u8], modifier: &str) -> bool {
    let mut cur = node.walk();
    for child in node.children(&mut cur) {
        if child.kind() == modifier {
            return true;
        }
    }
    false
}

fn extract_return_type<'a>(node: Node<'a>, source: &[u8]) -> Option<String> {
    node.child_by_field_name("return_type")
        .and_then(|n| n.utf8_text(source).ok())
        .map(|s| s.trim_start_matches(':').trim().to_string())
}

fn extract_parameters<'a>(node: Node<'a>, source: &[u8]) -> Vec<Parameter> {
    let mut params = Vec::new();
    let mut cur = node.walk();
    if let Some(list) = node
        .children(&mut cur)
        .find(|n| n.kind().ends_with("parameters"))
    {
        let mut inner = list.walk();
        for p in list.named_children(&mut inner) {
            if p.kind().ends_with("parameter") {
                if let Ok(text) = p.utf8_text(source) {
                    let parts: Vec<&str> = text.splitn(2, '=').map(str::trim).collect();
                    let name = parts[0].to_string();
                    let default = parts.get(1).map(|d| d.to_string());
                    params.push(Parameter { name, default });
                }
            }
        }
    }
    params
}
