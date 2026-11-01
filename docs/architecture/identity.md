# CentFlow Multi-User Identity & Security Architecture

## 1. Overview & Security Objectives

CentFlow enforces multi-tenant user data isolation across portfolio tracking, watchlist management, and personalized analytical features.

The identity and security architecture provides:
1. **User Authentication:** Email/password credentials hashed with Argon2id and Google OAuth 2.0 / OpenID Connect.
2. **Session Security:** Opaque, high-entropy 32-byte session tokens stored exclusively as SHA-256 hashes in persistence.
3. **Transport & Cookie Defense:** `HttpOnly`, `SameSite=Lax`, and `Secure` (in production) cookies combined with double-submit CSRF token protection.
4. **Strict Multi-Tenant Isolation:** All financial portfolios, positions, and watchlists are strictly scoped to the authenticated `user_id`.
5. **Anti-Enumeration Defense:** Unauthorized cross-user resource accesses return `404 Not Found` instead of `403 Forbidden` to prevent probing entity identifiers.
6. **Account Linking Defense:** Google identities matching existing password-based accounts cannot be linked silently without an active authenticated session, preventing pre-hijacking and takeover attacks.

---

## 2. Technology & Primitives

| Component | Specification / Standard |
| :--- | :--- |
| **Password Hashing** | Argon2id (`time_cost=3`, `memory_cost=65536`, `parallelism=4`) via `argon2-cffi` |
| **Session Generation** | 32-byte cryptographically secure pseudorandom tokens (`secrets.token_bytes(32)`) |
| **Token Storage** | SHA-256 cryptographic digests in SQLite / SQLAlchemy |
| **CSRF Protection** | Double-submit cookie pattern (`centflow_csrf`) verified against `X-CSRF-Token` header for state-mutating requests (`POST`, `PUT`, `DELETE`, `PATCH`) |
| **OAuth 2.0 PKCE** | RFC 7636 Proof Key for Code Exchange with `S256` code challenge and server-side state verification |
| **Email Validation** | RFC 5322 compliance and canonical lowercase normalization |

---

## 3. Data Entities & Relational Schema

```text
┌─────────────────┐       ┌──────────────────────┐
│   UserSession   │       │     UserIdentity     │
│─────────────────│       │──────────────────────│
│ id (UUID)       │       │ id (UUID)            │
│ user_id (FK)────┼──┐    │ user_id (FK)─────────┼──┐
│ token_hash      │  │    │ provider             │  │
│ expires_at      │  │    │ provider_subject     │  │
│ revoked_at      │  │    │ provider_email       │  │
└─────────────────┘  │    └──────────────────────┘  │
                     ▼                              ▼
             ┌──────────────────────────────────────────────┐
             │                    User                      │
             │──────────────────────────────────────────────│
             │ id (UUID, PK)                                │
             │ email (Unique, Indexed)                      │
             │ email_normalized (Unique, Indexed)           │
             │ display_name                                 │
             │ password_hash (Nullable)                     │
             │ is_active (Boolean)                          │
             │ email_verified_at (Nullable)                 │
             │ created_at / updated_at / last_login_at      │
             └───────┬──────────────────────────────┬───────┘
                     │                              │
                     ▼                              ▼
             ┌───────────────┐              ┌───────────────┐
             │   Portfolio   │              │   Watchlist   │
             │───────────────│              │───────────────│
             │ id            │              │ id            │
             │ user_id (FK)  │              │ user_id (FK)  │
             │ name          │              │ name          │
             └───────────────┘              └───────────────┘
```

### Relational Constraints
- `portfolios.user_id` and `watchlists.user_id` are `NOT NULL` foreign keys referencing `users.id` with `ON DELETE CASCADE`.
- Existing unauthenticated development data is migrated to a deterministic legacy development account (`legacy-dev-user-0000-000000000001`) during database migration.

---

## 4. Authentication Workflows

### A. Email & Password Registration & Login
1. Client submits registration payload (`email`, `password`, `display_name`).
2. Server validates password complexity (minimum 8 characters) and normalizes email.
3. Server generates Argon2id password hash and stores new `User` record.
4. Server generates 32-byte opaque session token, hashes it with SHA-256, and stores it in `user_sessions`.
5. Server sets `centflow_session` (`HttpOnly`, `SameSite=Lax`, `Path=/`) and `centflow_csrf` cookies.

### B. Google OAuth 2.0 PKCE Flow
1. Client requests Google authorization URL from `/api/v1/auth/google/url`.
2. Server generates random `state`, cryptographically random `code_verifier`, and `code_challenge = BASE64URL(SHA256(code_verifier))`.
3. Client stores `state` and `code_verifier` in `sessionStorage` and navigates to Google consent screen.
4. Google redirects to `/auth/google/callback?code=...&state=...`.
5. Client verifies `state` and exchanges `code` and `code_verifier` with `/api/v1/auth/google/callback`.
6. Server exchanges code with Google, verifies `id_token` and `email_verified: true`, and safely logs in or provisions user.

---

## 5. Multi-Tenant Enforcement & Security Dependencies

In FastAPI route handlers, user identity and CSRF validation are injected via dependencies:

```python
from app.api.deps import get_current_user, enforce_csrf

@router.post("", dependencies=[Depends(enforce_csrf)])
def create_portfolio(
    portfolio_in: PortfolioCreateSchema,
    current_user: UserModel = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    return service.create_portfolio(user_id=current_user.id, data=portfolio_in)
```

1. **`get_current_user`:** Validates session cookie existence, verifies expiration and revocation against SQLite session store, updates `last_used_at`, and returns active `UserModel`. If invalid or expired, raises `401 Unauthorized`.
2. **`enforce_csrf`:** Enforces CSRF token match for mutating methods (`POST`, `PUT`, `DELETE`, `PATCH`). Compares `centflow_csrf` cookie against `X-CSRF-Token` header using constant-time comparison (`secrets.compare_digest`). If invalid, raises `403 Forbidden`.

---

## 6. Frontend Security Layer

The React application coordinates with the backend via:
- **`src/api/client.js`:** Custom HTTP wrapper with `credentials: 'include'` and automated extraction of `centflow_csrf` cookie into `X-CSRF-Token` header.
- **`src/auth/AuthContext.jsx`:** React context maintaining `user`, `isAuthenticated`, `isLoading`, and providing `login`, `register`, `logout`, and session restoration.
- **`src/auth/ProtectedRoute.jsx`:** Route protection component preventing unauthenticated rendering of financial views.
- **`src/components/layout/Header.jsx`:** User identity indicator displaying avatar and secure one-click session termination.

