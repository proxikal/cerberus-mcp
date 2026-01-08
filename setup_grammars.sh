#!/bin/bash
set -e

# This script clones the necessary tree-sitter grammars and compiles them
# into a single shared library for Cerberus to use.

VENDOR_DIR="vendor"
GRAMMAR_DIR="$VENDOR_DIR/grammars"
BUILD_DIR="build"
LIBRARY_PATH="$BUILD_DIR/languages.so"

# Create directories
mkdir -p "$GRAMMAR_DIR"
mkdir -p "$BUILD_DIR"

echo "--- Cloning tree-sitter grammars ---"
# Python
if [ ! -d "$GRAMMAR_DIR/tree-sitter-python" ]; then
    git clone https://github.com/tree-sitter/tree-sitter-python.git "$GRAMMAR_DIR/tree-sitter-python"
else
    echo "Python grammar already cloned."
fi
(cd "$GRAMMAR_DIR/tree-sitter-python" && git checkout v0.20.0)

# JavaScript
if [ ! -d "$GRAMMAR_DIR/tree-sitter-javascript" ]; then
    git clone https://github.com/tree-sitter/tree-sitter-javascript.git "$GRAMMAR_DIR/tree-sitter-javascript"
else
    echo "JavaScript grammar already cloned."
fi
(cd "$GRAMMAR_DIR/tree-sitter-javascript" && git checkout v0.20.1)

# TypeScript
if [ ! -d "$GRAMMAR_DIR/tree-sitter-typescript" ]; then
    git clone https://github.com/tree-sitter/tree-sitter-typescript.git "$GRAMMAR_DIR/tree-sitter-typescript"
else
    echo "TypeScript grammar already cloned."
fi
(cd "$GRAMMAR_DIR/tree-sitter-typescript" && git checkout v0.20.1 && cd typescript && npm install)

echo "--- Compiling grammars into shared library ($LIBRARY_PATH) ---"

# Use a Python script to call the tree-sitter build function
# This is more portable than calling a C compiler directly.
# We set SETUPTOOLS_USE_DISTUTILS to ensure the vendored distutils from setuptools is used.
cat << EOF | SETUPTOOLS_USE_DISTUTILS=local ./.venv/bin/python3
from tree_sitter import Language

Language.build_library(
  # The output library path
  '$LIBRARY_PATH',

  # The list of grammar directories to compile
  [
    '$GRAMMAR_DIR/tree-sitter-python',
    '$GRAMMAR_DIR/tree-sitter-javascript',
    '$GRAMMAR_DIR/tree-sitter-typescript/typescript',
  ]
)
EOF

echo "--- Grammar setup complete. Library built at $LIBRARY_PATH ---"
echo "Add 'vendor/' and 'build/' to your .gitignore file."

