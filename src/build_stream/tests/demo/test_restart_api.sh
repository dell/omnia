#!/bin/bash
# Restart API Test Script
BASE="https://100.10.0.80:8010"
AUTH=$(echo -n "dell1234:dell1234" | base64)

echo "=== Step 1: Register client ==="
CLIENT_RESPONSE=$(curl -sk -X POST "$BASE/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic $AUTH" \
  -d "{\"client_name\":\"restart-test\",\"allowed_scopes\":[\"job:write\"],\"grant_types\":[\"client_credentials\"]}")
echo "$CLIENT_RESPONSE" | jq .
CLIENT_ID=$(echo "$CLIENT_RESPONSE" | jq -r ".client_id")
CLIENT_SECRET=$(echo "$CLIENT_RESPONSE" | jq -r ".client_secret")
echo "CLIENT_ID: $CLIENT_ID"
echo "CLIENT_SECRET: $CLIENT_SECRET"

echo ""
echo "=== Step 2: Get token ==="
TOKEN_RESPONSE=$(curl -sk -X POST "$BASE/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=$CLIENT_ID&client_secret=$CLIENT_SECRET")
ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r ".access_token")
echo "Token: ${ACCESS_TOKEN:0:20}..."

echo ""
echo "=== Step 3: Create job ==="
IDEM_KEY=$(uuidgen)
JOB_RESPONSE=$(curl -sk -X POST "$BASE/api/v1/jobs" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $IDEM_KEY" \
  -d "{\"client_id\":\"$CLIENT_ID\"}")
echo "$JOB_RESPONSE" | jq .
JOB_ID=$(echo "$JOB_RESPONSE" | jq -r ".job_id")
echo "JOB_ID: $JOB_ID"

echo ""
echo "=== TEST 1: Trigger restart (expect 202) ==="
curl -sk -o /tmp/resp1.json -w "HTTP Status: %{http_code}\n" \
  -X POST "$BASE/api/v1/jobs/$JOB_ID/stages/restart" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
cat /tmp/resp1.json | jq .

echo ""
echo "=== TEST 2: Duplicate restart (expect 409) ==="
curl -sk -o /tmp/resp2.json -w "HTTP Status: %{http_code}\n" \
  -X POST "$BASE/api/v1/jobs/$JOB_ID/stages/restart" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
cat /tmp/resp2.json | jq .

echo ""
echo "=== TEST 3: Invalid job ID (expect 400) ==="
curl -sk -o /tmp/resp3.json -w "HTTP Status: %{http_code}\n" \
  -X POST "$BASE/api/v1/jobs/not-valid/stages/restart" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
cat /tmp/resp3.json | jq .

echo ""
echo "=== TEST 4: Non-existent job (expect 404) ==="
FAKE_ID=$(uuidgen)
curl -sk -o /tmp/resp4.json -w "HTTP Status: %{http_code}\n" \
  -X POST "$BASE/api/v1/jobs/$FAKE_ID/stages/restart" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
cat /tmp/resp4.json | jq .

echo ""
echo "=== TEST 5: No auth (expect 401) ==="
curl -sk -o /tmp/resp5.json -w "HTTP Status: %{http_code}\n" \
  -X POST "$BASE/api/v1/jobs/$JOB_ID/stages/restart"
cat /tmp/resp5.json | jq .

echo ""
echo "=== Check playbook queue ==="
for dir in /dell/omnia/playbook_queue/requests /dell/omnia/playbook_queue/processing /dell/omnia/omnia/playbook_queue/requests /dell/omnia/omnia/playbook_queue/processing; do
  if [ -d "$dir" ]; then
    echo "Found: $dir"
    ls -la "$dir"
  fi
done
