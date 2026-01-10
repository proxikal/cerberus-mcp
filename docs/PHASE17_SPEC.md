# Phase 17 Specification: Integration & Safety Hardening

**Status:** Proposed (Deferred from Phase 14)
**Goal:** Complete integration of Phase 14 features with existing safety systems (Phase 12/13), add progressive rollout flags, and optimize performance to meet <250ms total budget.

---

## 🎯 Core Objectives

### 1. Style Guard + Verify Workflow Integration
**Mission:** Enable atomic style fixing with test verification.

**Problem:**
- Style Guard currently fixes issues without running tests
- Agents need to manually verify fixes don't break functionality
- No atomic rollback if style fixes cause test failures

**Solution:**
```bash
# Atomic style fix with verification
cerberus quality style-fix src/mutations.py --verify "pytest tests/"
# Flow:
#   1. Apply style fixes
#   2. Run test command
#   3. If tests pass: commit fixes
#   4. If tests fail: rollback all fixes (use undo system)

# Batch style fix with verification
cerberus quality style-fix src/ --recursive --verify "pytest"
# Fixes all files, rollback entire batch if any test fails
```

**Integration Points:**
- Leverage `DiffLedger` undo system (Phase 12.5)
- Use Symbol Guard risk scoring (Phase 13.2)
- Record style operations to ledger for transparency

---

### 2. Predictions + Undo History Integration
**Mission:** Prevent suggesting recently-undone symbols to avoid suggestion loops.

**Problem:**
- Agent edits symbol A
- Gets prediction to edit symbol B
- Agent edits B, realizes mistake, runs `cerberus mutations undo`
- Agent edits A again, gets prediction for B again (already know it was wrong)

**Solution:**
```python
# In PredictionEngine.predict_related_changes()
def predict_related_changes(self, edited_symbol, file_path):
    suggestions = self._find_direct_callers(...)

    # Check undo history
    recently_undone = self._get_recently_undone_symbols(time_window=3600)  # 1 hour

    # Filter out recently undone symbols
    filtered = [s for s in suggestions if s.symbol not in recently_undone]

    # Add metadata to predictions
    for pred in suggestions:
        if pred.symbol in recently_undone:
            pred.metadata = {"recently_undone": True, "reason": "skip"}

    return filtered
```

**Output:**
```json
{
  "predictions": [...],
  "filtered_predictions": [
    {
      "symbol": "validate_ops",
      "reason": "recently_undone",
      "undone_at": "2026-01-10T15:30:00Z",
      "undo_reason": "Reverted failed edit"
    }
  ]
}
```

---

### 3. Safety Metadata in All Anchors
**Mission:** Ensure every output includes Phase 13.2 risk signals.

**Current State:**
- Context anchors exist (Phase 14.2) but not all outputs have full safety metadata
- Risk scores calculated but not consistently displayed

**Enhancement:**
```python
# Standard anchor format with safety metadata
class ContextAnchor:
    @staticmethod
    def create_anchor(symbol, file_path):
        return {
            "gps": {
                "file": file_path,
                "symbol": symbol.name,
                "lines": {"start": symbol.start_line, "end": symbol.end_line}
            },
            "dependencies": [...],
            "risk": {
                "level": "MEDIUM",  # From Phase 13.2
                "score": 0.65,
                "factors": {
                    "churn_per_week": 0.8,
                    "test_coverage": 0.85,
                    "authors": 3
                }
            },
            "temporal": {
                "last_modified": "2026-01-08T14:32:15Z",
                "last_modified_by": "alice"
            },
            "safety": {
                "symbol_guard": "WARN",      # Phase 13.2
                "verifiable": True,           # Has tests
                "undo_available": True,       # Phase 12.5
                "recent_undo": False,         # Phase 17.2
                "prediction_accuracy": 0.85   # Phase 14.4 (if symbol frequently predicted)
            }
        }
```

**Apply to:**
- `cerberus retrieval get-symbol` (already has partial anchors)
- `cerberus retrieval blueprint` (add anchor metadata to nodes)
- `cerberus mutations edit/delete` (include in confirmation output)
- `cerberus quality related-changes` (predictions already have anchors)

---

### 4. Progressive Rollout Flags
**Mission:** Allow gradual adoption of Phase 14 features with feature flags.

