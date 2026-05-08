# IS-Lab Project: Secure Online Examination System

Semester Project for a secure, modular, and scalable web-based online examination system.

## 1. Project Title

Secure Online Examination System with Multi-Layer Security & Behavioral Risk Detection
See [installation.md](installation.md) for full setup and run instructions.

## 2. Project Objective

The objective of this project is to design and develop a secure, modular, and scalable web-based online examination system that enforces academic integrity by implementing core information security concepts, including:

- Authentication and authorization
- Access control
- Secure session management
- Data integrity and confidentiality
- Monitoring and auditing
- Threat detection and prevention
- Risk-based security analysis

This project simulates a real-world secure system, where the primary focus is implementing security mechanisms, not just building features.

## 3. Project Vision

To build a complete working web application where:

- Students can attempt exams securely
- Teachers can monitor behavior
- Suspicious activity is detected and logged
- Security risks are analyzed and reported

## 4. Problem Statement

Online examination systems commonly suffer from:

- Tab switching and multitasking
- Use of unauthorized tools
- Credential sharing
- Multiple logins
- Copying and collusion
- Lack of monitoring
- No audit trails
- No log integrity

This project addresses these issues using a multi-layered security architecture.

## 5. System Overview

### Student Interface

- Secure login
- Device verification
- Exam participation
- Answer submission

### Teacher Interface

- Student approval
- Monitoring dashboard
- Activity logs
- Risk reports

## 6. Security-Centric Development Requirement

Every module must implement:

- A clear security concept
- A real-world threat scenario
- A practical defense mechanism

Each group must answer:

- What security problem is solved?
- What attack is prevented?
- How is it implemented?

Modules without security focus will be rejected.

## 7. System Architecture

```text
Web Frontend (React.js)
				|
				v
Backend API Server (Flask)
				|
				v
Independent Security Modules (17)
				|
				v
MongoDB + Logs + Security Engine
```

## 8. Development Approach

- Each group develops one security module
- Modules communicate via APIs only
- Final system = all modules integrated into one app

## 9. Technology Stack

### Frontend (Web)

- React.js

### Backend

- Python (Flask)

### Database

- MongoDB

### Security Tools

- JWT for authentication
- bcrypt for password hashing
- SHA-256 for log integrity

### AI/ML

- Scikit-learn
- TF-IDF / cosine similarity

## 10. Module Independence Rule

Each module must:

- Work independently
- Provide APIs
- Not depend on internal code of other modules
- Be integration-ready

## 11. Module Distribution

### Access Control and Authentication

- Module 1: Secure Authentication - password hashing (bcrypt), OTP-based MFA
- Module 2: Secure Session Management - JWT tokens, session expiration
- Module 3: Device Fingerprinting - device binding, prevent account sharing
- Module 4: Activation Code Security - one-time tokens, time-based validation
- Module 5: RBAC - role-based authorization

### System and Exam Security

- Module 6: Secure Question Delivery - confidential API access
- Module 7: Question Randomization - anti-collusion
- Module 8: Secure Timer - server-side timing
- Module 9: Input Validation - injection prevention

### Monitoring and Auditing

- Module 10: Tab Monitoring - detect app switching
- Module 11: Clipboard Monitoring - prevent data leakage
- Module 12: Activity Logging - audit trails
- Module 13: Secure Logging - SHA-256 log integrity

### Threat Detection

- Module 14: Multi-Session Detection - prevent multiple logins
- Module 15: Behavioral Analysis - rule-based anomaly detection
- Module 16: Answer Similarity Detection - detect copying
- Module 17: Risk Scoring and Dashboard - security analytics

## 12. API Standard

All modules should follow the shared API convention:

```http
POST /api/module/action
GET /api/module/action
```

Standard response:

```json
{
	"status": "success",
	"data": {},
	"message": ""
}
```

## 13. Database Design

Collections:

- users
- devices
- exams
- questions
- responses
- logs
- risk_scores

## 14. System Workflow

1. Student logs in
2. Device verification
3. Teacher approval
4. Activation code validation
5. Exam starts
6. Monitoring begins
7. Logs generated
8. Answers submitted
9. Security analysis
10. Risk score generated

## 15. Security Features

- Authentication and MFA
- Authorization (RBAC)
- Session control
- Device binding
- Input validation
- Monitoring
- Secure logging
- Risk scoring

## 16. AI Usage Policy

AI is not the focus.

Allowed:

- TF-IDF
- Cosine similarity
- Rule-based logic

Focus: security implementation.

## 17. Risk Score Example

Risk score formula example:

```text
Risk Score = (0.3 x Tab Switches) +
						 (0.2 x Idle Time) +
						 (0.3 x Similarity Score) +
						 (0.2 x Fast Answering)
```

## 18. Project Timeline

- Proposal after mids
- Development during lab sessions
- Integration phase at end

## 19. Integration Plan

- One shared GitHub repository
- Each group works on a separate module
- Final integration phase

## 20. Final System Requirement

At the end of the semester, the class must deliver one complete web application.

The application must:

- Be fully functional
- Integrate all modules
- Work in a real-life scenario
- Include student and teacher panels

Not allowed:

- Separate apps per group
- Incomplete modules
- Dummy implementations

Required:

- Full integration
- Real data flow
- Working APIs
- End-to-end functionality

## 21. Deliverables

### Each Group

- Module implementation
- API documentation
- Source code
- Demo
- Security explanation

### Whole Class

- Complete web application
- Backend system
- Integrated modules
- Final demo

