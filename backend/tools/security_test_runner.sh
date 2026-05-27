#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:5000}"
TOKEN="${JWT_TOKEN:-}"
AUTH_USERNAME="${AUTH_USERNAME:-}"
AUTH_PASSWORD="${AUTH_PASSWORD:-}"
BRUTE_FORCE_ATTEMPTS="${BRUTE_FORCE_ATTEMPTS:-40}"

VALIDATION_URL="${BASE_URL%/}/api/validation/check"
LOGIN_URL="${BASE_URL%/}/api/auth/login"
HEALTH_URL="${BASE_URL%/}/api/health"

PASSED=0
FAILED=0
TOTAL=0

print_header() {
  echo "==============================================="
  echo " Secure Exam System - Terminal Security Tests "
  echo "==============================================="
  echo "Base URL: ${BASE_URL}"
  echo
}

check_server_reachable() {
  if ! curl -sS --max-time 4 "$HEALTH_URL" >/dev/null 2>&1; then
    echo "ERROR: Backend is not reachable at $BASE_URL"
    echo "Start the server first, or set BASE_URL to the correct host/port."
    echo "Example: BASE_URL=http://localhost:5000 bash backend/tools/security_test_runner.sh"
    exit 1
  fi
}

prompt_inputs() {
  if [[ -z "$AUTH_USERNAME" ]]; then
    read -r -p "Enter username: " AUTH_USERNAME
  fi

  if [[ -z "$AUTH_PASSWORD" ]]; then
    read -r -s -p "Enter password (leave blank to run brute-force simulation): " AUTH_PASSWORD
    echo
  fi
}

extract_http_status() {
  local body_and_status="$1"
  printf '%s\n' "$body_and_status" | sed -n 's/^__HTTP_STATUS__:\([0-9][0-9][0-9]\)$/\1/p'
}

extract_http_body() {
  local body_and_status="$1"
  printf '%s\n' "$body_and_status" | sed '/^__HTTP_STATUS__:[0-9][0-9][0-9]$/d'
}

json_escape() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  printf '%s' "$value"
}

build_login_payload() {
  local username="$1"
  local password="$2"
  printf '{"username":"%s","password":"%s"}' "$(json_escape "$username")" "$(json_escape "$password")"
}

run_request() {
  local method="$1"
  local url="$2"
  local payload="$3"
  local content_type="$4"
  local auth_mode="$5"

  local -a cmd
  cmd=(curl -sS -X "$method" "$url")

  if [[ "$content_type" != "none" ]]; then
    cmd+=(-H "Content-Type: $content_type")
  fi

  case "$auth_mode" in
    bearer)
      cmd+=(-H "Authorization: Bearer $TOKEN")
      ;;
    invalid)
      cmd+=(-H "Authorization: Bearer invalid.invalid.invalid")
      ;;
    none)
      ;;
    *)
      echo "ERROR: Unknown auth mode: $auth_mode" >&2
      exit 1
      ;;
  esac

  if [[ "$payload" != "__NO_BODY__" ]]; then
    cmd+=(-d "$payload")
  fi

  cmd+=(-w '\n__HTTP_STATUS__:%{http_code}')
  "${cmd[@]}"
}