**Configuration:**
```bash
# Environment variables for progressive rollout
export CERBERUS_STYLE_GUARD=enabled      # enabled, beta, disabled
export CERBERUS_ANCHORS=json             # json, compact, text, off
export CERBERUS_PREDICTIVE=inline        # off, inline, verbose
export CERBERUS_PREDICT_ACCURACY=enabled # Track action accuracy

# Per-command overrides
cerberus mutations edit --no-predict     # Disable predictions for this edit
cerberus mutations edit --no-style       # Skip style detection
cerberus quality style-fix --dry-run     # Preview without applying
```

**Default Configuration (Phase 17):**
```python
# src/cerberus/config.py
DEFAULT_PHASE14_CONFIG = {
    "style_guard": "enabled",
    "anchors": "json",
    "predictive": "inline",
    "prediction_accuracy_tracking": "enabled",
    "style_fix_with_verify": "enabled",
    "undo_aware_predictions": "enabled"
}
```

**CLI Flag Support:**
```bash
cerberus --disable-phase14 mutations edit ...  # Disable all Phase 14 features
cerberus --phase14-config=minimal ...          # Minimal overhead mode
```

---

### 5. Performance Optimization
**Mission:** Ensure Phase 14 total overhead <250ms per operation.

**Current Performance:**
- Style detection: ~30ms
- Prediction engine: ~150ms
- Anchor generation: ~20ms
- Action tracking: <10ms
- **Total:** ~210ms ✅ (under budget)

**Optimizations:**
1. **Lazy Loading:**
   ```python
   # Don't import PredictionEngine until needed
   if not no_predict:
       from cerberus.quality.predictor import PredictionEngine  # Lazy import
   ```

2. **Async Predictions (Optional):**
   ```python
   # Run predictions in background thread (don't block mutation response)
   import threading

   def async_predict():
       predictions = engine.predict_related_changes(...)
       ledger.record_predictions(...)

   thread = threading.Thread(target=async_predict)
   thread.start()
   # Return mutation result immediately
   ```

3. **Cache Frequently Predicted Symbols:**
   ```python
   # Cache hot predictions (e.g., batch_edit always suggests validate_ops)
   @lru_cache(maxsize=100)
   def get_predictions_for_symbol(symbol, file_path):
       ...
   ```

4. **Performance Monitoring:**
   ```bash
   cerberus debug performance-report
   # Shows Phase 14 overhead breakdown:
   #   Style Guard: 28ms (avg)
   #   Predictions: 142ms (avg)
   #   Anchors: 18ms (avg)
   #   Action Tracking: 8ms (avg)
   #   Total: 196ms ✅
   ```

---

## 🛡️ Mission Compliance

### Alignment with Core Mandates

| Mandate | Phase 17 Implementation |
|---------|------------------------|
| **Verified Transactions** | ✅ Style fixes integrated with --verify |
| **Strict Resolution** | ✅ All features controllable via flags |
| **100% Signal / 0% Noise** | ✅ Undo-aware predictions prevent loops |
| **Parse-Perfect Output** | ✅ Safety metadata in structured anchors |
| **Performance** | ✅ <250ms total overhead maintained |

---

## 🏗 Implementation Strategy

### Phase 17.1: Style Guard + Verify (Week 1)
- [ ] Add `--verify` flag to `cerberus quality style-fix`
- [ ] Integrate with `DiffLedger` undo system
- [ ] Test verification flow: apply → test → commit/rollback
- [ ] Add ledger logging for verification results

**Success Criteria:**
- Style fixes rollback if tests fail
- Verification command output captured and displayed
- Zero regressions in existing `style-fix` behavior

### Phase 17.2: Undo-Aware Predictions (Week 1)
- [ ] Add `_get_recently_undone_symbols()` to `PredictionEngine`
- [ ] Filter predictions against undo history
- [ ] Add metadata for filtered predictions
- [ ] Update `prediction-stats` to show undo-filtered count

**Success Criteria:**
- Recently undone symbols not suggested within 1-hour window
- Filtered predictions logged with reason
- Accuracy calculation excludes undo-filtered suggestions

### Phase 17.3: Universal Safety Metadata (Week 2)
- [ ] Audit all command outputs for anchor completeness
- [ ] Ensure risk scores present in all anchors
- [ ] Add prediction accuracy to frequently predicted symbols
- [ ] Validate anchor schema compliance

