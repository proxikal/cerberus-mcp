#!/usr/bin/env python3
"""
Phase 14.4 Demonstration: Prediction Accuracy Tracking

This script demonstrates the prediction accuracy tracking system in action.
"""

import sys
import time
sys.path.insert(0, 'src')

from cerberus.mutation.ledger import DiffLedger

def main():
    print("=" * 60)
    print("Phase 14.4: Prediction Accuracy Tracking Demo")
    print("=" * 60)
    print()

    # Initialize ledger
    ledger = DiffLedger()

    # Scenario: Agent edits a function and gets predictions
    print("1. Agent edits 'validate_ops' function...")
    predictions = [
        {"symbol": "batch_edit", "confidence_score": 1.0},
        {"symbol": "process_request", "confidence_score": 0.95},
        {"symbol": "test_validate_ops", "confidence_score": 0.95}
    ]
    ledger.record_predictions("validate_ops", "src/mutations.py", predictions)
    print(f"   ✓ Logged {len(predictions)} predictions")
    print()

    # Simulate agent following some predictions
    time.sleep(0.5)

    print("2. Agent follows up on predictions...")

    # Follow first prediction
    print("   → Agent runs: cerberus retrieval get-symbol batch_edit")
    ledger.record_action(
        action_type="get-symbol",
        target_symbol="batch_edit",
        target_file="src/mutations.py",
        command="cerberus retrieval get-symbol batch_edit"
    )
    time.sleep(0.3)

    # Follow third prediction
    print("   → Agent runs: cerberus retrieval get-symbol test_validate_ops")
    ledger.record_action(
        action_type="get-symbol",
        target_symbol="test_validate_ops",
        target_file="tests/test_mutations.py",
        command="cerberus retrieval get-symbol test_validate_ops"
    )
    time.sleep(0.2)

    # Agent edits following a prediction
    print("   → Agent runs: cerberus mutations edit ... --symbol batch_edit")
    ledger.record_action(
        action_type="edit",
        target_symbol="batch_edit",
        target_file="src/mutations.py",
        command="cerberus mutations edit src/mutations.py --symbol batch_edit"
    )

    # Note: process_request prediction is ignored by the agent
    print()

    # Calculate accuracy
    print("3. Calculating prediction accuracy...")
    accuracy = ledger.get_prediction_accuracy(time_window=10.0)
    basic_stats = ledger.get_prediction_stats()
    print()

    # Display results
    print("=" * 60)
    print("ACCURACY METRICS")
    print("=" * 60)
    print(f"Total Predictions Made:    {accuracy['total_predictions']}")
    print(f"Predictions Followed:      {accuracy['predictions_followed']} ✓")
    print(f"Predictions Ignored:       {accuracy['predictions_ignored']} ✗")
    print(f"Accuracy Rate:             {accuracy['accuracy_rate']:.1%}")
    print(f"Avg Time to Action:        {accuracy['avg_time_to_action_seconds']:.1f}s")
    print(f"Time Window:               {accuracy['time_window_seconds']}s")
    print()

    print("=" * 60)
    print("PREDICTION STATS")
    print("=" * 60)
    print(f"Total Prediction Logs:     {basic_stats['total_prediction_logs']}")
    print(f"Avg Predictions Per Edit:  {basic_stats['average_predictions_per_edit']:.1f}")
    print()

    if basic_stats['top_predicted_symbols']:
        print("Most Frequently Predicted Symbols:")
        for symbol, count in list(basic_stats['top_predicted_symbols'].items())[:5]:
            print(f"  • {symbol}: {count} time(s)")
    print()

    # Interpretation
    print("=" * 60)
    print("INTERPRETATION")
    print("=" * 60)
    accuracy_rate = accuracy['accuracy_rate']
    if accuracy_rate >= 0.9:
        status = "🟢 EXCELLENT"
        message = f"{accuracy_rate:.1%} of predictions are being followed by agents"
    elif accuracy_rate >= 0.7:
        status = "🟡 GOOD"
        message = f"{accuracy_rate:.1%} of predictions are useful"
    elif accuracy_rate >= 0.5:
        status = "🟠 FAIR"
        message = f"{accuracy_rate:.1%} accuracy - room for improvement"
    else:
        status = "🔴 LOW"
        message = f"{accuracy_rate:.1%} accuracy - predictions may need tuning"

    print(f"{status}: {message}")
    print()

    print("=" * 60)
    print("CLI COMMAND")
    print("=" * 60)
    print("View these stats anytime with:")
    print("  cerberus quality prediction-stats")
    print("  cerberus quality prediction-stats --json")
    print("  cerberus quality prediction-stats --window 600 --limit 50")
    print()

    print("✅ Phase 14.4 demonstration complete!")

if __name__ == "__main__":
    main()