ensure_token() {
  if [[ -n "$TOKEN" ]]; then
    return 0
  fi

  if [[ -z "$AUTH_USERNAME" || -z "$AUTH_PASSWORD" ]]; then
    echo "ERROR: Provide JWT_TOKEN or AUTH_USERNAME and AUTH_PASSWORD."
    echo "Example:"
    echo "  JWT_TOKEN=<token> ./backend/tools/security_test_runner.sh"
    echo "  AUTH_USERNAME=student01 AUTH_PASSWORD=strong-password ./backend/tools/security_test_runner.sh"
    exit 1
  fi

  local login_payload
  login_payload=$(build_login_payload "$AUTH_USERNAME" "$AUTH_PASSWORD")

  local login_result
  login_result=$(curl -sS -X POST "$LOGIN_URL" \
    -H "Content-Type: application/json" \
    -d "$login_payload" \
    -w '\n__HTTP_STATUS__:%{http_code}')

  local login_status
  login_status=$(extract_http_status "$login_result")
  local login_body
  login_body=$(extract_http_body "$login_result")

  if [[ "$login_status" != "200" ]]; then
    echo "ERROR: Login failed (HTTP $login_status)."
    echo "Response: $login_body"
    exit 1
  fi

  TOKEN=$(printf '%s' "$login_body" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')
  if [[ -z "$TOKEN" ]]; then
    echo "ERROR: Could not extract token from login response."
    echo "Response: $login_body"
    exit 1
  fi
}

run_bruteforce_suite() {
  if [[ -z "$AUTH_USERNAME" ]]; then
    echo "ERROR: Username is required for brute-force simulation."
    exit 1
  fi

  echo
  echo "Running brute-force simulation against rate limit controls"
  echo "Target username: $AUTH_USERNAME"
  echo "Attempt count: $BRUTE_FORCE_ATTEMPTS"
  echo

  local -a common_passwords=(
    "123456"
    "password"
    "password123"
    "qwerty"
    "letmein"
    "admin"
    "welcome123"
    "exam123"
    "student123"
    "secure123"
  )

  local rate_limited=0
  local unauthorized=0
  local success=0
  local other=0
  local attempt=1

  while [[ "$attempt" -le "$BRUTE_FORCE_ATTEMPTS" ]]; do
    local guess
    if [[ "$attempt" -le "${#common_passwords[@]}" ]]; then
      guess="${common_passwords[$((attempt - 1))]}"
    else
      guess="guess${attempt}"
    fi

    local payload
    payload=$(build_login_payload "$AUTH_USERNAME" "$guess")

    local result
    result=$(run_request "POST" "$LOGIN_URL" "$payload" "application/json" "none")

    local status
    status=$(extract_http_status "$result")
    local body
    body=$(extract_http_body "$result")

    case "$status" in
      429)
        rate_limited=$((rate_limited + 1))
        ;;
      401)
        unauthorized=$((unauthorized + 1))
        ;;
      200)
        success=$((success + 1))
        ;;
      *)
        other=$((other + 1))
        ;;
    esac

    echo "[attempt $attempt/$BRUTE_FORCE_ATTEMPTS] password=$guess | http_status=$status"
    echo "  input: $payload"
    echo "  output: $body"
    echo

    attempt=$((attempt + 1))
  done

  echo "==============================================="
  echo " Brute-Force Summary"
  echo "==============================================="
  echo "Attempts:            $BRUTE_FORCE_ATTEMPTS"
  echo "Rate limited (429):  $rate_limited"
  echo "Unauthorized (401):  $unauthorized"
  echo "Successful (200):    $success"
  echo "Other responses:     $other"

  if [[ "$rate_limited" -gt 0 ]]; then
    echo "Result: PASSED - rate limiting blocked repeated login attempts."
  else
    echo "Result: WARNING - no 429 responses seen. Check rate limit configuration."
  fi
}

run_status_case() {
  local attack_id="$1"
  local category="$2"
  local attack_name="$3"
  local expected_status_regex="$4"
  local method="$5"
  local url="$6"
  local payload="$7"
  local content_type="$8"
  local auth_mode="$9"

  TOTAL=$((TOTAL + 1))

  local result
  result=$(run_request "$method" "$url" "$payload" "$content_type" "$auth_mode")

  local status
  status=$(extract_http_status "$result")
  local body
  body=$(extract_http_body "$result")

  local verdict="failed"
  if [[ "$status" =~ ^(${expected_status_regex})$ ]]; then
    verdict="passed"
    PASSED=$((PASSED + 1))
  else
    FAILED=$((FAILED + 1))
  fi

  echo "[$verdict] $attack_id | $category | $attack_name"
  echo "  expected_http_status: $expected_status_regex"
  echo "  http_status: $status"
  echo "  input: method=$method url=$url payload=$payload"
  echo "  output: $body"
  echo
}