**Success Criteria:**
- 100% of symbol outputs include safety metadata
- Parse accuracy >98% for all anchor formats
- Schema validation passing

### Phase 17.4: Progressive Rollout Flags (Week 2)
- [ ] Add `CERBERUS_PHASE14_*` environment variables
- [ ] Implement per-command `--no-*` flags
- [ ] Add `cerberus config show-phase14` command
- [ ] Document feature flag usage

**Success Criteria:**
- All Phase 14 features toggle-able independently
- Default configuration documented
- Flags work in machine and human modes

### Phase 17.5: Performance Optimization (Week 3)
- [ ] Profile Phase 14 overhead in production scenarios
- [ ] Implement lazy loading for heavy modules
- [ ] Optional async predictions (configurable)
- [ ] Add `cerberus debug performance-report` command

**Success Criteria:**
- Total Phase 14 overhead <250ms (verified)
- Performance report shows per-feature breakdown
- Async mode available for high-throughput scenarios

---

## 📋 Testing Strategy

### Unit Tests
- `test_phase17_1_verify.py` - Style fix verification flow
- `test_phase17_2_undo_aware.py` - Undo history integration
- `test_phase17_3_anchors.py` - Safety metadata completeness
- `test_phase17_4_flags.py` - Feature flag toggling
- `test_phase17_5_performance.py` - Overhead benchmarks

### Integration Tests
- End-to-end style fix with failing tests (rollback)
- Prediction filtering after undo
- Anchor metadata validation across all commands
- Feature flags in machine/human modes

### Performance Tests
- Benchmark Phase 14 overhead with 100 operations
- Verify <250ms budget maintained
- Async predictions don't block mutations

---

## 📊 Success Metrics

### Phase 17.1: Style Guard + Verify
- 100% rollback on test failure
- Verification output captured correctly
- Zero regressions

### Phase 17.2: Undo-Aware Predictions
- Recently undone symbols filtered within 1-hour window
- Accuracy metrics exclude filtered predictions
- Suggestion loop prevention verified

### Phase 17.3: Safety Metadata
- 100% anchor completeness
- Parse accuracy >98%
- Schema validation passing

### Phase 17.4: Feature Flags
- All Phase 14 features independently toggle-able
- Flags documented and tested
- Default config production-ready

### Phase 17.5: Performance
- Total Phase 14 overhead <250ms
- Performance report available
- Async mode functional (optional)

---

## 🔗 Dependencies

**Requires:**
- Phase 12.5 (Undo system) ✅
- Phase 13.2 (Symbol Guard, Stability) ✅
- Phase 14.1 (Style Guard) ✅
- Phase 14.2 (Context Anchors) ✅
- Phase 14.3 (Predictive Editing) ✅
- Phase 14.4 (Prediction Accuracy) ✅

**Enables:**
- Production readiness for all Phase 14 features
- Safe gradual rollout
- Complete safety integration

---

## 🚧 Considerations & Risks

### Risks
1. **Verification Complexity:** Running test commands may have environment dependencies
2. **Undo History Size:** Long-running sessions may accumulate large undo logs
3. **Performance Async:** Background threads may complicate error handling

### Mitigations
1. **Verification:** Document test command requirements, provide clear error messages
2. **Undo History:** Implement time-based expiration (default: 24 hours)
3. **Async:** Make async mode opt-in, default to synchronous

---

## 📚 Documentation Updates

### CERBERUS.md
- Document `--verify` flag for style-fix
- Add feature flag configuration section
- Update performance expectations

### PHASE14_SPEC.md
- Mark integration items as "Moved to Phase 17"
- Cross-reference Phase 17 spec

### User Guide
- When to use `--verify` with style-fix
- How to configure feature flags
- Performance tuning for high-throughput scenarios

---

## 🎓 Expected Benefits

1. **Safety:** Style fixes can't break tests (rollback protection)
2. **Efficiency:** No suggestion loops from recently undone edits
3. **Transparency:** Full safety metadata in all outputs
4. **Control:** Feature flags for gradual adoption
5. **Performance:** Optimized to stay under 250ms budget

---

## Conclusion

Phase 17 completes the integration and hardening of Phase 14 features, ensuring:
- Safety through verification and undo integration
- Transparency through complete safety metadata
- Control through progressive rollout flags
- Performance through optimization and monitoring

This phase transforms Phase 14 from "feature complete" to "production hardened."
