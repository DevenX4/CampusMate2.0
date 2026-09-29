# CampusMate Backend Frontend Integration Guide

This guide documents the API contract, authentication mechanism, request/response models, and endpoint details required for integrating a web or mobile frontend with the CampusMate AI backend.

---

## 1. Base URL & Development Setup

- **Development Base URL**: `http://127.0.0.1:8000/api/v1`
- **Interactive OpenAPI Documentation (Swagger)**: `http://127.0.0.1:8000/docs`
- **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`
- **OpenAPI Schema**: `http://127.0.0.1:8000/openapi.json`

---

## 2. Authentication & Session Management

CampusMate uses dual session authentication:
1. **Cookie-based (Browsers)**: An `HttpOnly`, `SameSite=Lax` cookie named `campusmate_session` is set on login.
2. **Bearer Token (API Clients)**: An `access_token` string is returned in the `POST /auth/login` JSON body and accepted via `Authorization: Bearer <token>`.

### Key Endpoints

#### Login: `POST /api/v1/auth/login`
- **Auth Required**: None
- **Request Body**:
  ```json
  {
    "username": "student",
    "password": "student@123"
  }
  ```
- **Response (`200 OK`)**:
  ```json
  {
    "access_token": "px2Lzebvz5rzJO6U...",
    "expires_at": "2026-09-30T10:48:09.569123Z",
    "user": {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "email": "student@campusmate-demo.example",
      "username": "student",
      "full_name": "Demo Student",
      "role": "student",
      "is_active": true,
      "created_at": "2026-09-29T22:48:09.569123Z"
    }
  }
  ```

#### Logout: `POST /api/v1/auth/logout`
- **Auth Required**: Optional (Clears session and cookie)
- **Response**: `204 No Content`

#### Current User Profile: `GET /api/v1/auth/me`
- **Auth Required**: Authenticated User
- **Response (`200 OK`)**:
  ```json
  {
    "user": {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "email": "student@campusmate-demo.example",
      "username": "student",
      "full_name": "Demo Student",
      "role": "student",
      "is_active": true,
      "created_at": "2026-09-29T22:48:09.569123Z"
    },
    "permissions": ["chat:use", "catalog:read"]
  }
  ```

#### Demo Accounts (Development Only): `GET /api/v1/auth/demo`
- **Auth Required**: None
- **Response (`200 OK`)**: Lists active demo accounts (`admin`, `student`) and public credentials.

---

## 3. Frontend Fetch Credentials Requirement

Because session tokens are stored in an `HttpOnly` cookie (`campusmate_session`), browser `fetch()` calls from the React frontend MUST specify:

```javascript
credentials: "include"
```

### Example Frontend Request (`fetch`)

```javascript
const response = await fetch("http://127.0.0.1:8000/api/v1/chat/query", {
  method: "POST",
  credentials: "include", // Essential for session cookie transmission
  headers: {
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    question: "What is 2CEIT602 and how many credits does it have?"
  })
});

const data = await response.json();
```

---

## 4. Chat Endpoint: `POST /api/v1/chat/query`

Answers user questions strictly from CampusMate's authoritative knowledge base.

- **Method**: `POST`
- **Path**: `/api/v1/chat/query`
- **Auth Required**: Guest / Authenticated User (with `chat:use` permission)
- **Request Body**:
  ```json
  {
    "question": "What is the attendance requirement for exams?",
    "program_id": null,
    "semester_id": null
  }
  ```
