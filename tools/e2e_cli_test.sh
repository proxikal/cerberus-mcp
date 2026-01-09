#!/bin/bash
# End-to-end CLI verification for all phases
# Tests that every command actually works in production

set -e

echo "=========================================="
echo "Cerberus E2E CLI Verification"
echo "=========================================="
echo ""

# Setup
export PYTHONPATH=src
export CERBERUS_TRACK_SESSION=false
TEST_DIR="/tmp/cerberus_e2e_test_$$"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

# Create test Python project
cat > main.py << 'EOF'
class BaseOptimizer:
    """Base optimizer class."""
    def step(self):
        """Base step method."""
        pass

    def zero_grad(self):
        """Zero gradients."""
        pass

class Adam(BaseOptimizer):
    """Adam optimizer."""
    def __init__(self, lr=0.001):
        self.lr = lr

    def step(self):
        """Adam-specific step."""
        print("Adam step")

class SGD(BaseOptimizer):
    """SGD optimizer."""
    def step(self):
        """SGD-specific step."""
        print("SGD step")

def train_model():
    """Train with optimizer."""
    optimizer = Adam(lr=0.01)
    optimizer.step()
    optimizer.zero_grad()
    return optimizer
EOF

# Initialize git
git init
git add .
git commit -m "Initial commit"

echo "✓ Test environment created"
echo ""

# Phase 1: Advanced Dependency Intelligence
echo "Phase 1: Advanced Dependency Intelligence"
echo "------------------------------------------"

# Test index
python3 -m cerberus.main index . > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ cerberus index"
else
    echo "❌ cerberus index FAILED"
    exit 1
fi

# Test deps
python3 -m cerberus.main deps --symbol "train_model" --json > /tmp/deps.json 2>/dev/null
if grep -q "train_model" /tmp/deps.json; then
    echo "✅ cerberus deps --symbol"
else
    echo "❌ cerberus deps FAILED"
    exit 1
fi

# Test inspect
python3 -m cerberus.main inspect main.py --json > /tmp/inspect.json 2>/dev/null
if grep -q "BaseOptimizer" /tmp/inspect.json; then
    echo "✅ cerberus inspect"
else
    echo "❌ cerberus inspect FAILED"
    exit 1
fi

echo ""

# Phase 2: Context Synthesis
echo "Phase 2: Context Synthesis & Compaction"
echo "----------------------------------------"

# Test skeletonize
python3 -m cerberus.main skeletonize main.py --json > /tmp/skeleton.json 2>/dev/null
if grep -q "signature" /tmp/skeleton.json; then
    echo "✅ cerberus skeletonize"
else
    echo "❌ cerberus skeletonize FAILED"
    exit 1
fi

# Test get-context
python3 -m cerberus.main get-context train_model --json > /tmp/context.json 2>/dev/null
if grep -q "train_model" /tmp/context.json; then
    echo "✅ cerberus get-context"
else
    echo "❌ cerberus get-context FAILED"
    exit 1
fi

# Test skeleton-file
python3 -m cerberus.main skeleton-file main.py --json > /tmp/skel_file.json 2>/dev/null
if grep -q "content" /tmp/skel_file.json; then
    echo "✅ cerberus skeleton-file"
else
    echo "❌ cerberus skeleton-file FAILED"
    exit 1
fi

echo ""

# Phase 3: Operational Excellence
echo "Phase 3: Operational Excellence"
echo "--------------------------------"

# Test search
python3 -m cerberus.main search "optimizer" --json > /tmp/search.json 2>/dev/null
if grep -q "results" /tmp/search.json; then
    echo "✅ cerberus search"
else
    echo "❌ cerberus search FAILED"
    exit 1
fi

# Test update (after modifying file)
echo "# Comment" >> main.py
git add main.py
git commit -m "Add comment" > /dev/null 2>&1
python3 -m cerberus.main update > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ cerberus update"
else
    echo "❌ cerberus update FAILED"
    exit 1
fi

# Test watcher status (don't start, just check command works)
python3 -m cerberus.main watcher status > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ cerberus watcher"
else
    echo "❌ cerberus watcher FAILED"
    exit 1
fi

echo ""

# Phase 4: Aegis-Scale Performance
echo "Phase 4: Aegis-Scale Performance"
echo "--------------------------------"

# Test stats
python3 -m cerberus.main stats --json > /tmp/stats.json 2>/dev/null
if grep -q "symbols" /tmp/stats.json; then
    echo "✅ cerberus stats"