run_enum_case() {
  local known_username="$1"
  local unknown_username="ghost_user_$(date +%s)"
  local probe_password="definitely-wrong-password"

  TOTAL=$((TOTAL + 1))

  local known_payload
  known_payload=$(build_login_payload "$known_username" "$probe_password")
  local unknown_payload
  unknown_payload=$(build_login_payload "$unknown_username" "$probe_password")

  local known_result
  known_result=$(run_request "POST" "$LOGIN_URL" "$known_payload" "application/json" "none")
  local unknown_result
  unknown_result=$(run_request "POST" "$LOGIN_URL" "$unknown_payload" "application/json" "none")

  local known_status
  known_status=$(extract_http_status "$known_result")
  local unknown_status
  unknown_status=$(extract_http_status "$unknown_result")

  local known_body
  known_body=$(extract_http_body "$known_result")
  local unknown_body
  unknown_body=$(extract_http_body "$unknown_result")

  local verdict="failed"
  if [[ "$known_status" == "$unknown_status" ]]; then
    verdict="passed"
    PASSED=$((PASSED + 1))
  else
    FAILED=$((FAILED + 1))
  fi

  echo "[$verdict] auth-user-enumeration | Auth Abuse | Username enumeration consistency"
  echo "  expected: same response code pattern for known and unknown users"
  echo "  input_known: $known_payload"
  echo "  input_unknown: $unknown_payload"
  echo "  output_known: status=$known_status body=$known_body"
  echo "  output_unknown: status=$unknown_status body=$unknown_body"
  echo
}

run_case() {
  local attack_id="$1"
  local category="$2"
  local attack_name="$3"
  local expected_blocked="$4"
  local payload="$5"

  TOTAL=$((TOTAL + 1))

  local result
  result=$(run_request "POST" "$VALIDATION_URL" "$payload" "application/json" "bearer")

  local status
  status=$(extract_http_status "$result")
  local body
  body=$(extract_http_body "$result")

  local blocked="unknown"
  if printf '%s' "$body" | grep -Eq '"is_valid"[[:space:]]*:[[:space:]]*false'; then
    blocked="true"
  elif printf '%s' "$body" | grep -Eq '"is_valid"[[:space:]]*:[[:space:]]*true'; then
    blocked="false"
  fi

  local verdict="failed"
  if [[ "$status" == "200" && "$blocked" == "$expected_blocked" ]]; then
    verdict="passed"
    PASSED=$((PASSED + 1))
  else
    FAILED=$((FAILED + 1))
  fi

  echo "[$verdict] $attack_id | $category | $attack_name"
  echo "  expected_blocked: $expected_blocked"
  echo "  http_status: $status"
  echo "  input: $payload"
  echo "  output: $body"
  echo
}

print_summary() {
  local score="0.00"
  if [[ "$TOTAL" -gt 0 ]]; then
    score=$(awk "BEGIN { printf \"%.2f\", ($PASSED/$TOTAL)*100 }")
  fi

  echo "==============================================="
  echo " Summary"
  echo "==============================================="
  echo "Total:  $TOTAL"
  echo "Passed: $PASSED"
  echo "Failed: $FAILED"
  echo "Score:  ${score}%"
}

run_validation_suite() {
  local payload

  payload='{"username":{"$ne":null},"password":"anything"}'
  run_case "nosql-operator-ne" "NoSQL Injection" "NoSQL operator injection (\$ne)" "true" "$payload"

  payload='{"filter":{"$where":"this.score > 90"}}'
  run_case "nosql-where" "NoSQL Injection" "NoSQL JavaScript execution (\$where)" "true" "$payload"

  payload='{"query":{"$regex":".*"}}'
  run_case "nosql-regex" "NoSQL Injection" "NoSQL regex operator injection" "true" "$payload"

  payload='{"query":{"$expr":{"$gt":[1,0]}}}'
  run_case "nosql-expr" "NoSQL Injection" "NoSQL expression operator injection" "true" "$payload"

  payload='{"answer":"<script>alert(\"xss\")</script>"}'
  run_case "xss-script" "XSS" "XSS script tag injection" "true" "$payload"

  payload='{"bio":"<img src=\"x\" onerror=\"alert(1)\">"}'
  run_case "xss-event-handler" "XSS" "XSS event handler payload" "true" "$payload"

  payload='{"bio":"<svg onload=\"alert(1)\"></svg>"}'
  run_case "xss-svg-onload" "XSS" "XSS SVG onload payload" "true" "$payload"

  payload='{"link":"javascript:alert(1)"}'
  run_case "xss-js-uri" "XSS" "javascript: URI payload" "true" "$payload"

  payload='{"essay":"'
  payload+="$(printf 'A%.0s' {1..2101})"
  payload+='"}'
  run_case "oversized-field" "Input Size" "Oversized field payload" "true" "$payload"

  payload='{"nested":[[[[[[["boom"]]]]]]]}'
  run_case "nested-array-depth" "Structure Abuse" "Excessive nested array payload" "true" "$payload"

  payload='{"next":{"next":{"next":{"next":{"next":{"next":{"value":"safe"}}}}}}}'
  run_case "deep-nesting" "Structure Abuse" "Excessive JSON nesting" "true" "$payload"

  payload='{"comment":"drop db; --"}'
  run_case "sqli-style-string" "Injection" "SQL-style injection probe in text" "false" "$payload"

  payload='{"student_id":"S-001","answer":"normal safe answer"}'
  run_case "benign-safe-1" "Control" "Benign payload control sample 1" "false" "$payload"

  payload='{"candidate_id":"CAND-001","answer":"The capital is Paris."}'
  run_case "benign-control" "Control" "Benign payload control sample" "false" "$payload"

  payload='{"essay":"Unicode test: مرحبا 你好 hello"}'
  run_case "benign-unicode" "Control" "Benign Unicode text payload" "false" "$payload"
}

