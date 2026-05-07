#!/bin/bash
# Compare Lynis baseline and post-hardening scans
# Extracts key metrics and shows improvements

set -euo pipefail

BASELINE_FILE="${1:-evidence/baseline/lynis-baseline.txt}"
POST_FILE="${2:-evidence/post/lynis-post.txt}"

if [ ! -f "$BASELINE_FILE" ] || [ ! -f "$POST_FILE" ]; then
    echo "Usage: $0 <baseline-lynis-file> <post-hardening-lynis-file>"
    echo ""
    echo "Files not found:"
    [ ! -f "$BASELINE_FILE" ] && echo "  - $BASELINE_FILE"
    [ ! -f "$POST_FILE" ] && echo "  - $POST_FILE"
    exit 1
fi

echo "=== Lynis Comparison Report ==="
echo "Baseline: $BASELINE_FILE"
echo "Post-Hardening: $POST_FILE"
echo ""

# Extract scores
BASELINE_SCORE=$(grep -E "^Hardening index" "$BASELINE_FILE" | awk '{print $3}' | head -1 || echo "N/A")
POST_SCORE=$(grep -E "^Hardening index" "$POST_FILE" | awk '{print $3}' | head -1 || echo "N/A")

echo "Hardening Index:"
echo "  Baseline:     $BASELINE_SCORE"
echo "  Post-Hardening: $POST_SCORE"

if [ "$BASELINE_SCORE" != "N/A" ] && [ "$POST_SCORE" != "N/A" ]; then
    IMPROVEMENT=$(echo "$POST_SCORE - $BASELINE_SCORE" | bc 2>/dev/null || echo "N/A")
    if [ "$IMPROVEMENT" != "N/A" ]; then
        if (( $(echo "$IMPROVEMENT > 0" | bc -l) )); then
            echo "  Improvement:  +$IMPROVEMENT points ✓"
        else
            echo "  Change:       $IMPROVEMENT points"
        fi
    fi
fi

echo ""

# Extract warnings
BASELINE_WARNINGS=$(grep -c "Warning\|Suggestion" "$BASELINE_FILE" 2>/dev/null || echo "0")
POST_WARNINGS=$(grep -c "Warning\|Suggestion" "$POST_FILE" 2>/dev/null || echo "0")

echo "Warnings/Suggestions:"
echo "  Baseline:     $BASELINE_WARNINGS"
echo "  Post-Hardening: $POST_WARNINGS"

if [ "$BASELINE_WARNINGS" != "0" ] && [ "$POST_WARNINGS" != "0" ]; then
    REDUCTION=$(echo "$BASELINE_WARNINGS - $POST_WARNINGS" | bc 2>/dev/null || echo "N/A")
    if [ "$REDUCTION" != "N/A" ]; then
        if (( $(echo "$REDUCTION > 0" | bc -l) )); then
            echo "  Reduction:    -$REDUCTION warnings ✓"
        else
            echo "  Change:       $REDUCTION warnings"
        fi
    fi
fi

echo ""

# Extract test results
echo "Test Results Summary:"
echo ""

BASELINE_PASSED=$(grep -c "\[ OK \]" "$BASELINE_FILE" 2>/dev/null || echo "0")
POST_PASSED=$(grep -c "\[ OK \]" "$POST_FILE" 2>/dev/null || echo "0")

echo "  Tests Passed:"
echo "    Baseline:     $BASELINE_PASSED"
echo "    Post-Hardening: $POST_PASSED"

BASELINE_FAILED=$(grep -c "\[ FAIL \]" "$BASELINE_FILE" 2>/dev/null || echo "0")
POST_FAILED=$(grep -c "\[ FAIL \]" "$POST_FILE" 2>/dev/null || echo "0")

echo "  Tests Failed:"
echo "    Baseline:     $BASELINE_FAILED"
echo "    Post-Hardening: $POST_FAILED"

echo ""

# Show key improvements
echo "Key Improvements (Post-Hardening):"
echo ""

# Check for specific improvements
if grep -q "SSH.*hardening" "$POST_FILE" && ! grep -q "SSH.*hardening" "$BASELINE_FILE" 2>/dev/null; then
    echo "  ✓ SSH hardening applied"
fi

if grep -q "Firewall.*enabled" "$POST_FILE" && ! grep -q "Firewall.*enabled" "$BASELINE_FILE" 2>/dev/null; then
    echo "  ✓ Firewall enabled"
fi

if grep -q "fail2ban" "$POST_FILE" && ! grep -q "fail2ban" "$BASELINE_FILE" 2>/dev/null; then
    echo "  ✓ fail2ban installed and configured"
fi

if grep -q "auditd" "$POST_FILE" && ! grep -q "auditd" "$BASELINE_FILE" 2>/dev/null; then
    echo "  ✓ auditd installed and configured"
fi

echo ""
echo "=== End of Comparison Report ==="