- **Response (`200 OK`)**:
  ```json
  {
    "query_id": "adb0cb89-fb30-46ee-8155-189b079f0272",
    "question": "What is the attendance requirement for exams?",
    "answer": "Students must maintain at least 75% attendance in all courses to be eligible for end semester examinations. [DOC-ATT-001, p.1].",
    "answer_type": "fallback",
    "contains_synthetic": false,
    "route": "documents",
    "intents": ["documents"],
    "reasons": ["no structured intent: hybrid retrieval"],
    "tables": [],
    "sources": [
      {
        "ref": 1,
        "kind": "document",
        "source_type": "official",
        "cited": true,
        "label": "DOC-ATT-001, p.1",
        "text": "Students must maintain at least 75% attendance in all courses to be eligible for end semester examinations.",
        "citation": {
          "document_id": "DOC-ATT-001",
          "version_no": 1,
          "page_start": 1,
          "page_end": 1,
          "title": "Attendance Policy",
          "source_url": null,
          "source_type": "official"
        },
        "entity_ids": []
      }
    ],
    "grounding": {
      "passed": true,
      "issues": [],
      "warnings": []
    },
    "provider": "extractive",
    "model": "extractive-v1",
    "timings_ms": {
      "routing": 2,
      "retrieval": 18,
      "context": 1,
      "generation": 0,
      "grounding": 1,
      "total": 22
    }
  }
  ```

---

## 5. Error Responses Schema

All errors follow a unified JSON error format across all status codes:

```json
{
  "error": {
    "code": "validation_error",
    "message": "The request is invalid.",
    "details": [
      {
        "location": "body.question",
        "message": "String should have at least 2 characters"
      }
    ]
  }
}
```

### Common HTTP Status Codes
- `400 Bad Request`: Malformed payload or unparseable JSON (`code: "bad_request"`).
- `401 Unauthorized`: Not logged in, missing session cookie / bearer token (`code: "unauthorized"`).
- `403 Forbidden`: Role lacks required permission (`code: "forbidden"`).
- `404 Not Found`: Resource does not exist (`code: "not_found"`).
- `413 Body Too Large`: Request body exceeds size limit (`code: "body_too_large"`).
- `422 Unprocessable Content`: Validation error in fields (`code: "validation_error"`).
- `429 Too Many Requests`: Rate limit exceeded (`code: "rate_limited"`).
- `500 Internal Server Error`: Server-side unhandled exception (`code: "internal_error"`).

---

## 6. Document & Admin Endpoints

The following administrative endpoints are implemented for content management:

| Endpoint | Method | Role Permission | Description |
| :--- | :--- | :--- | :--- |
| `/api/v1/documents` | `GET` | `documents:read` | List all documents with pagination & status filters |
| `/api/v1/documents` | `POST` | `documents:manage` | Upload new PDF document (`multipart/form-data`) |
| `/api/v1/documents/stats` | `GET` | `documents:read` | Dashboard statistics (active docs, pending jobs, etc.) |
| `/api/v1/documents/{id}` | `GET` | `documents:read` | Document details & version history |
| `/api/v1/documents/{id}/versions` | `POST` | `documents:manage` | Upload new version (N+1) of a document |
| `/api/v1/documents/{id}/versions/{v}/activate` | `POST` | `documents:manage` | Activate specific document version |
| `/api/v1/documents/{id}/reindex` | `POST` | `documents:manage` | Re-queue active version for ingestion/embedding |
| `/api/v1/documents/{id}/deactivate` | `POST` | `documents:manage` | Deactivate document (stops answering from it) |
| `/api/v1/documents/{id}` | `DELETE` | `documents:manage` | Soft delete document |
| `/api/v1/ingestion/jobs` | `GET` | `ingestion:manage` | List background ingestion worker jobs |
| `/api/v1/ingestion/jobs/{id}` | `GET` | `ingestion:manage` | Get detailed job ingestion progress & errors |
| `/api/v1/ingestion/jobs/{id}/retry` | `POST` | `ingestion:manage` | Retry a failed ingestion job |
| `/api/v1/knowledge/entities/{id}` | `GET` | `catalog:read` | Inspect OKF knowledge graph entity details |
| `/api/v1/knowledge/entities/{id}/okf` | `GET` | `catalog:read` | Export entity as OKF YAML + Markdown |
| `/api/v1/audit-logs` | `GET` | `audit:read` | Audit log trail (security, login & document actions) |
| `/api/v1/chat/analytics` | `GET` | `audit:read` | Chat system analytics (routes, unanswered queries) |

---

## 7. CORS Configuration Requirement

Currently, CORS middleware is not enabled in `app/main.py`. Before connecting the React frontend (running on `http://localhost:5173`), FastAPI must include `CORSMiddleware` configured with:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