else
    echo "❌ cerberus stats FAILED"
    exit 1
fi

# Test bench
python3 -m cerberus.main bench --json > /tmp/bench.json 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ cerberus bench"
else
    echo "❌ cerberus bench FAILED"
    exit 1
fi

echo ""

# Phase 5: Symbolic Intelligence
echo "Phase 5: Symbolic Intelligence"
echo "-------------------------------"

# Test calls
python3 -m cerberus.main calls --json > /tmp/calls.json 2>/dev/null
if grep -q "calls" /tmp/calls.json; then
    echo "✅ cerberus calls"
else
    echo "❌ cerberus calls FAILED"
    exit 1
fi

# Test references
python3 -m cerberus.main references --json > /tmp/refs.json 2>/dev/null
if grep -q "references" /tmp/refs.json; then
    echo "✅ cerberus references"
else
    echo "❌ cerberus references FAILED"
    exit 1
fi

# Test resolution-stats
python3 -m cerberus.main resolution-stats --json > /tmp/res_stats.json 2>/dev/null
if grep -q "total" /tmp/res_stats.json; then
    echo "✅ cerberus resolution-stats"
else
    echo "❌ cerberus resolution-stats FAILED"
    exit 1
fi

echo ""

# Phase 6: Advanced Context Synthesis
echo "Phase 6: Advanced Context Synthesis"
echo "------------------------------------"

# Test inherit-tree
python3 -m cerberus.main inherit-tree Adam --json > /tmp/inherit.json 2>/dev/null
if grep -q "mro" /tmp/inherit.json; then
    echo "✅ cerberus inherit-tree"
else
    echo "❌ cerberus inherit-tree FAILED"
    exit 1
fi

# Test descendants
python3 -m cerberus.main descendants BaseOptimizer --json > /tmp/desc.json 2>/dev/null
if grep -q "descendants" /tmp/desc.json; then
    echo "✅ cerberus descendants"
else
    echo "❌ cerberus descendants FAILED"
    exit 1
fi

# Test overrides
python3 -m cerberus.main overrides Adam --json > /tmp/over.json 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ cerberus overrides"
else
    echo "❌ cerberus overrides FAILED"
    exit 1
fi

# Test call-graph
python3 -m cerberus.main call-graph train_model --json > /tmp/callgraph.json 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ cerberus call-graph"
else
    echo "❌ cerberus call-graph FAILED"
    exit 1
fi

# Test smart-context
python3 -m cerberus.main smart-context Adam --include-bases --json > /tmp/smart.json 2>/dev/null
if grep -q "context" /tmp/smart.json; then
    echo "✅ cerberus smart-context"
else
    echo "❌ cerberus smart-context FAILED"
    exit 1
fi

echo ""

# Utilities
echo "Utilities & Verification"
echo "------------------------"

# Test doctor
python3 -m cerberus.main doctor --json > /tmp/doctor.json 2>/dev/null
if grep -q "checks" /tmp/doctor.json; then
    echo "✅ cerberus doctor"
else
    echo "❌ cerberus doctor FAILED"
    exit 1
fi

# Test generate-tools
python3 -m cerberus.main generate-tools --json > /tmp/tools.json 2>/dev/null
if grep -q "tools" /tmp/tools.json; then
    echo "✅ cerberus generate-tools"
else
    echo "❌ cerberus generate-tools FAILED"
    exit 1
fi

# Test verify-context (from project root)
cd - > /dev/null
python3 -m cerberus.main verify-context > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ cerberus verify-context"
else
    echo "❌ cerberus verify-context FAILED"
    exit 1
fi

# Test version
python3 -m cerberus.main version > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ cerberus version"
else
    echo "❌ cerberus version FAILED"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ ALL CLI COMMANDS FUNCTIONAL"
echo "=========================================="
echo ""
echo "Summary:"
echo "  Phase 1: ✅ index, deps, inspect"
echo "  Phase 2: ✅ skeletonize, get-context, skeleton-file"
echo "  Phase 3: ✅ search, update, watcher"
echo "  Phase 4: ✅ stats, bench"
echo "  Phase 5: ✅ calls, references, resolution-stats"
echo "  Phase 6: ✅ inherit-tree, descendants, overrides, call-graph, smart-context"
echo "  Utils:   ✅ doctor, generate-tools, verify-context, version"
echo ""

# Cleanup
rm -rf "$TEST_DIR"
cd - > /dev/null

exit 0
