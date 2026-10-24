# CentFlow API Conventions

## 1. Overview & Principles

This document defines the architectural and design standards for CentFlow APIs.

The objective is to ensure that all endpoints across the platform are predictable, consistent, versioned, and easy for clients (both frontend applications and external consumers) to integrate with.

### Core Principles

1. **Predictability:** Every response follows a standardized envelope structure (`data`, `pagination`, or `error`).
2. **RESTful Semantics:** Standard HTTP verbs (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`) and status codes (`200`, `201`, `204`, `400`, `404`, `422`, `500`) are used consistently.
3. **Explicit Error Envelopes:** Error payloads always provide a machine-readable `code`, a human-readable `message`, and optional granular `details`.
4. **Deterministic Versioning:** All domain endpoints reside under a versioned path prefix (e.g., `/api/v1/`).
5. **Separation of Concerns:** Route handlers validate inputs and serialize responses; they delegate all computational and business logic to the service layer.

---

## 2. URL Design & Resource Naming

### 2.1 Route Structure

All API routes follow this structure:

```text
/api/v{version}/{resource}[/{id}][/{sub-resource}]
```

Examples:

```text
GET    /api/v1/instruments
GET    /api/v1/instruments/{id}
POST   /api/v1/watchlists
GET    /api/v1/watchlists/{id}/instruments
POST   /api/v1/portfolios/{id}/positions
GET    /api/v1/prices/latest?symbol=AAPL
```

### 2.2 Naming Conventions

- **Plural Nouns:** Resources use plural lower-case nouns (`instruments`, `assets`, `watchlists`, `portfolios`).
- **Kebab-Case Paths:** Multi-word resources use kebab-case in URLs: `/api/v1/market-data`, `/api/v1/watchlist-items`.
- **Hierarchical Nesting:** Sub-resources that belong to a parent container are nested under the parent ID: `/api/v1/portfolios/{id}/positions`. Deep nesting beyond two levels is avoided.
- **Top-Level Health Checks:** Infrastructure and liveness checks are exposed at `/health` (and `/api/v1/health` for versioned routing).

---

## 3. HTTP Methods & Status Codes

| Method | Idempotent | Standard Status | Description |
| :--- | :--- | :--- | :--- |
| `GET` | Yes | `200 OK` | Retrieve resource representation(s) |
| `POST` | No | `201 Created` | Create a new resource |
| `PUT` | Yes | `200 OK` | Completely replace an existing resource |
| `PATCH` | No | `200 OK` | Partially update an existing resource |
| `DELETE` | Yes | `204 No Content` / `200 OK` | Remove a resource |

### Common HTTP Error Statuses

- **`400 Bad Request`**: Malformed request syntax or invalid business parameters.
- **`401 Unauthorized`**: Missing or invalid authentication credentials (when introduced).
- **`403 Forbidden`**: Authenticated caller lacks permission for the resource.
- **`404 Not Found`**: Target resource identifier does not exist.
- **`409 Conflict`**: Request conflicts with current resource state (e.g., duplicate symbol or unique key violation).
- **`422 Unprocessable Entity`**: Request body or query parameters failed Pydantic schema validation.
- **`500 Internal Server Error`**: Unexpected server-side failure.

---

## 4. Response Envelopes

### 4.1 Single Resource Response

Successful requests returning a single object are wrapped in a `ResponseEnvelope`:

```json
{
  "data": {
    "id": "7f80b21e-1234-4567-89ab-cdef01234567",
    "symbol": "AAPL",
    "name": "Apple Inc. Common Stock",
    "currency": "USD",
    "is_active": true
  },
  "meta": {
    "cached": false
  }
}
```

The `meta` field is optional and used for operational metadata (e.g., execution time, provider attribution).

---

### 4.2 Paginated Collection Response

List endpoints return a `PaginatedResponse` containing the item array and a `pagination` metadata object:

```json
{
  "data": [
    {
      "id": "7f80b21e-1234-4567-89ab-cdef01234567",
      "symbol": "AAPL",
      "name": "Apple Inc. Common Stock"
    },
    {
      "id": "8a91c32f-5678-4321-98ba-fedcba987654",
      "symbol": "MSFT",
      "name": "Microsoft Corporation"
    }
  ],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "total": 142,
    "has_next": true
  }
}
```

---

## 5. Error Envelopes

All errors returned by CentFlow APIs conform to the standard `ErrorResponse` schema:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Instrument 'AAPL' not found.",
    "details": [
      {
        "field": "symbol",
        "message": "Instrument with symbol 'AAPL' was not found."
      }
    ]
  }
}
```

### Validation Error Example (`422 Unprocessable Entity`)

```json
{
  "error": {
    "code": "REQUEST_VALIDATION_ERROR",
    "message": "Request body or query parameters failed validation.",
    "details": [
      {
        "field": "quantity",
        "message": "Input should be greater than 0",
        "type": "greater_than"
      }
    ]
  }
}
```

### Error Code Conventions

- Standard error codes are uppercase snake_case (`NOT_FOUND`, `VALIDATION_ERROR`, `CONFLICT_ERROR`, `INTERNAL_SERVER_ERROR`).
- Custom domain exceptions subclass `CentFlowException` in [`backend/app/core/errors.py`](../backend/app/core/errors.py).

---

## 6. Query Parameters: Pagination, Filtering & Sorting

### 6.1 Pagination Parameters

- `limit` (integer, default: `20`, min: `1`, max: `100`): Maximum items to return.
- `offset` (integer, default: `0`, min: `0`): Number of items to skip.

### 6.2 Sorting Parameters

- `sort_by` (string): Field to sort by (e.g., `symbol`, `created_at`, `price`).
- `order` (string, default: `asc`): Sort direction (`asc` or `desc`).

---

## 7. Field Naming & Serialization Conventions

1. **JSON Keys:** All JSON fields use `snake_case` (e.g., `asset_id`, `created_at`, `average_price`), matching the backend domain models and persistence data model.
2. **Timestamps:** Formatted as ISO 8601 strings in UTC: `2026-10-24T13:45:00Z`.
3. **Monetary & Decimal Figures:**
   - Values that require precision (prices, quantities) are serialized as fixed-point decimals or numeric strings to eliminate floating-point rounding errors on the client.
4. **Currencies:** ISO 4217 uppercase 3-character strings (`USD`, `EUR`, `INR`).

---

## 8. Frontend Integration Contract

By establishing these conventions in Phase 2:
- The React frontend API client (Phase 2, Issue #20) can implement a unified response interceptor:
  - Automatically unwraps `response.data`.
  - Captures `response.pagination` for tables and lists.
  - Automatically routes `response.error` to toast notifications or form validation errors.
- No frontend component needs to guess whether an endpoint returns `{ "result": ... }`, `{ "items": ... }`, or raw lists.