run_endpoint_hardening_suite() {
  run_status_case \
    "jwt-missing-validation" \
    "Auth Bypass" \
    "Validation endpoint without JWT" \
    "401" \
    "POST" \
    "$VALIDATION_URL" \
    '{"answer":"hello"}' \
    "application/json" \
    "none"

  run_status_case \
    "jwt-invalid-validation" \
    "Auth Bypass" \
    "Validation endpoint with invalid JWT" \
    "401" \
    "POST" \
    "$VALIDATION_URL" \
    '{"answer":"hello"}' \
    "application/json" \
    "invalid"

  run_status_case \
    "method-tamper-login-get" \
    "Protocol Abuse" \
    "GET on POST-only /api/auth/login" \
    "404|405" \
    "GET" \
    "$LOGIN_URL" \
    "__NO_BODY__" \
    "none" \
    "none"

  run_status_case \
    "method-tamper-validation-get" \
    "Protocol Abuse" \
    "GET on POST-only /api/validation/check" \
    "404|405" \
    "GET" \
    "$VALIDATION_URL" \
    "__NO_BODY__" \
    "none" \
    "bearer"

  run_status_case \
    "login-malformed-json" \
    "Parser Abuse" \
    "Malformed JSON to login endpoint" \
    "400|401|429" \
    "POST" \
    "$LOGIN_URL" \
    '{"username":"student"' \
    "application/json" \
    "none"

  local big_payload
  big_payload='{"username":"student","password":"'
  big_payload+="$(printf 'B%.0s' {1..2500})"
  big_payload+='"}'
  run_status_case \
    "login-oversized-password" \
    "Input Size" \
    "Oversized password payload to login" \
    "400|401|429" \
    "POST" \
    "$LOGIN_URL" \
    "$big_payload" \
    "application/json" \
    "none"
}

run_auth_abuse_suite() {
  run_status_case \
    "login-nosql-object-username" \
    "Auth Abuse" \
    "NoSQL object sent as username" \
    "400|401|429" \
    "POST" \
    "$LOGIN_URL" \
    '{"username":{"$ne":null},"password":"x"}' \
    "application/json" \
    "none"

  run_status_case \
    "login-script-username" \
    "Auth Abuse" \
    "Script payload in username field" \
    "400|401|429" \
    "POST" \
    "$LOGIN_URL" \
    '{"username":"<script>alert(1)</script>","password":"x"}' \
    "application/json" \
    "none"

  run_status_case \
    "login-empty-credentials" \
    "Auth Abuse" \
    "Empty JSON object to login" \
    "400|401|429" \
    "POST" \
    "$LOGIN_URL" \
    '{}' \
    "application/json" \
    "none"

  run_enum_case "$AUTH_USERNAME"
}

main() {
  print_header
  check_server_reachable
  prompt_inputs

  if [[ -n "$AUTH_USERNAME" && -z "$AUTH_PASSWORD" ]]; then
    run_bruteforce_suite
    return 0
  fi

  ensure_token
  run_validation_suite
  run_endpoint_hardening_suite
  run_auth_abuse_suite
  print_summary
}

main "$@"
