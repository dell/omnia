#!/bin/bash
# Simple verification script for cleanup_sinks short-form parameter logic

echo "=========================================="
echo "Cleanup Sinks Short-Form Verification"
echo "=========================================="
echo ""

cd /root/automation_testing/omnia

echo "Test 1: Invalid single sink name (-e kafs)"
echo "Expected: Error message"
echo "----------------------------------------"
if bash -c 'source src/main/omnia.sh 2>/dev/null; args=("-e" "kafs"); normalize_extra_args args' 2>&1 | grep -q "ERROR"; then
    echo "✅ PASS: Invalid sink name rejected"
else
    echo "❌ FAIL: Should have rejected invalid sink name"
fi
echo ""

echo "Test 2: Valid single sink name (-e kafka)"
echo "Expected: Normalized to kafka=true"
echo "----------------------------------------"
result=$(bash -c 'source src/main/omnia.sh 2>/dev/null; args=("-e" "kafka"); normalize_extra_args args; echo "${args[@]}"' 2>/dev/null)
if [[ "$result" == *"kafka=true"* ]]; then
    echo "✅ PASS: Valid sink normalized correctly"
    echo "   Result: $result"
else
    echo "❌ FAIL: Should have normalized to kafka=true"
    echo "   Result: $result"
fi
echo ""

echo "Test 3: Invalid sink in comma-separated list (-e kafka,kafs)"
echo "Expected: Error message with specific invalid sink"
echo "----------------------------------------"
if bash -c 'source src/main/omnia.sh 2>/dev/null; args=("-e" "kafka,kafs"); normalize_extra_args args' 2>&1 | grep -q "ERROR.*kafs"; then
    echo "✅ PASS: Invalid sink in list rejected"
else
    echo "❌ FAIL: Should have rejected invalid sink in list"
fi
echo ""

echo "Test 4: Valid comma-separated list (-e kafka,victoria_metrics)"
echo "Expected: Normalized to sinks=kafka,victoria_metrics"
echo "----------------------------------------"
result=$(bash -c 'source src/main/omnia.sh 2>/dev/null; args=("-e" "kafka,victoria_metrics"); normalize_extra_args args; echo "${args[@]}"' 2>/dev/null)
if [[ "$result" == *"sinks=kafka,victoria_metrics"* ]]; then
    echo "✅ PASS: Valid comma-separated list normalized correctly"
    echo "   Result: $result"
else
    echo "❌ FAIL: Should have normalized to sinks=kafka,victoria_metrics"
    echo "   Result: $result"
fi
echo ""

echo "Test 5: All three sinks comma-separated (-e kafka,victoria_metrics,victoria_logs)"
echo "Expected: Normalized to sinks=kafka,victoria_metrics,victoria_logs"
echo "----------------------------------------"
result=$(bash -c 'source src/main/omnia.sh 2>/dev/null; args=("-e" "kafka,victoria_metrics,victoria_logs"); normalize_extra_args args; echo "${args[@]}"' 2>/dev/null)
if [[ "$result" == *"sinks=kafka,victoria_metrics,victoria_logs"* ]]; then
    echo "✅ PASS: All three sinks normalized correctly"
    echo "   Result: $result"
else
    echo "❌ FAIL: Should have normalized to sinks=kafka,victoria_metrics,victoria_logs"
    echo "   Result: $result"
fi
echo ""

echo "Test 6: Separate flags (-e kafka -e victoria_metrics)"
echo "Expected: Both normalized to kafka=true and victoria_metrics=true"
echo "----------------------------------------"
result=$(bash -c 'source src/main/omnia.sh 2>/dev/null; args=("-e" "kafka" "-e" "victoria_metrics"); normalize_extra_args args; echo "${args[@]}"' 2>/dev/null)
if [[ "$result" == *"kafka=true"* ]] && [[ "$result" == *"victoria_metrics=true"* ]]; then
    echo "✅ PASS: Separate flags normalized correctly"
    echo "   Result: $result"
else
    echo "❌ FAIL: Should have normalized both to true"
    echo "   Result: $result"
fi
echo ""

echo "Test 7: Case variation - Kafka (capital K)"
echo "Expected: Normalized to Kafka=true"
echo "----------------------------------------"
result=$(bash -c 'source src/main/omnia.sh 2>/dev/null; args=("-e" "Kafka"); normalize_extra_args args; echo "${args[@]}"' 2>/dev/null)
if [[ "$result" == *"Kafka=true"* ]]; then
    echo "✅ PASS: Case variation handled correctly"
    echo "   Result: $result"
else
    echo "❌ FAIL: Should have normalized Kafka=true"
    echo "   Result: $result"
fi
echo ""

echo "Test 8: Other -e arguments pass through (-e delete_sinks_volume=true)"
echo "Expected: Pass through unchanged"
echo "----------------------------------------"
result=$(bash -c 'source src/main/omnia.sh 2>/dev/null; args=("-e" "delete_sinks_volume=true"); normalize_extra_args args; echo "${args[@]}"' 2>/dev/null)
if [[ "$result" == *"delete_sinks_volume=true"* ]]; then
    echo "✅ PASS: Other -e arguments pass through unchanged"
    echo "   Result: $result"
else
    echo "❌ FAIL: Other -e arguments should pass through"
    echo "   Result: $result"
fi
echo ""

echo "=========================================="
echo "Verification Complete"
echo "=========================================="
