#!/bin/bash
# Publish Cerberus wiki content to GitHub wiki

set -e

WIKI_REPO="https://github.com/proxikal/cerberus-mcp.wiki.git"
WIKI_DIR="cerberus-mcp.wiki"

echo "Publishing Cerberus wiki..."

# Check if wiki content exists
if [ ! -d "wiki-content" ]; then
    echo "Error: wiki-content directory not found"
    exit 1
fi

# Clone wiki repo (or use existing)
if [ -d "$WIKI_DIR" ]; then
    echo "Using existing wiki directory..."
    cd "$WIKI_DIR"
    git pull
else
    echo "Cloning wiki repository..."
    git clone "$WIKI_REPO" "$WIKI_DIR"
    cd "$WIKI_DIR"
fi

# Copy wiki content
echo "Copying wiki pages..."
cp ../wiki-content/*.md .

# Commit and push
echo "Committing changes..."
git add *.md
git commit -m "Update comprehensive Cerberus documentation

- Complete MCP tools reference (all 51 tools)
- Installation guide for all components
- Quick start tutorial
- Token efficiency deep dive
- Context-aware operation explained
- FAQ and troubleshooting
- Session memory guide"

echo "Pushing to GitHub..."
git push

echo "✓ Wiki published successfully!"
echo "View at: https://github.com/proxikal/cerberus-mcp/wiki"

cd ..
