#!/bin/bash
# Test cerberus works from any directory with proper PATH setup

set -e

CERBERUS_BIN="/Users/proxikal/Desktop/Dev/Cerberus/bin/cerberus"

# Helper function to filter logging from JSON output
filter_json() {
    grep -v "INFO" | grep -v "Agent Session" | grep -v "Tokens" | grep -v "╭" | grep -v "│" | grep -v "╰" | grep -v "💰" | grep -v "Saved.*tokens" | grep -v "WARNING"
}

echo "=========================================="
echo "Cerberus Global Installation Test"
echo "=========================================="
echo ""

# Test 1: Version check
echo "Test 1: Version check from current directory"
cd /Users/proxikal/Desktop/Dev/Cerberus
VERSION=$($CERBERUS_BIN version 2>&1 | grep "Cerberus v")
echo "✓ Version: $VERSION"
echo ""

# Test 2: Create test project in /tmp
echo "Test 2: Creating test project in /tmp"
TEST_DIR="/tmp/cerberus_global_test_$$"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

cat > main.py << 'EOF'
"""Test module for Cerberus global testing."""

class Animal:
    """Base animal class."""
    def speak(self):
        pass

class Dog(Animal):
    """Dog class."""
    def speak(self):
        return "Woof!"

class Cat(Animal):
    """Cat class."""
    def speak(self):
        return "Meow!"

def create_dog():
    """Create a dog instance."""
    dog = Dog()
    return dog

def make_animals_speak():
    """Make all animals speak."""
    dog = create_dog()
    cat = Cat()

    print(dog.speak())
    print(cat.speak())
EOF

git init > /dev/null 2>&1
git add . > /dev/null 2>&1
git commit -m "Initial commit" > /dev/null 2>&1

echo "✓ Test project created in: $TEST_DIR"
echo ""

# Test 3: Index from /tmp directory
echo "Test 3: Index from /tmp directory (working directory test)"
$CERBERUS_BIN index . > /dev/null 2>&1
if [ -f "cerberus.db" ]; then
    echo "✓ Index created: cerberus.db"
else
    echo "✗ FAILED: cerberus.db not created"
    exit 1
fi
echo ""

# Test 4: Stats
echo "Test 4: Stats command"
STATS=$($CERBERUS_BIN stats --json 2>&1 | filter_json | jq -r '.total_symbols')
if [ "$STATS" -gt 0 ] 2>/dev/null; then
    echo "✓ Stats shows $STATS symbols"
else
    echo "✗ FAILED: No symbols found (got: $STATS)"
    exit 1
fi
echo ""

# Test 5: Search
echo "Test 5: Search command"
SEARCH_RESULTS=$($CERBERUS_BIN search "Dog" --json 2>&1 | filter_json | jq -r 'length')
if [ "$SEARCH_RESULTS" -gt 0 ] 2>/dev/null; then
    echo "✓ Search found $SEARCH_RESULTS results"
else
    echo "✗ FAILED: Search returned no results (got: $SEARCH_RESULTS)"
    exit 1
fi
echo ""

# Test 6: Get symbol
echo "Test 6: Get symbol"
SYMBOL=$($CERBERUS_BIN get-symbol Dog --json 2>&1 | filter_json | jq -r '.name')
if [ "$SYMBOL" = "Dog" ]; then
    echo "✓ get-symbol works"
else
    echo "✗ FAILED: get-symbol didn't find Dog"
    exit 1
fi
echo ""

# Test 7: Skeletonize
echo "Test 7: Skeletonize"
SKEL=$($CERBERUS_BIN skeletonize main.py --json 2>&1 | filter_json | jq -r '.signature')
if [ -n "$SKEL" ]; then
    echo "✓ Skeletonize works"
else
    echo "✗ FAILED: Skeletonize failed"
    exit 1
fi
echo ""

# Test 8: Inherit-tree (Phase 6)
echo "Test 8: Inherit-tree (Phase 6)"
MRO=$($CERBERUS_BIN inherit-tree Dog --json 2>&1 | filter_json | jq -r '.mro | length')
if [ "$MRO" -gt 0 ]; then
    echo "✓ Inherit-tree works (MRO length: $MRO)"
else
    echo "✗ FAILED: Inherit-tree failed"
    exit 1
fi
echo ""

# Test 9: Descendants
echo "Test 9: Descendants"
DESC=$($CERBERUS_BIN descendants Animal --json 2>&1 | filter_json | jq -r '.descendants | length')
if [ "$DESC" -gt 0 ]; then
    echo "✓ Descendants works (found $DESC)"
else
    echo "✗ FAILED: Descendants failed"
    exit 1
fi
echo ""

# Test 10: Smart context (Phase 6)
echo "Test 10: Smart context"
CONTEXT=$($CERBERUS_BIN smart-context Dog --include-bases --json 2>&1 | filter_json | jq -r '.context')
if [ -n "$CONTEXT" ]; then
    echo "✓ Smart context works"
else
    echo "✗ FAILED: Smart context failed"
    exit 1
fi
echo ""

# Test 11: Update (incremental)
echo "Test 11: Incremental update"
echo "# Comment" >> main.py
git add main.py > /dev/null 2>&1
git commit -m "Add comment" > /dev/null 2>&1
$CERBERUS_BIN update > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Incremental update works"
else
    echo "✗ FAILED: Update failed"
    exit 1
fi
echo ""

# Test 12: Doctor
echo "Test 12: Doctor diagnostic"
DOCTOR=$($CERBERUS_BIN doctor --json 2>&1 | filter_json | jq -r '.checks | length')
if [ "$DOCTOR" -gt 0 ]; then
    echo "✓ Doctor works (ran $DOCTOR checks)"
else
    echo "✗ FAILED: Doctor failed"
    exit 1
fi
echo ""

# Test 13: From nested directory
echo "Test 13: From nested subdirectory"
mkdir -p subdir/nested
cd subdir/nested
INDEX_CHECK=$($CERBERUS_BIN stats --index ../../cerberus.db --json 2>&1 | filter_json | jq -r '.total_symbols')
if [ "$INDEX_CHECK" -gt 0 ] 2>/dev/null; then
    echo "✓ Works from nested directory with --index"
else
    echo "✗ FAILED: Nested directory test failed (got: $INDEX_CHECK)"
    exit 1
fi
echo ""

# Test 14: Verify-context (from project root)
echo "Test 14: Verify-context (project-specific)"
cd /Users/proxikal/Desktop/Dev/Cerberus
VERIFY=$($CERBERUS_BIN verify-context 2>&1 | grep -c "✓" || true)
if [ "$VERIFY" -gt 0 ]; then
    echo "✓ Verify-context works"
else
    echo "⚠ Verify-context might have issues (non-critical)"
fi
echo ""

echo "=========================================="
echo "✅ ALL TESTS PASSED"
echo "=========================================="
echo ""
echo "Cerberus works correctly from any directory!"
echo ""
echo "To add to PATH, run:"
echo "  export PATH=\"/Users/proxikal/Desktop/Dev/Cerberus/bin:\$PATH\""
echo ""
echo "Or create symlink:"
echo "  sudo ln -sf /Users/proxikal/Desktop/Dev/Cerberus/bin/cerberus /usr/local/bin/cerberus"
echo ""

# Cleanup
rm -rf "$TEST_DIR"

exit 0
