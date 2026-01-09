#!/bin/bash
# Simple test that cerberus works from any directory

set -e

CERBERUS="/Users/proxikal/Desktop/Dev/Cerberus/bin/cerberus"

echo "================================================"
echo "Cerberus Global Installation Test (Simple)"
echo "================================================"
echo ""

# Create test project in /tmp
TEST_DIR="/tmp/cerberus_simple_test_$$"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

cat > example.py << 'EOF'
class Animal:
    def speak(self):
        pass

class Dog(Animal):
    def speak(self):
        return "Woof!"

def create_pet():
    return Dog()
EOF

git init > /dev/null 2>&1
git add . && git commit -m "init" > /dev/null 2>&1

echo "Test 1: Index project"
$CERBERUS index . > /dev/null 2>&1
if [ -f "cerberus.db" ]; then
    echo "✅ Index created"
else
    echo "❌ FAILED: No index created"
    exit 1
fi

echo "Test 2: Version"
$CERBERUS version 2>&1 | grep -q "Cerberus v0.5.0"
echo "✅ Version correct"

echo "Test 3: Stats"
$CERBERUS stats 2>&1 | grep -qi "symbol"
echo "✅ Stats works"

echo "Test 4: Search"
$CERBERUS search "Dog" > /dev/null 2>&1
echo "✅ Search works"

echo "Test 5: Get symbol"
$CERBERUS get-symbol Animal > /dev/null 2>&1
echo "✅ Get symbol works"

echo "Test 6: Skeletonize"
$CERBERUS skeletonize example.py > /dev/null 2>&1
echo "✅ Skeletonize works"

echo "Test 7: Inherit-tree"
$CERBERUS inherit-tree Dog > /dev/null 2>&1
echo "✅ Inherit-tree works"

echo "Test 8: Descendants"
$CERBERUS descendants Animal > /dev/null 2>&1
echo "✅ Descendants works"

echo "Test 9: Smart context"
$CERBERUS smart-context Dog --include-bases > /dev/null 2>&1
echo "✅ Smart context works"

echo "Test 10: Update"
echo "# comment" >> example.py
git add . && git commit -m "update" > /dev/null 2>&1
$CERBERUS update > /dev/null 2>&1
echo "✅ Update works"

echo "Test 11: Doctor"
$CERBERUS doctor > /dev/null 2>&1
echo "✅ Doctor works"

# Test from nested directory
echo "Test 12: From nested directory"
mkdir -p subdir/nested
cd subdir/nested
$CERBERUS stats --index ../../cerberus.db > /dev/null 2>&1
echo "✅ Works from nested directory"

echo ""
echo "================================================"
echo "✅ ALL TESTS PASSED"
echo "================================================"
echo ""
echo "Cerberus binary location:"
echo "  $CERBERUS"
echo ""
echo "To use from anywhere, add to PATH:"
echo "  export PATH=\"/Users/proxikal/Desktop/Dev/Cerberus/bin:\$PATH\""
echo ""
echo "Or create symlink:"
echo "  ln -sf $CERBERUS /usr/local/bin/cerberus"
echo ""

# Cleanup
rm -rf "$TEST_DIR"

exit 0
