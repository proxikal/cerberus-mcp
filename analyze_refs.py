#!/usr/bin/env python3
"""Analyze reference data to find most referenced symbols."""
import json
import sys
from collections import Counter

data = json.load(sys.stdin)
refs = data['references']

# Find symbols with cross-file references
targets = [r['target_symbol'] for r in refs if r['source_file'] != r['target_file']]
counts = Counter(targets)

print("Most referenced symbols (cross-file):")
for sym, count in counts.most_common(15):
    print(f"{count:3d}: {sym}")
