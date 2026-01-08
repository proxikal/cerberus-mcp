"""
Configuration for code summarization using local LLMs.
"""

# LLM backend configuration
LLM_CONFIG = {
    "backend": "ollama",  # "ollama", "llamacpp", "api", or "none"
    "model": "llama2:7b",  # Model identifier
    "temperature": 0.2,  # Lower = more deterministic
    "max_tokens": 500,  # Maximum tokens in response
    "timeout": 30,  # Request timeout in seconds
    "api_base": "http://localhost:11434",  # Ollama default endpoint
}

# Summarization behavior configuration
SUMMARIZATION_CONFIG = {
    "chunk_size": 2000,  # Lines to summarize at once
    "min_lines_for_summary": 50,  # Don't summarize small files
    "include_complexity_score": True,
    "include_key_points": True,
    "max_key_points": 5,
    "include_dependencies": True,
}

# Prompt templates for different summary types
PROMPT_TEMPLATES = {
    "file": """Analyze the following source code file and provide a concise summary.

File: {file_path}
Language: {language}

Code:
{code_content}

Provide:
1. Primary purpose (1-2 sentences)
2. Key functions/classes (up to 5 bullet points)
3. Major dependencies (libraries, frameworks)
4. Complexity assessment (1-10, where 10 is most complex)

Format your response as:
PURPOSE: <text>
KEY_POINTS:
- <point 1>
- <point 2>
...
DEPENDENCIES: <comma-separated list>
COMPLEXITY: <number>
""",

    "symbol": """Analyze the following code symbol and explain what it does.

Symbol: {symbol_name}
Type: {symbol_type}
File: {file_path}

Code:
{code_content}

Provide:
1. What this {symbol_type} does (1-2 sentences)
2. Key functionality (up to 3 bullet points)
3. Dependencies used
4. Complexity (1-10)

FORMAT:
PURPOSE: <text>
KEY_POINTS:
- <point>
DEPENDENCIES: <list>
COMPLEXITY: <number>
""",

    "architecture": """Analyze the following code architecture/subsystem and describe it.

Subsystem: {target}
Files: {file_count}

Code Overview:
{code_content}

Provide:
1. Overall purpose of this subsystem (2-3 sentences)
2. Main components and their roles (up to 5 bullet points)
3. Key dependencies and integrations
4. Overall complexity assessment (1-10)

FORMAT:
PURPOSE: <text>
KEY_POINTS:
- <component>: <role>
DEPENDENCIES: <list>
COMPLEXITY: <number>
""",

    "layer": """Analyze the following architectural layer and describe its purpose.

Layer: {target}
Files: {file_count}

Code:
{code_content}

Provide:
1. Purpose of this layer (2-3 sentences)
2. Main responsibilities (up to 5 bullet points)
3. Dependencies (what it relies on)
4. Complexity (1-10)

FORMAT:
PURPOSE: <text>
KEY_POINTS:
- <responsibility>
DEPENDENCIES: <list>
COMPLEXITY: <number>
"""
}

# Response parsing patterns
RESPONSE_PATTERNS = {
    "purpose": r"PURPOSE:\s*(.+?)(?=\n(?:KEY_POINTS|DEPENDENCIES|COMPLEXITY|$))",
    "key_points": r"KEY_POINTS:\s*\n((?:[-•]\s*.+\n?)+)",
    "dependencies": r"DEPENDENCIES:\s*(.+?)(?=\n(?:COMPLEXITY|$))",
    "complexity": r"COMPLEXITY:\s*(\d+)"
}
