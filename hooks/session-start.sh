#!/bin/bash
# Cerberus MCP Session Startup Hook
# Auto-invokes Cerberus skill for optimal token efficiency
#
# Installation: Copy to your AI agent's hooks directory
# Examples:
#   cp hooks/session-start.sh ~/.claude/hooks/cerberus-startup.sh
#   cp hooks/session-start.sh ~/.codex/hooks/cerberus-startup.sh
#   cp hooks/session-start.sh ~/.aider/hooks/cerberus-startup.sh
#
# Make it executable: chmod +x ~/.*/hooks/cerberus-startup.sh

# Check if we're in a CODE project (not just general notes/brainstorming)
is_code_project() {
    # Version control = definite project
    [ -d ".git" ] || [ -d ".svn" ] || [ -d ".hg" ] || \
    # Language-specific project files
    [ -f "go.mod" ] || [ -f "package.json" ] || [ -f "Cargo.toml" ] || \
    [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "requirements.txt" ] || \
    [ -f "pom.xml" ] || [ -f "build.gradle" ] || [ -f "composer.json" ] || \
    [ -f "Gemfile" ] || [ -f "mix.exs" ] || [ -f "Makefile" ] || \
    # Cerberus index exists (has been indexed)
    [ -f ".cerberus/index.db" ] || [ -f ".cerberus/cerberus.db" ]
}

# Detect agent skills directory
detect_skills_dir() {
    # Check common agent skill locations
    for dir in ~/.claude/skills ~/.codex/skills ~/.aider/skills; do
        if [ -d "$dir/Cerberus" ]; then
            echo "$dir"
            return 0
        fi
    done
    return 1
}

# Check if Cerberus skill is installed
SKILLS_DIR=$(detect_skills_dir)

if [ -n "$SKILLS_DIR" ] && [ -f "$SKILLS_DIR/Cerberus/skill.md" ]; then
    # Skill exists - instruct agent to auto-invoke it
    if is_code_project; then
        echo "IMPORTANT: Invoke Cerberus skill immediately using Skill tool (skill=\"Cerberus\")"
        echo "Context: Project directory detected - full Cerberus toolset available"
    else
        echo "IMPORTANT: Invoke Cerberus skill immediately using Skill tool (skill=\"Cerberus\")"
        echo "Context: General directory - memory tools available, index tools will gracefully skip"
    fi
else
    # Skill not installed - provide fallback guidance
    if is_code_project; then
        echo "CERBERUS [project]: memory_context() recommended"
        echo "TIP: Install Cerberus skill for 95% token savings - see repo skill/ directory"
    else
        echo "CERBERUS [general]: Memory tools available"
        echo "TIP: Install Cerberus skill for full guidance - see repo skill/ directory"
    fi
fi