## 22. Rules

- Use open-source tools only
- No plagiarism
- Follow API standards
- Must implement security logic
- Must support integration

## 23. Limitations

- No second-device detection
- No webcam proctoring
- Device-level limitations

## 24. Bonus

- Real-time monitoring
- WebSockets
- Advanced detection
- UI improvements

## 25. Evaluation Criteria

| Component | Marks |
| --- | ---: |
| Security implementation | 10 |
| Concept understanding | 10 |
| Functionality | 10 |
| Integration | 10 |
| Documentation and presentation | 10 |

## 26. Final Note to Students

This is not just an app development project. It is a security engineering project.

Focus on:

- Real-world threats
- Practical defenses
- Secure coding
- System integration

## 27. Integration Contract

This section defines the rules for integrating all 17 modules into one application.

### 27.1 Shared JWT Token Specification

Module 1 (Secure Authentication) is the only module that issues JWT tokens.
All other modules must accept and validate the same JWT format.

JWT structure:

```json
{
	"header": {
		"alg": "HS256",
		"typ": "JWT"
	},
	"payload": {
		"user_id": "string",
		"username": "string",
		"role": "student | teacher",
		"session_id": "string",
		"device_fingerprint_hash": "string",
		"exp": "timestamp"
	}
}
```

Validation rule: every API endpoint except login and registration must:

1. Extract JWT from `Authorization: Bearer <token>`
2. Verify signature using a shared secret key provided by the instructor
3. Check expiration
4. Reject with HTTP 401 if validation fails

### 27.2 Standard HTTP Error Responses

| Status | Meaning | When to use |
| --- | --- | --- |
| 200 | Success | Request processed correctly |
| 400 | Bad Request | Missing or invalid parameters |
| 401 | Unauthorized | Invalid or missing JWT |
| 403 | Forbidden | Valid JWT but insufficient permissions |
| 404 | Not Found | Resource does not exist |
| 409 | Conflict | State violation |
| 500 | Internal Error | Module crashed or dependency failed |
| 503 | Service Unavailable | Dependent module is down |

Error response format:

```json
{
	"status": "error",
	"error_code": 401,
	"message": "JWT expired",
	"timestamp": "2024-01-15T10:30:00Z"
}
```

### 27.3 Logging Gateway

All modules must send logs to a single logging endpoint.

## Generating a JWT Secret

Generate a secure JWT secret and add it to `backend/.env` as `JWT_SECRET`.

Use the included helper script to create a secret:

```bash
python backend/tools/generate_jwt_secret.py --bytes 32 --format urlsafe
```

Then add the output value to your `backend/.env` file:

```env
JWT_SECRET=PASTE_GENERATED_SECRET_HERE
```

Recommended: keep this secret private and rotate periodically.

Endpoint:

```http
POST /api/logs/write
```

Request body:

```json
{
	"module": "Module_10_TabMonitor",
	"level": "INFO | WARNING | ERROR | SECURITY",
	"user_id": "string",
	"exam_id": "string",
	"action": "tab_switch_detected",
	"details": {},
	"timestamp": "ISO8601"
}
```

Response: HTTP 202 Accepted.

No module is allowed to write directly to the MongoDB logs collection.

### 27.4 Exam State Machine

All exam-related modules must respect this state machine:

```text
NOT_STARTED -> DEVICE_VERIFIED -> TEACHER_APPROVED ->
ACTIVATION_VALID -> IN_PROGRESS -> SUBMITTED -> ANALYZING -> COMPLETED
```

State transition rules:

- Timer (Module 8) only runs during `IN_PROGRESS`
- Monitoring (Modules 10-13) only active during `IN_PROGRESS`
- Answer submission only allowed during `IN_PROGRESS`
- Risk scoring (Module 17) runs during `ANALYZING`

API endpoint for state: `GET /api/exam/state/{exam_id}`

### 27.5 Health Check Requirement

Every module must implement:

```http
GET /api/module/health
```

Response:

```json
{
	"module": "Module_1_Auth",
	"status": "healthy",
	"dependencies": ["mongodb"],
	"version": "1.0.0"
}
```

If a module is unhealthy, dependent modules must return HTTP 503.

### 27.6 Shared Database Configuration

All modules must connect to the same MongoDB instance:

```text
mongodb://localhost:27017/exam_security
```

No module may use a different database name or port.

### 27.7 Risk Data Aggregation Schema

For Module 17 to work, Modules 10, 11, 12, 14, 15, and 16 must provide:

```http
GET /api/module/risk-data?user_id={id}&exam_id={id}
```

Response:

```json
{
	"module": "Module_10_TabMonitor",
	"data": [
		{
			"user_id": "string",
			"exam_id": "string",
			"timestamp": "ISO8601",
			"metric": "tab_switch_count",
			"value": 3
		}
	]
}
```

### 27.8 Integration Testing Requirements

Before final submission, each module must pass:

1. JWT test: call your API with an expired JWT and receive HTTP 401
2. Logging test: generate a log and verify it appears in the shared logs collection
3. Health test: `GET /health` returns 200 within 1 second
4. State test: attempt an exam action in the wrong state and receive HTTP 409

## 28. Current Status

- Module 1: Secure Authentication - done
- Other modules: pending integration

## 29. Repository Notes

- Backend: Flask API in `backend/`
- Frontend: Web client planned in `frontend/`
- Shared configuration and security policy should remain consistent across modules

## 30. How to Run the Project

See [installation.md](installation.md) for full setup and run instructions.
