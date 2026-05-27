# Security Test Runner Guide

## Purpose

This guide explains how to run the security testing script for the Secure Exam System and how to interpret the results.

Script path:
- backend/tools/security_test_runner.sh

## What The Script Tests

The script runs controlled security simulations and reports pass or fail for each case.

### 1) Brute-force and rate-limit testing

If you enter only username and leave password empty, the script runs repeated login attempts to validate rate limiting.

Checks include:
- repeated incorrect password attempts
- rate-limit trigger detection (HTTP 429)
- summary of 401, 429, 200, and other responses

### 2) Validation and injection testing

If you enter both username and password, the script first logs in and then runs broader attack simulations.

Checks include:
- NoSQL operator payloads (example: $ne, $where, $regex, $expr)
- XSS payload patterns (script tag, event handler, javascript URI)
- input size abuse (oversized fields)
- nested payload abuse (deep object and array structures)
- control payloads expected to pass as safe input

### 3) Endpoint hardening checks

Checks include:
- protected endpoint access without JWT
- invalid JWT rejection
- wrong HTTP method behavior (GET on POST-only endpoint)
- malformed JSON handling

### 4) Auth abuse checks

Checks include:
- unexpected object/script values in auth fields
- empty credential payload behavior
- basic username enumeration consistency check

## Requirements

- Backend server must be running.
- Curl must be available in the shell.
- Use Git Bash or WSL for this .sh script.

## Run Instructions

From repository root:

```bash
cd backend/tools
bash security_test_runner.sh
```

You will be prompted:
- Enter username
- Enter password (leave blank for brute-force mode)

## Environment Variables

You can override defaults:

```bash
BASE_URL=http://localhost:5000 BRUTE_FORCE_ATTEMPTS=120 bash backend/tools/security_test_runner.sh
```

Variables:
- BASE_URL: backend base URL (default: http://localhost:5000)
- BRUTE_FORCE_ATTEMPTS: number of brute-force login attempts (default: 40)
- AUTH_USERNAME: optional non-interactive username
- AUTH_PASSWORD: optional non-interactive password
- JWT_TOKEN: optional token for validation tests

## Understanding Results

Per test output includes:
- attack id, category, attack name
- expected behavior
- HTTP status
- input payload
- output response body

Final summary includes:
- total tests
- passed tests
- failed tests
- score percentage

For brute-force mode, summary includes:
- attempts
- rate limited (429)
- unauthorized (401)
- successful (200)
- other responses

A high 429 count after repeated attempts indicates rate limiting is working.

## Troubleshooting

### Backend unreachable

If you see connection errors such as:
- Failed to connect to localhost

Actions:
- confirm backend is running
- confirm port in BASE_URL (5000 vs 5500)

### Bash not available in PowerShell

If PowerShell cannot run bash, use:
- Git Bash terminal
- WSL terminal

### Login failures in full suite mode

If username and password are provided but login fails:
- verify credentials
- verify account exists and is active

## Notes For Information Security Report

Recommended evidence to include:
- brute-force run showing transition from 401 to 429
- summary section with pass/fail counts
- examples of blocked injection payloads and responses
- short explanation of how rate limiting mitigates credential stuffing attacks
