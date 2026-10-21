# API Document and Flow Diagram

> [!NOTE]
> **Retries and concurrency.** Any `POST`/`PATCH` may carry an `Idempotency-Key` header (unique per logical operation, e.g. a UUID): a retry with the same key replays the first response with `Idempotent-Replayed: true` instead of executing twice (422 `idempotency_key_reused` if the body differs, 409 `idempotency_request_in_progress` while the first call runs). Single-resource reads return an `ETag`; send it back in `If-Match` on updates to get 412 `precondition_failed` instead of overwriting a concurrent change. Concurrent writes that still collide return 409 `concurrent_modification`.

> [!NOTE]
> **Error format.** Every error response is an [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) Problem Details object served as `application/problem+json`: `type` (`PROBLEM_TYPE_BASE_URI/<code>`), `title`, `status`, `detail`, `instance` (request path), a stable machine-readable `code` that clients should branch on, the `request_id` (also sent as the `X-Request-ID` header) and, for 422 responses, an `errors` list with one entry per invalid field. Failed requests (any 4xx/5xx) never persist partial writes.

> [!IMPORTANT]
> If any API updates modify the underlying database schemas, fields, or relationships, make sure to update the [DATABASE_DESIGN.md](/docs/DATABASE_DESIGN.md) file, which contains the Mermaid entity-relationship diagram and detailed column descriptions.

## API Index

- **Auth Endpoints**

  - [User Signup (POST `/v1/auth/signup`)](#user-signup)
  - [User Signin (POST `/v1/auth/signin`)](#user-signin)
  - [User Signout (POST `/v1/auth/signout`)](#user-signout)
  - [Complete MFA Signin (POST `/v1/auth/mfa/verify`)](#complete-mfa-signin)
  - [Refresh Session (POST `/v1/auth/refresh`)](#refresh-session)
  - [Sign Out Everywhere (POST `/v1/auth/signout-all`)](#sign-out-everywhere)
  - [Verify Email (POST `/v1/auth/verify-email`)](#verify-email)
  - [Resend Verification Email (POST `/v1/auth/verify-email/resend`)](#resend-verification-email)
  - [Request Password Reset (POST `/v1/auth/password/forgot`)](#request-password-reset)
  - [Reset Password (POST `/v1/auth/password/reset`)](#reset-password)
  - [Change Password (POST `/v1/auth/password/change`)](#change-password)
  - [Start MFA Setup (POST `/v1/auth/mfa/setup`)](#start-mfa-setup)
  - [Enable MFA (POST `/v1/auth/mfa/enable`)](#enable-mfa)
  - [Disable MFA (POST `/v1/auth/mfa/disable`)](#disable-mfa)

- **Users Endpoints**

  - [Get Current User (GET `/v2/user/me`)](#get-current-user)
  - [Delete Current User (DELETE `/v2/user/me`)](#delete-current-user)
  - [List Users (admin) (GET `/v2/users/`)](#list-users-admin)

- **Todos Endpoints**

  - [List Todos (GET `/v2/todos/`)](#list-todos)
  - [Create Todo (POST `/v2/todos/`)](#create-todo)
  - [Toggle Todo Archive Status (POST `/v2/todos/{_todo_id}:archive`)](#toggle-todo-archive-status)
  - [Get Todo (GET `/v2/todos/{todo_id}`)](#get-todo)
  - [Update Todo (PATCH `/v2/todos/{_todo_id}`)](#update-todo)
  - [Delete Todo (DELETE `/v2/todos/{_todo_id}`)](#delete-todo)

- **Audit Endpoints**

  - [List Audit Logs (admin) (GET `/v2/audit-logs/`)](#list-audit-logs)

- **Health Endpoints**

  - [Liveness Probe (GET `/health/live`)](#liveness-probe)
  - [Readiness Probe (GET `/health/ready`)](#readiness-probe)

- **Data Acquisition Endpoints** (`data-acquisition`, a separate service)

  - [Service contract and authentication](#data-acquisition-service)
  - [Create Acquisition Job (POST `/v1/acquisition-jobs/`)](#create-acquisition-job)
  - [Job lifecycle endpoints (`:start`, `:progress`, `:complete`, `:fail`, `:retry`, `:cancel`)](#acquisition-job-lifecycle)

---

## Auth Endpoints

### <a id="user-signup"></a>User Signup

<details>
<summary>User Signup (POST /v1/auth/signup)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v1/auth/signup` | POST | False | Registers a new user account if the email is not already taken. Generates a random username automatically. |

> <details>
> <summary>Request body</summary>
>
> **Fields:**
>
> - `email` (string, **Required**): Unique email address for the new account.
> - `password` (string, **Required**): Password for the new account: at least 8 characters and at most 72 bytes (bcrypt limit).
>
> ```json
> {
>   "email": "user@example.com",
>   "password": "securepassword123"
> }
> ```
> </details>
>
> <details>
> <summary>Response body</summary>
>
> ```json
> null
> ```
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **422 Unprocessable Entity** (If input email is invalid or missing required fields):
> ```json
> {
>   "type": "https://errors.example.com/validation_failed",
>   "title": "Validation Failed",
>   "status": 422,
>   "detail": "Input validation failed.",
>   "instance": "<request path>",
>   "code": "validation_failed",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a",
>   "errors": [
>     {
>       "field": "email",
>       "message": "Value is not a valid email address",
>       "type": "value_error.email"
>     }
>   ]
> }
> ```
>
> **429 Too Many Requests** (If exceeding rate limit of 5 signups/minute per client IP):
> ```json
> {
>   "type": "https://errors.example.com/rate_limited",
>   "title": "Too Many Requests",
>   "status": 429,
>   "detail": "Too many requests. Please try again later.",
>   "instance": "<request path>",
>   "code": "rate_limited",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Auth Router]
>     Service[AuthService.sign_up]
>     Repo[UserRepository.get_list]
>     DB[(PostgreSQL)]
>     Repo2[UserRepository.add]
>
>     Client -->|1. POST /v1/auth/signup| Router
>     Router -->|2. Validate SignUp Schema| Service
>     Service -->|3. Check existing user| Repo
>     Repo -->|4. SELECT| DB
>     DB -->|5. Return search results| Repo
>     Repo -->|6. Result list| Service
>     Service -->|7. Hash password & generate username| Repo2
>     Repo2 -->|8. INSERT| DB
>     DB -->|9. Success| Repo2
>     Repo2 -->|10. Success| Service
>     Service -->|11. 201 Created| Router
>     Router -->|12. 201 Created| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef repo fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Service service
>     class Repo,Repo2 repo
>     class DB db
> ```
>
> </div>
> </details>

</details>

---

### <a id="user-signin"></a>User Signin

<details>
<summary>User Signin (POST /v1/auth/signin)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v1/auth/signin` | POST | False | Verifies credentials and starts a session (or returns an MFA challenge). Failed attempts are counted per account; after `LOGIN_MAX_FAILED_ATTEMPTS` the account is locked for `LOGIN_LOCKOUT_MINUTES` (401 `account_locked`). |

> <details>
> <summary>Request body</summary>
>
> **Fields:**
>
> - `email` (string, **Required**): User's registered email address.
> - `password` (string, **Required**): User's password.
>
> ```json
> {
>   "email": "user@example.com",
>   "password": "securepassword123"
> }
> ```
> </details>
>
> <details>
> <summary>Response body</summary>
>
> **200 OK.** Without MFA a session is started: `Set-Cookie` for the access token (`HttpOnly`, path `/`, `ACCESS_TOKEN_EXPIRE_MINUTES`), the refresh token (`HttpOnly`, path `/v1/auth`, `REFRESH_TOKEN_EXPIRE_DAYS`) and `csrf_token` (readable; echo it in the `X-CSRF-Token` header on unsafe requests).
>
> ```json
> {
>   "mfaRequired": false,
>   "mfaToken": null
> }
> ```
>
> With MFA enabled no cookies are set; complete sign-in with [Complete MFA Signin](#complete-mfa-signin):
>
> ```json
> {
>   "mfaRequired": true,
>   "mfaToken": "eyJhbGciOi..."
> }
> ```
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **401 Unauthorized** (If password verification or email match fails):
> ```json
> {
>   "type": "https://errors.example.com/unauthenticated",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Incorrect email or password",
>   "instance": "<request path>",
>   "code": "unauthenticated",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **422 Unprocessable Entity** (If validation format errors exist):
> ```json
> {
>   "type": "https://errors.example.com/validation_failed",
>   "title": "Validation Failed",
>   "status": 422,
>   "detail": "Input validation failed.",
>   "instance": "<request path>",
>   "code": "validation_failed",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a",
>   "errors": [
>     {
>       "field": "password",
>       "message": "Field required",
>       "type": "missing"
>     }
>   ]
> }
> ```
>
> **429 Too Many Requests** (If exceeding rate limit of 10 sign-ins/minute per client IP):
> ```json
> {
>   "type": "https://errors.example.com/rate_limited",
>   "title": "Too Many Requests",
>   "status": 429,
>   "detail": "Too many requests. Please try again later.",
>   "instance": "<request path>",
>   "code": "rate_limited",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Auth Router]
>     Service[AuthService.sign_in]
>     Repo[UserRepository.get_list]
>     DB[(PostgreSQL)]
>
>     Client -->|1. POST /v1/auth/signin| Router
>     Router -->|2. Validate SignIn Schema| Service
>     Service -->|3. Fetch user by email| Repo
>     Repo -->|4. SELECT| DB
>     DB -->|5. Return user record| Repo
>     Repo -->|6. User record| Service
>     Service -->|7. Verify password hash & generate JWT| Router
>     Router -->|8. Set HttpOnly cookie & return 200 OK| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef repo fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Service service
>     class Repo repo
>     class DB db
> ```
>
> </div>
> </details>

</details>

---

### <a id="user-signout"></a>User Signout

<details>
<summary>User Signout (POST /v1/auth/signout)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v1/auth/signout` | POST | False | Revokes the current session (its refresh-token family) and expires all session cookies. Idempotent: returns 204 even when no session exists. Requires `X-CSRF-Token` when session cookies are present. |

> <details>
> <summary>Request body</summary>
>
> No request body. The session cookie (if any) is sent automatically by the browser.
> </details>
>
> <details>
> <summary>Response body</summary>
>
> **204 No Content**, with a `Set-Cookie` header that expires the auth cookie (`Max-Age=0; HttpOnly; SameSite=lax`, plus `Secure` outside development).
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **429 Too Many Requests** (If exceeding rate limit of 30 requests/minute):
> ```json
> {
>   "type": "https://errors.example.com/rate_limited",
>   "title": "Too Many Requests",
>   "status": 429,
>   "detail": "Too many requests. Please try again later.",
>   "instance": "<request path>",
>   "code": "rate_limited",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Auth Router]
>     Security[clear_auth_cookie]
>
>     Client -->|1. POST /v1/auth/signout| Router
>     Router -->|2. Expire auth cookie| Security
>     Security -->|3. Set-Cookie Max-Age=0| Router
>     Router -->|4. Return 204 No Content| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Security service
> ```
>
> </div>
> </details>

</details>

---

### <a id="complete-mfa-signin"></a>Complete MFA Signin

<details>
<summary>Complete MFA Signin (POST /v1/auth/mfa/verify)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v1/auth/mfa/verify` | POST | False | Exchanges the MFA challenge token from sign-in plus a 6-digit TOTP code for a session. |

> <details>
> <summary>Request body</summary>
>
> **Fields:**
>
> - `mfaToken` (string, **Required**, alias `mfa_token`): Challenge token returned by sign-in (valid 5 minutes).
> - `code` (string, **Required**): 6-digit code from the authenticator app.
>
> ```json
> {
>   "mfaToken": "eyJhbGciOi...",
>   "code": "492039"
> }
> ```
> </details>
>
> <details>
> <summary>Response body</summary>
>
> **204 No Content** with `Set-Cookie` for the access (`HttpOnly`, path `/`), refresh (`HttpOnly`, path `/v1/auth`) and `csrf_token` (readable) cookies.
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **401 Unauthorized** (Wrong code; counts towards account lockout):
> ```json
> {
>   "type": "https://errors.example.com/invalid_mfa_code",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Invalid authentication code",
>   "instance": "<request path>",
>   "code": "invalid_mfa_code",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **401 Unauthorized** (Challenge token expired):
> ```json
> {
>   "type": "https://errors.example.com/token_expired",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Token expired",
>   "instance": "<request path>",
>   "code": "token_expired",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **422 Unprocessable Entity** (Request body fails validation):
> ```json
> {
>   "type": "https://errors.example.com/validation_failed",
>   "title": "Validation Failed",
>   "status": 422,
>   "detail": "Input validation failed.",
>   "instance": "<request path>",
>   "code": "validation_failed",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a",
>   "errors": [
>     {
>       "field": "code",
>       "message": "String should match pattern '^\\d{6}$'",
>       "type": "string_pattern_mismatch"
>     }
>   ]
> }
> ```
>
> **429 Too Many Requests** (More than 10/minute per client IP):
> ```json
> {
>   "type": "https://errors.example.com/rate_limited",
>   "title": "Too Many Requests",
>   "status": 429,
>   "detail": "Too many requests. Please try again later.",
>   "instance": "<request path>",
>   "code": "rate_limited",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Auth Router]
>     Service[AuthService]
>     Repo[Repositories]
>     DB[(PostgreSQL)]
>
>     Client -->|1. POST /v1/auth/mfa/verify| Router
>     Router -->|2. verify_mfa| Service
>     Service -->|3. Load user, verify TOTP| Repo
>     Repo -->|4. SELECT user / INSERT refresh_token| DB
>     Service -->|5. Session tokens| Router
>     Router -->|6. Set cookies, 204| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef repo fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Service service
>     class Repo repo
>     class DB db
> ```
>
> </div>
> </details>

</details>

---
### <a id="refresh-session"></a>Refresh Session

<details>
<summary>Refresh Session (POST /v1/auth/refresh)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v1/auth/refresh` | POST | Refresh cookie | Rotates the refresh token and issues a new short-lived access token. Replaying an already-rotated refresh token revokes the whole session family. |

> <details>
> <summary>Request body</summary>
>
> **Fields:**
>
> - Header `X-CSRF-Token` (**Required**): value of the `csrf_token` cookie.
>
> No request body.
> </details>
>
> <details>
> <summary>Response body</summary>
>
> **204 No Content** with `Set-Cookie` for the access (`HttpOnly`, path `/`), refresh (`HttpOnly`, path `/v1/auth`) and `csrf_token` (readable) cookies.
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **401 Unauthorized** (Refresh token missing, unknown or expired):
> ```json
> {
>   "type": "https://errors.example.com/invalid_token",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Invalid refresh token",
>   "instance": "<request path>",
>   "code": "invalid_token",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **401 Unauthorized** (Rotated token replayed: possible theft, all sessions of this sign-in are revoked):
> ```json
> {
>   "type": "https://errors.example.com/refresh_token_reused",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Session has been revoked",
>   "instance": "<request path>",
>   "code": "refresh_token_reused",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **403 Forbidden** (Session cookie present but `X-CSRF-Token` header missing or wrong):
> ```json
> {
>   "type": "https://errors.example.com/csrf_failed",
>   "title": "Forbidden",
>   "status": 403,
>   "detail": "Missing or invalid X-CSRF-Token header",
>   "instance": "<request path>",
>   "code": "csrf_failed",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **429 Too Many Requests** (More than 30/minute per client IP):
> ```json
> {
>   "type": "https://errors.example.com/rate_limited",
>   "title": "Too Many Requests",
>   "status": 429,
>   "detail": "Too many requests. Please try again later.",
>   "instance": "<request path>",
>   "code": "rate_limited",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Auth Router]
>     Service[AuthService]
>     Repo[Repositories]
>     DB[(PostgreSQL)]
>
>     Client -->|1. POST /v1/auth/refresh| Router
>     Router -->|2. refresh(cookie)| Service
>     Service -->|3. Find token by SHA-256 hash| Repo
>     Repo -->|4. SELECT / UPDATE revoked_at / INSERT new| DB
>     Service -->|5. New session tokens| Router
>     Router -->|6. Set cookies, 204| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef repo fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Service service
>     class Repo repo
>     class DB db
> ```
>
> </div>
> </details>

</details>

---
### <a id="sign-out-everywhere"></a>Sign Out Everywhere

<details>
<summary>Sign Out Everywhere (POST /v1/auth/signout-all)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v1/auth/signout-all` | POST | True | Revokes every session of the current user: all refresh tokens and, via `token_version`, every issued access token. |

> <details>
> <summary>Request body</summary>
>
> **Fields:**
>
> - Header `X-CSRF-Token` (**Required**).
>
> No request body.
> </details>
>
> <details>
> <summary>Response body</summary>
>
> **204 No Content**. Session cookies are (re)set via `Set-Cookie` where noted. All session cookies are expired.
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **401 Unauthorized** (No valid session, or the session was revoked):
> ```json
> {
>   "type": "https://errors.example.com/not_authenticated",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Not authenticated",
>   "instance": "<request path>",
>   "code": "not_authenticated",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **403 Forbidden** (Session cookie present but `X-CSRF-Token` header missing or wrong):
> ```json
> {
>   "type": "https://errors.example.com/csrf_failed",
>   "title": "Forbidden",
>   "status": 403,
>   "detail": "Missing or invalid X-CSRF-Token header",
>   "instance": "<request path>",
>   "code": "csrf_failed",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **429 Too Many Requests** (More than 10/minute per client IP):
> ```json
> {
>   "type": "https://errors.example.com/rate_limited",
>   "title": "Too Many Requests",
>   "status": 429,
>   "detail": "Too many requests. Please try again later.",
>   "instance": "<request path>",
>   "code": "rate_limited",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Auth Router]
>     Service[AuthService]
>     Repo[Repositories]
>     DB[(PostgreSQL)]
>
>     Client -->|1. POST /v1/auth/signout-all| Router
>     Router -->|2. sign_out_everywhere| Service
>     Service -->|3. Revoke tokens, bump token_version| Repo
>     Repo -->|4. UPDATE refresh_tokens, users| DB
>     Router -->|5. Clear cookies, 204| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef repo fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Service service
>     class Repo repo
>     class DB db
> ```
>
> </div>
> </details>

</details>

---
### <a id="verify-email"></a>Verify Email

<details>
<summary>Verify Email (POST /v1/auth/verify-email)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v1/auth/verify-email` | POST | False | Confirms the email address with the single-use token from the verification email (valid `EMAIL_VERIFICATION_EXPIRE_HOURS`). |

> <details>
> <summary>Request body</summary>
>
> **Fields:**
>
> - `token` (string, **Required**): token from the email link.
>
> ```json
> {
>   "token": "Xq3...single-use-token"
> }
> ```
> </details>
>
> <details>
> <summary>Response body</summary>
>
> **204 No Content**. Session cookies are (re)set via `Set-Cookie` where noted.
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **400 Bad Request** (Token unknown, already used or expired):
> ```json
> {
>   "type": "https://errors.example.com/invalid_or_expired_token",
>   "title": "Bad Request",
>   "status": 400,
>   "detail": "This link is invalid or has expired",
>   "instance": "<request path>",
>   "code": "invalid_or_expired_token",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **429 Too Many Requests** (More than 10/minute per client IP):
> ```json
> {
>   "type": "https://errors.example.com/rate_limited",
>   "title": "Too Many Requests",
>   "status": 429,
>   "detail": "Too many requests. Please try again later.",
>   "instance": "<request path>",
>   "code": "rate_limited",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Auth Router]
>     Service[AuthService]
>     Repo[Repositories]
>     DB[(PostgreSQL)]
>
>     Client -->|1. POST /v1/auth/verify-email| Router
>     Router -->|2. verify_email| Service
>     Service -->|3. Consume one-time token| Repo
>     Repo -->|4. UPDATE used_at, users.email_verified_at| DB
>     Router -->|5. 204| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef repo fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Service service
>     class Repo repo
>     class DB db
> ```
>
> </div>
> </details>

</details>

---
### <a id="resend-verification-email"></a>Resend Verification Email

<details>
<summary>Resend Verification Email (POST /v1/auth/verify-email/resend)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v1/auth/verify-email/resend` | POST | True | Sends a new verification link; previous links stop working. No-op if already verified. |

> <details>
> <summary>Request body</summary>
>
> **Fields:**
>
> - Header `X-CSRF-Token` (**Required**).
>
> No request body.
> </details>
>
> <details>
> <summary>Response body</summary>
>
> **202 Accepted**. The email is sent after the transaction commits.
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **401 Unauthorized** (No valid session, or the session was revoked):
> ```json
> {
>   "type": "https://errors.example.com/not_authenticated",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Not authenticated",
>   "instance": "<request path>",
>   "code": "not_authenticated",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **403 Forbidden** (Session cookie present but `X-CSRF-Token` header missing or wrong):
> ```json
> {
>   "type": "https://errors.example.com/csrf_failed",
>   "title": "Forbidden",
>   "status": 403,
>   "detail": "Missing or invalid X-CSRF-Token header",
>   "instance": "<request path>",
>   "code": "csrf_failed",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **429 Too Many Requests** (More than 3/minute per client IP):
> ```json
> {
>   "type": "https://errors.example.com/rate_limited",
>   "title": "Too Many Requests",
>   "status": 429,
>   "detail": "Too many requests. Please try again later.",
>   "instance": "<request path>",
>   "code": "rate_limited",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Auth Router]
>     Service[AuthService]
>     Repo[Repositories]
>     DB[(PostgreSQL)]
>     Mail[[Email provider]]
>
>     Client -->|1. POST /v1/auth/verify-email/resend| Router
>     Router -->|2. resend_verification| Service
>     Service -->|3. Invalidate old, store new token hash| Repo
>     Repo -->|4. UPDATE / INSERT one_time_tokens| DB
>     Service -->|5. After commit: send link| Mail
>     Router -->|6. 202| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef repo fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Service service
>     class Repo repo
>     class DB db
>     class Mail service
> ```
>
> </div>
> </details>

</details>

---
### <a id="request-password-reset"></a>Request Password Reset

<details>
<summary>Request Password Reset (POST /v1/auth/password/forgot)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v1/auth/password/forgot` | POST | False | Emails a single-use reset link (valid `PASSWORD_RESET_EXPIRE_MINUTES`) if the account exists. Always 202 so accounts cannot be enumerated. |

> <details>
> <summary>Request body</summary>
>
> **Fields:**
>
> - `email` (string, **Required**).
>
> ```json
> {
>   "email": "user@example.com"
> }
> ```
> </details>
>
> <details>
> <summary>Response body</summary>
>
> **202 Accepted** (also for unknown emails).
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **422 Unprocessable Entity** (Request body fails validation):
> ```json
> {
>   "type": "https://errors.example.com/validation_failed",
>   "title": "Validation Failed",
>   "status": 422,
>   "detail": "Input validation failed.",
>   "instance": "<request path>",
>   "code": "validation_failed",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a",
>   "errors": [
>     {
>       "field": "code",
>       "message": "String should match pattern '^\\d{6}$'",
>       "type": "string_pattern_mismatch"
>     }
>   ]
> }
> ```
>
> **429 Too Many Requests** (More than 3/minute per client IP):
> ```json
> {
>   "type": "https://errors.example.com/rate_limited",
>   "title": "Too Many Requests",
>   "status": 429,
>   "detail": "Too many requests. Please try again later.",
>   "instance": "<request path>",
>   "code": "rate_limited",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Auth Router]
>     Service[AuthService]
>     Repo[Repositories]
>     DB[(PostgreSQL)]
>     Mail[[Email provider]]
>
>     Client -->|1. POST /v1/auth/password/forgot| Router
>     Router -->|2. forgot_password| Service
>     Service -->|3. Store reset token hash| Repo
>     Repo -->|4. INSERT one_time_tokens| DB
>     Service -->|5. After commit: send link| Mail
>     Router -->|6. 202| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef repo fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Service service
>     class Repo repo
>     class DB db
>     class Mail service
> ```
>
> </div>
> </details>

</details>

---
### <a id="reset-password"></a>Reset Password

<details>
<summary>Reset Password (POST /v1/auth/password/reset)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v1/auth/password/reset` | POST | False | Sets a new password with a reset token, revokes every session (refresh tokens and access tokens) and emails a confirmation. |

> <details>
> <summary>Request body</summary>
>
> **Fields:**
>
> - `token` (string, **Required**): token from the reset email.
> - `newPassword` (string, **Required**, alias `new_password`): 8 characters to 72 bytes.
>
> ```json
> {
>   "token": "Xq3...single-use-token",
>   "newPassword": "a-new-strong-password"
> }
> ```
> </details>
>
> <details>
> <summary>Response body</summary>
>
> **204 No Content**. Session cookies are (re)set via `Set-Cookie` where noted. Session cookies are expired.
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **400 Bad Request** (Token unknown, already used or expired):
> ```json
> {
>   "type": "https://errors.example.com/invalid_or_expired_token",
>   "title": "Bad Request",
>   "status": 400,
>   "detail": "This link is invalid or has expired",
>   "instance": "<request path>",
>   "code": "invalid_or_expired_token",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **422 Unprocessable Entity** (Request body fails validation):
> ```json
> {
>   "type": "https://errors.example.com/validation_failed",
>   "title": "Validation Failed",
>   "status": 422,
>   "detail": "Input validation failed.",
>   "instance": "<request path>",
>   "code": "validation_failed",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a",
>   "errors": [
>     {
>       "field": "code",
>       "message": "String should match pattern '^\\d{6}$'",
>       "type": "string_pattern_mismatch"
>     }
>   ]
> }
> ```
>
> **429 Too Many Requests** (More than 5/minute per client IP):
> ```json
> {
>   "type": "https://errors.example.com/rate_limited",
>   "title": "Too Many Requests",
>   "status": 429,
>   "detail": "Too many requests. Please try again later.",
>   "instance": "<request path>",
>   "code": "rate_limited",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Auth Router]
>     Service[AuthService]
>     Repo[Repositories]
>     DB[(PostgreSQL)]
>     Mail[[Email provider]]
>
>     Client -->|1. POST /v1/auth/password/reset| Router
>     Router -->|2. reset_password| Service
>     Service -->|3. Consume token, set hash, revoke sessions| Repo
>     Repo -->|4. UPDATE users, refresh_tokens| DB
>     Service -->|5. After commit: password changed notice| Mail
>     Router -->|6. 204| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef repo fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Service service
>     class Repo repo
>     class DB db
>     class Mail service
> ```
>
> </div>
> </details>

</details>

---
### <a id="change-password"></a>Change Password

<details>
<summary>Change Password (POST /v1/auth/password/change)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v1/auth/password/change` | POST | True | Changes the password of the signed-in user, signs out all other sessions and starts a fresh session on this device. |

> <details>
> <summary>Request body</summary>
>
> **Fields:**
>
> - `currentPassword` (string, **Required**, alias `current_password`).
> - `newPassword` (string, **Required**, alias `new_password`): 8 characters to 72 bytes.
> - Header `X-CSRF-Token` (**Required**).
>
> ```json
> {
>   "currentPassword": "old-password",
>   "newPassword": "a-new-strong-password"
> }
> ```
> </details>
>
> <details>
> <summary>Response body</summary>
>
> **204 No Content** with `Set-Cookie` for the access (`HttpOnly`, path `/`), refresh (`HttpOnly`, path `/v1/auth`) and `csrf_token` (readable) cookies.
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **401 Unauthorized** (Current password wrong):
> ```json
> {
>   "type": "https://errors.example.com/invalid_credentials",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Current password is incorrect",
>   "instance": "<request path>",
>   "code": "invalid_credentials",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **401 Unauthorized** (No valid session, or the session was revoked):
> ```json
> {
>   "type": "https://errors.example.com/not_authenticated",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Not authenticated",
>   "instance": "<request path>",
>   "code": "not_authenticated",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **403 Forbidden** (Session cookie present but `X-CSRF-Token` header missing or wrong):
> ```json
> {
>   "type": "https://errors.example.com/csrf_failed",
>   "title": "Forbidden",
>   "status": 403,
>   "detail": "Missing or invalid X-CSRF-Token header",
>   "instance": "<request path>",
>   "code": "csrf_failed",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **422 Unprocessable Entity** (Request body fails validation):
> ```json
> {
>   "type": "https://errors.example.com/validation_failed",
>   "title": "Validation Failed",
>   "status": 422,
>   "detail": "Input validation failed.",
>   "instance": "<request path>",
>   "code": "validation_failed",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a",
>   "errors": [
>     {
>       "field": "code",
>       "message": "String should match pattern '^\\d{6}$'",
>       "type": "string_pattern_mismatch"
>     }
>   ]
> }
> ```
>
> **429 Too Many Requests** (More than 5/minute per client IP):
> ```json
> {
>   "type": "https://errors.example.com/rate_limited",
>   "title": "Too Many Requests",
>   "status": 429,
>   "detail": "Too many requests. Please try again later.",
>   "instance": "<request path>",
>   "code": "rate_limited",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Auth Router]
>     Service[AuthService]
>     Repo[Repositories]
>     DB[(PostgreSQL)]
>
>     Client -->|1. POST /v1/auth/password/change| Router
>     Router -->|2. change_password| Service
>     Service -->|3. Verify, set hash, revoke sessions, new session| Repo
>     Repo -->|4. UPDATE users, refresh_tokens / INSERT| DB
>     Router -->|5. Set cookies, 204| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef repo fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Service service
>     class Repo repo
>     class DB db
> ```
>
> </div>
> </details>

</details>

---
### <a id="start-mfa-setup"></a>Start MFA Setup

<details>
<summary>Start MFA Setup (POST /v1/auth/mfa/setup)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v1/auth/mfa/setup` | POST | True | Generates a TOTP secret (stored encrypted, inactive until confirmed) to add to an authenticator app. |

> <details>
> <summary>Request body</summary>
>
> **Fields:**
>
> - Header `X-CSRF-Token` (**Required**).
>
> No request body.
> </details>
>
> <details>
> <summary>Response body</summary>
>
> ```json
> {
>   "secret": "JBSWY3DPEHPK3PXP",
>   "otpauthUri": "otpauth://totp/FastAPI%20Template:user%40example.com?secret=JBSWY3DPEHPK3PXP&issuer=FastAPI%20Template"
> }
> ```
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **400 Bad Request** (MFA already enabled):
> ```json
> {
>   "type": "https://errors.example.com/mfa_already_enabled",
>   "title": "Bad Request",
>   "status": 400,
>   "detail": "MFA is already enabled",
>   "instance": "<request path>",
>   "code": "mfa_already_enabled",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **401 Unauthorized** (No valid session, or the session was revoked):
> ```json
> {
>   "type": "https://errors.example.com/not_authenticated",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Not authenticated",
>   "instance": "<request path>",
>   "code": "not_authenticated",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **403 Forbidden** (Session cookie present but `X-CSRF-Token` header missing or wrong):
> ```json
> {
>   "type": "https://errors.example.com/csrf_failed",
>   "title": "Forbidden",
>   "status": 403,
>   "detail": "Missing or invalid X-CSRF-Token header",
>   "instance": "<request path>",
>   "code": "csrf_failed",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **429 Too Many Requests** (More than 5/minute per client IP):
> ```json
> {
>   "type": "https://errors.example.com/rate_limited",
>   "title": "Too Many Requests",
>   "status": 429,
>   "detail": "Too many requests. Please try again later.",
>   "instance": "<request path>",
>   "code": "rate_limited",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Auth Router]
>     Service[AuthService]
>     Repo[Repositories]
>     DB[(PostgreSQL)]
>
>     Client -->|1. POST /v1/auth/mfa/setup| Router
>     Router -->|2. start_mfa_setup| Service
>     Service -->|3. Store encrypted secret| Repo
>     Repo -->|4. UPDATE users.mfa_secret_encrypted| DB
>     Router -->|5. 200 secret + otpauth URI| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef repo fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Service service
>     class Repo repo
>     class DB db
> ```
>
> </div>
> </details>

</details>

---
### <a id="enable-mfa"></a>Enable MFA

<details>
<summary>Enable MFA (POST /v1/auth/mfa/enable)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v1/auth/mfa/enable` | POST | True | Activates MFA after verifying a code generated from the new secret. From then on sign-in requires a TOTP code. |

> <details>
> <summary>Request body</summary>
>
> **Fields:**
>
> - `code` (string, **Required**): 6-digit code.
> - Header `X-CSRF-Token` (**Required**).
>
> ```json
> {
>   "code": "492039"
> }
> ```
> </details>
>
> <details>
> <summary>Response body</summary>
>
> **204 No Content**. Session cookies are (re)set via `Set-Cookie` where noted.
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **400 Bad Request** (Setup not started or code wrong):
> ```json
> {
>   "type": "https://errors.example.com/invalid_mfa_code",
>   "title": "Bad Request",
>   "status": 400,
>   "detail": "Invalid authentication code",
>   "instance": "<request path>",
>   "code": "invalid_mfa_code",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **401 Unauthorized** (No valid session, or the session was revoked):
> ```json
> {
>   "type": "https://errors.example.com/not_authenticated",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Not authenticated",
>   "instance": "<request path>",
>   "code": "not_authenticated",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **403 Forbidden** (Session cookie present but `X-CSRF-Token` header missing or wrong):
> ```json
> {
>   "type": "https://errors.example.com/csrf_failed",
>   "title": "Forbidden",
>   "status": 403,
>   "detail": "Missing or invalid X-CSRF-Token header",
>   "instance": "<request path>",
>   "code": "csrf_failed",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **422 Unprocessable Entity** (Request body fails validation):
> ```json
> {
>   "type": "https://errors.example.com/validation_failed",
>   "title": "Validation Failed",
>   "status": 422,
>   "detail": "Input validation failed.",
>   "instance": "<request path>",
>   "code": "validation_failed",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a",
>   "errors": [
>     {
>       "field": "code",
>       "message": "String should match pattern '^\\d{6}$'",
>       "type": "string_pattern_mismatch"
>     }
>   ]
> }
> ```
>
> **429 Too Many Requests** (More than 10/minute per client IP):
> ```json
> {
>   "type": "https://errors.example.com/rate_limited",
>   "title": "Too Many Requests",
>   "status": 429,
>   "detail": "Too many requests. Please try again later.",
>   "instance": "<request path>",
>   "code": "rate_limited",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Auth Router]
>     Service[AuthService]
>     Repo[Repositories]
>     DB[(PostgreSQL)]
>
>     Client -->|1. POST /v1/auth/mfa/enable| Router
>     Router -->|2. confirm_mfa_setup| Service
>     Service -->|3. Verify TOTP, set mfa_enabled_at| Repo
>     Repo -->|4. UPDATE users| DB
>     Router -->|5. 204| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef repo fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Service service
>     class Repo repo
>     class DB db
> ```
>
> </div>
> </details>

</details>

---
### <a id="disable-mfa"></a>Disable MFA

<details>
<summary>Disable MFA (POST /v1/auth/mfa/disable)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v1/auth/mfa/disable` | POST | True | Turns MFA off and deletes the secret; requires a current code. |

> <details>
> <summary>Request body</summary>
>
> **Fields:**
>
> - `code` (string, **Required**): 6-digit code.
> - Header `X-CSRF-Token` (**Required**).
>
> ```json
> {
>   "code": "492039"
> }
> ```
> </details>
>
> <details>
> <summary>Response body</summary>
>
> **204 No Content**. Session cookies are (re)set via `Set-Cookie` where noted.
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **400 Bad Request** (MFA not enabled or code wrong):
> ```json
> {
>   "type": "https://errors.example.com/invalid_mfa_code",
>   "title": "Bad Request",
>   "status": 400,
>   "detail": "Invalid authentication code",
>   "instance": "<request path>",
>   "code": "invalid_mfa_code",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **401 Unauthorized** (No valid session, or the session was revoked):
> ```json
> {
>   "type": "https://errors.example.com/not_authenticated",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Not authenticated",
>   "instance": "<request path>",
>   "code": "not_authenticated",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **403 Forbidden** (Session cookie present but `X-CSRF-Token` header missing or wrong):
> ```json
> {
>   "type": "https://errors.example.com/csrf_failed",
>   "title": "Forbidden",
>   "status": 403,
>   "detail": "Missing or invalid X-CSRF-Token header",
>   "instance": "<request path>",
>   "code": "csrf_failed",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **422 Unprocessable Entity** (Request body fails validation):
> ```json
> {
>   "type": "https://errors.example.com/validation_failed",
>   "title": "Validation Failed",
>   "status": 422,
>   "detail": "Input validation failed.",
>   "instance": "<request path>",
>   "code": "validation_failed",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a",
>   "errors": [
>     {
>       "field": "code",
>       "message": "String should match pattern '^\\d{6}$'",
>       "type": "string_pattern_mismatch"
>     }
>   ]
> }
> ```
>
> **429 Too Many Requests** (More than 10/minute per client IP):
> ```json
> {
>   "type": "https://errors.example.com/rate_limited",
>   "title": "Too Many Requests",
>   "status": 429,
>   "detail": "Too many requests. Please try again later.",
>   "instance": "<request path>",
>   "code": "rate_limited",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Auth Router]
>     Service[AuthService]
>     Repo[Repositories]
>     DB[(PostgreSQL)]
>
>     Client -->|1. POST /v1/auth/mfa/disable| Router
>     Router -->|2. disable_mfa| Service
>     Service -->|3. Verify TOTP, clear secret| Repo
>     Repo -->|4. UPDATE users| DB
>     Router -->|5. 204| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef repo fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Service service
>     class Repo repo
>     class DB db
> ```
>
> </div>
> </details>

</details>

---
## Users Endpoints

### <a id="get-current-user"></a>Get Current User

<details>
<summary>Get Current User (GET /v2/user/me)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v2/user/me` | GET | True | Returns the profile information of the currently authenticated user based on session token. |

> <details>
> <summary>Request body</summary>
>
> No request body payload.
>
> ```json
> null
> ```
> </details>
>
> <details>
> <summary>Response body</summary>
>
> ```json
> {
>   "id": "d7e393b4-19dc-43ab-9a31-6ab9256123cb",
>   "email": "user@example.com",
>   "username": "friendly_llama_42",
>   "role": "user",
>   "emailVerified": true,
>   "mfaEnabled": false
> }
> ```
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **401 Unauthorized** (If auth cookie is missing, expired, or invalid):
> ```json
> {
>   "type": "https://errors.example.com/unauthenticated",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Missing credentials or invalid session token",
>   "instance": "<request path>",
>   "code": "unauthenticated",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **429 Too Many Requests** (If exceeding rate limit of 100 requests/minute):
> ```json
> {
>   "type": "https://errors.example.com/rate_limited",
>   "title": "Too Many Requests",
>   "status": 429,
>   "detail": "Too many requests. Please try again later.",
>   "instance": "<request path>",
>   "code": "rate_limited",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[User Router]
>     Auth[get_current_user Dependency]
>
>     Client -->|1. GET /v2/user/me| Router
>     Router -->|2. Verify HTTP Cookie| Auth
>     Auth -->|3. Valid Session| Router
>     Router -->|4. Return current user model| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef auth fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Auth auth
> ```
>
> </div>
> </details>

</details>

---

### <a id="delete-current-user"></a>Delete Current User

<details>
<summary>Delete Current User (DELETE /v2/user/me)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v2/user/me` | DELETE | True | Deletes the currently authenticated user's account and clears the session. |

> <details>
> <summary>Request body</summary>
>
> No request body payload.
>
> ```json
> null
> ```
> </details>
>
> <details>
> <summary>Response body</summary>
>
> ```json
> null
> ```
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **401 Unauthorized** (If auth cookie is missing, expired, or invalid):
> ```json
> {
>   "type": "https://errors.example.com/unauthenticated",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Missing credentials or invalid session token",
>   "instance": "<request path>",
>   "code": "unauthenticated",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **429 Too Many Requests** (If exceeding rate limit of 100 requests/minute):
> ```json
> {
>   "type": "https://errors.example.com/rate_limited",
>   "title": "Too Many Requests",
>   "status": 429,
>   "detail": "Too many requests. Please try again later.",
>   "instance": "<request path>",
>   "code": "rate_limited",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[User Router]
>     Auth[get_current_user Dependency]
>     Service[AuthService.remove]
>     DB[(PostgreSQL)]
>
>     Client -->|1. DELETE /v2/user/me| Router
>     Router -->|2. Verify HTTP Cookie| Auth
>     Auth -->|3. Valid Session| Service
>     Service -->|4. Hard-delete user & dependencies| DB
>     DB -->|5. Success| Service
>     Service -->|6. Delete Cookie & Return 204 No Content| Router
>     Router -->|7. 204 No Content| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef auth fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Auth auth
>     class Service service
>     class DB db
> ```
>
> </div>
> </details>

</details>

---

### <a id="list-users-admin"></a>List Users (admin)

<details>
<summary>List Users (admin) (GET /v2/users/)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v2/users/` | GET | True (`users:read_all`) | Lists all user accounts with pagination. Requires the `users:read_all` permission (granted to the `admin` role). |

> <details>
> <summary>Request body</summary>
>
> **Fields:**
>
> - `page` (integer, *Optional*, default `1`).
> - `pageSize` (integer, *Optional*, default `10`, max `100`).
> - `ordering` (string, *Optional*): `created_at` or `updated_at`, prefix `-` for descending.
>
> No request body.
> </details>
>
> <details>
> <summary>Response body</summary>
>
> ```json
> {
>   "founds": [
>     {
>       "id": "d7e393b4-19dc-43ab-9a31-6ab9256123cb",
>       "email": "user@example.com",
>       "username": "K3J9X2QW",
>       "role": "user",
>       "emailVerified": true,
>       "mfaEnabled": false,
>       "createdAt": "2026-10-16T09:00:00Z",
>       "lockedUntil": null
>     }
>   ],
>   "nextCursor": "eyJjIjoiMjAyNi0xMC0xNlQxMDoxNTowMCswMDowMCIsImkiOiIwYjdm..."
> }
> ```
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **401 Unauthorized** (No valid session, or the session was revoked):
> ```json
> {
>   "type": "https://errors.example.com/not_authenticated",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Not authenticated",
>   "instance": "<request path>",
>   "code": "not_authenticated",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **403 Forbidden** (Role lacks `users:read_all`):
> ```json
> {
>   "type": "https://errors.example.com/forbidden",
>   "title": "Forbidden",
>   "status": 403,
>   "detail": "You do not have permission to perform this action",
>   "instance": "<request path>",
>   "code": "forbidden",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **429 Too Many Requests** (More than 60/minute per client IP):
> ```json
> {
>   "type": "https://errors.example.com/rate_limited",
>   "title": "Too Many Requests",
>   "status": 429,
>   "detail": "Too many requests. Please try again later.",
>   "instance": "<request path>",
>   "code": "rate_limited",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Users Router]
>     Service[UserUseCases]
>     Repo[Repositories]
>     DB[(PostgreSQL)]
>
>     Client -->|1. GET /v2/users/| Router
>     Router -->|2. require_permission + UserUseCases.get_list| Service
>     Service -->|3. Paginated query| Repo
>     Repo -->|4. SELECT users| DB
>     Router -->|5. 200 page of users| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef repo fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Service service
>     class Repo repo
>     class DB db
> ```
>
> </div>
> </details>

</details>

---
## Todos Endpoints

### <a id="list-todos"></a>List Todos

<details>
<summary>List Todos (GET /v2/todos/)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v2/todos/` | GET | True | Retrieves a paginated list of todo items owned by the current authenticated user. Supports filtering. |

> <details>
> <summary>Query parameters (Request context)</summary>
>
> **Query Parameters:**
>
> - `page` (integer, *Optional*, default: `1`): The page number to retrieve. Must be >= 1.
> - `pageSize` (integer, *Optional*, default: `10`, max: `100`): Number of items per page. Values above `MAX_PAGE_SIZE` return 422.
> - `ordering` (string, *Optional*, default: `"-created_at"`): Field to sort by, prefix with `'-'` for descending order. Allowed: `created_at`, `updated_at`, `title`, `is_completed`. Other fields return 422.
> - `title` (string, *Optional*): Filter by partial case-insensitive title match.
> - `isActive` (boolean, *Optional*, default: `true`, accepts alternative alias: `is_active`): Filter by active (`true`) or archived (`false`) status.
>
> ```json
> {
>   "page": 1,
>   "pageSize": 10,
>   "ordering": "-createdAt",
>   "title": "optional_search_term",
>   "isActive": true
> }
> ```
> </details>
>
> <details>
> <summary>Response body</summary>
>
> ```json
> {
>   "founds": [
>     {
>       "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
>       "title": "Complete code review",
>       "isCompleted": false,
>       "createdAt": "2026-05-24T18:00:00Z",
>       "updatedAt": "2026-05-24T18:30:00Z"
>     }
>   ],
>   "searchOptions": {
>     "page": 1,
>     "pageSize": 10,
>     "ordering": "-createdAt",
>     "totalCount": 1
>   }
> }
> ```
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **401 Unauthorized** (If not signed in):
> ```json
> {
>   "type": "https://errors.example.com/unauthenticated",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Missing credentials or invalid session token",
>   "instance": "<request path>",
>   "code": "unauthenticated",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **422 Unprocessable Entity** (If querying with invalid query param types, e.g. non-integer page):
> ```json
> {
>   "type": "https://errors.example.com/validation_failed",
>   "title": "Validation Failed",
>   "status": 422,
>   "detail": "Input validation failed.",
>   "instance": "<request path>",
>   "code": "validation_failed",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a",
>   "errors": [
>     {
>       "field": "page",
>       "message": "Input should be a valid integer",
>       "type": "int_parsing"
>     }
>   ]
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Todos Router]
>     Service[TodoService.get_list]
>     Repo[TodoRepository.get_list]
>     DB[(PostgreSQL)]
>
>     Client -->|1. GET /v2/todos/| Router
>     Router -->|2. Inject query & auth| Service
>     Service -->|3. Fetch paginated list| Repo
>     Repo -->|4. SELECT with Filters/Pagination| DB
>     DB -->|5. Results & totalCount| Repo
>     Repo -->|6. Founds list & searchOptions| Service
>     Service -->|7. Serialize to TodoListResponse| Router
>     Router -->|8. 200 OK| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef repo fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Service service
>     class Repo repo
>     class DB db
> ```
>
> </div>
> </details>

</details>

---

### <a id="create-todo"></a>Create Todo

<details>
<summary>Create Todo (POST /v2/todos/)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v2/todos/` | POST | True | Creates a new todo item owned by the authenticated user. |

> <details>
> <summary>Request body</summary>
>
> **Fields:**
>
> - `title` (string, **Required**): The title of the task.
> - `description` (string, *Optional*, default: `null`): Detailed description of the task.
> - `isCompleted` (boolean, *Optional*, default: `false`): Whether the task has been finished.
>
> ```json
> {
>   "title": "Complete code review",
>   "description": "Review pull request #142 for the todo webapp",
>   "isCompleted": false
> }
> ```
> </details>
>
> <details>
> <summary>Response body</summary>
>
> ```json
> null
> ```
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **401 Unauthorized** (If not signed in):
> ```json
> {
>   "type": "https://errors.example.com/unauthenticated",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Missing credentials or invalid session token",
>   "instance": "<request path>",
>   "code": "unauthenticated",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **422 Unprocessable Entity** (If title is missing or a field has an invalid format):
> ```json
> {
>   "type": "https://errors.example.com/validation_failed",
>   "title": "Validation Failed",
>   "status": 422,
>   "detail": "Input validation failed.",
>   "instance": "<request path>",
>   "code": "validation_failed",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a",
>   "errors": [
>     {
>       "field": "title",
>       "message": "Field required",
>       "type": "missing"
>     }
>   ]
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Todos Router]
>     Service[TodoService.add]
>     Repo[TodoRepository.add]
>     DB[(PostgreSQL)]
>
>     Client -->|1. POST /v2/todos/| Router
>     Router -->|2. Validate TodoCreate Schema| Service
>     Service -->|3. INSERT todo item| Repo
>     Repo -->|4. INSERT| DB
>     DB -->|5. Success| Repo
>     Repo -->|6. Todo Model| Service
>     Service -->|7. 201 Created| Router
>     Router -->|8. 201 Created| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef repo fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Service service
>     class Repo repo
>     class DB db
> ```
>
> </div>
> </details>

</details>

---

### <a id="toggle-todo-archive-status"></a>Toggle Todo Archive Status

<details>
<summary>Toggle Todo Archive Status (POST /v2/todos/{_todo_id}:archive)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v2/todos/{_todo_id}:archive` | POST | True | Toggles the `is_active` status of a specific todo item. Requires ownership check. |

> <details>
> <summary>Request body</summary>
>
> No request body payload.
>
> ```json
> null
> ```
> </details>
>
> <details>
> <summary>Response body</summary>
>
> ```json
> null
> ```
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **401 Unauthorized** (If not signed in):
> ```json
> {
>   "type": "https://errors.example.com/unauthenticated",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Missing credentials or invalid session token",
>   "instance": "<request path>",
>   "code": "unauthenticated",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **404 Not Found** (If todo ID does not exist or belongs to another user):
> ```json
> {
>   "type": "https://errors.example.com/not_found",
>   "title": "Not Found",
>   "status": 404,
>   "detail": "Todo not found",
>   "instance": "<request path>",
>   "code": "not_found",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Todos Router]
>     Auth[check_ownership Dependency]
>     Service[TodoService.patch_attr]
>     DB[(PostgreSQL)]
>
>     Client -->|1. POST /v2/todos/id:archive| Router
>     Router -->|2. Check ownership & fetch| Auth
>     Auth -->|3. Valid & Owned| Service
>     Service -->|4. Toggle is_active field & UPDATE| DB
>     DB -->|5. Success| Service
>     Service -->|6. 200 OK| Router
>     Router -->|7. 200 OK| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef auth fill:#fbe9e7,stroke:#d84315,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Service service
>     class Auth auth
>     class DB db
> ```
>
> </div>
> </details>

</details>

---

### <a id="get-todo"></a>Get Todo

<details>
<summary>Get Todo (GET /v2/todos/{todo_id})</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v2/todos/{todo_id}` | GET | True | Retrieves a todo. Responds with `ETag: W/"<version>"` for use in `If-Match`. |

> <details>
> <summary>Request body</summary>
>
> No request body payload.
>
> ```json
> null
> ```
> </details>
>
> <details>
> <summary>Response body</summary>
>
> ```json
> {
>   "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
>   "title": "Complete code review",
>   "description": "Review pull request #142 for the todo webapp",
>   "isCompleted": false,
>   "userId": "d7e393b4-19dc-43ab-9a31-6ab9256123cb",
>   "createdAt": "2026-05-24T18:00:00Z",
>   "updatedAt": "2026-05-24T18:30:00Z"
> }
> ```
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **401 Unauthorized** (If not signed in):
> ```json
> {
>   "type": "https://errors.example.com/unauthenticated",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Missing credentials or invalid session token",
>   "instance": "<request path>",
>   "code": "unauthenticated",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **404 Not Found** (If todo ID does not exist or belongs to another user):
> ```json
> {
>   "type": "https://errors.example.com/not_found",
>   "title": "Not Found",
>   "status": 404,
>   "detail": "Todo not found",
>   "instance": "<request path>",
>   "code": "not_found",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Todos Router]
>     Auth[check_ownership Dependency]
>     Service[TodoService.get_by_id]
>     DB[(PostgreSQL)]
>
>     Client -->|1. GET /v2/todos/id| Router
>     Router -->|2. Check ownership & fetch| Auth
>     Auth -->|3. Valid & Owned| Service
>     Service -->|4. SELECT todo| DB
>     DB -->|5. Todo data| Service
>     Service -->|6. Serialize to Todo schema| Router
>     Router -->|7. 200 OK| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef auth fill:#fbe9e7,stroke:#d84315,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Service service
>     class Auth auth
>     class DB db
> ```
>
> </div>
> </details>

</details>

---

### <a id="update-todo"></a>Update Todo

<details>
<summary>Update Todo (PATCH /v2/todos/{_todo_id})</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v2/todos/{_todo_id}` | PATCH | True | Updates a todo. Optional `If-Match` header (ETag from GET): 412 `precondition_failed` if the todo changed meanwhile (body includes `current_etag`); the new `ETag` is returned. |

> <details>
> <summary>Request body</summary>
>
> **Fields:**
>
> - `title` (string, *Optional*, default: `null`): Updated title.
> - `description` (string, *Optional*, default: `null`): Updated description.
> - `isCompleted` (boolean, *Optional*, default: `null`): Updated completion status.
>
> ```json
> {
>   "title": "Complete code review v2",
>   "isCompleted": true
> }
> ```
> </details>
>
> <details>
> <summary>Response body</summary>
>
> ```json
> null
> ```
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **401 Unauthorized** (If not signed in):
> ```json
> {
>   "type": "https://errors.example.com/unauthenticated",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Missing credentials or invalid session token",
>   "instance": "<request path>",
>   "code": "unauthenticated",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **404 Not Found** (If todo ID does not exist or belongs to another user):
> ```json
> {
>   "type": "https://errors.example.com/not_found",
>   "title": "Not Found",
>   "status": 404,
>   "detail": "Todo not found",
>   "instance": "<request path>",
>   "code": "not_found",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Todos Router]
>     Auth[check_ownership Dependency]
>     Service[TodoService.patch]
>     Repo[TodoRepository.patch]
>     DB[(PostgreSQL)]
>
>     Client -->|1. PATCH /v2/todos/id| Router
>     Router -->|2. Check ownership & fetch| Auth
>     Auth -->|3. Valid & Owned| Service
>     Service -->|4. UPDATE fields| Repo
>     Repo -->|5. UPDATE| DB
>     DB -->|6. Success| Repo
>     Repo -->|7. Updated Todo| Service
>     Service -->|8. 200 OK| Router
>     Router -->|9. 200 OK| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef repo fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Service service
>     class Repo repo
>     class Auth auth
>     class DB db
> ```
>
> </div>
> </details>

</details>

---

### <a id="delete-todo"></a>Delete Todo

<details>
<summary>Delete Todo (DELETE /v2/todos/{_todo_id})</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v2/todos/{_todo_id}` | DELETE | True | Permanently deletes a todo task from the database. Requires ownership check and task to be inactive. |

> <details>
> <summary>Request body</summary>
>
> No request body payload.
>
> ```json
> null
> ```
> </details>
>
> <details>
> <summary>Response body</summary>
>
> ```json
> null
> ```
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **401 Unauthorized** (If not signed in):
> ```json
> {
>   "type": "https://errors.example.com/unauthenticated",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Missing credentials or invalid session token",
>   "instance": "<request path>",
>   "code": "unauthenticated",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **404 Not Found** (If todo ID does not exist, belongs to another user, or is still active - todo must be archived/inactive before permanent deletion):
> ```json
> {
>   "type": "https://errors.example.com/not_found",
>   "title": "Not Found",
>   "status": 404,
>   "detail": "Todo not found",
>   "instance": "<request path>",
>   "code": "not_found",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Todos Router]
>     Auth[check_ownership Dependency]
>     Service[TodoService.remove]
>     DB[(PostgreSQL)]
>
>     Client -->|1. DELETE /v2/todos/id| Router
>     Router -->|2. Check ownership & fetch if inactive| Auth
>     Auth -->|3. Valid & Inactive| Service
>     Service -->|4. DELETE FROM todos| DB
>     DB -->|5. Success| Service
>     Service -->|6. 204 No Content| Router
>     Router -->|7. 204 No Content| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef auth fill:#fbe9e7,stroke:#d84315,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Service service
>     class Auth auth
>     class DB db
> ```
>
> </div>
> </details>

</details>

---

## Audit Endpoints

### <a id="list-audit-logs"></a>List Audit Logs (admin)

<details>
<summary>List Audit Logs (admin) (GET /v2/audit-logs/)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v2/audit-logs/` | GET | True (`audit:read`) | Searches the append-only audit trail of security-relevant and administrative actions (sign-ins, lockouts, refresh-token reuse, password/MFA changes, account deletion). |

> <details>
> <summary>Request body</summary>
>
> **Fields:**
>
> - `action` (string, *Optional*, alias `action__eq`): exact action, e.g. `auth.signin.failed`.
> - `actorId` (UUID, *Optional*, alias `actor_id__eq`): acting user.
> - `outcome` (string, *Optional*, alias `outcome__eq`): `success` or `failure`.
> - `limit` (integer, *Optional*, default `10`, max `100`).
> - `cursor` (string, *Optional*): `nextCursor` from the previous page (keyset pagination, newest first). Malformed cursors return 400 `invalid_cursor`.
>
> No request body.
> </details>
>
> <details>
> <summary>Response body</summary>
>
> ```json
> {
>   "items": [
>     {
>       "id": "0b7f2c1e-8f1a-4f53-9c2d-3a1e5b7c9d10",
>       "createdAt": "2026-10-16T10:15:00Z",
>       "actorId": null,
>       "action": "auth.signin.failed",
>       "resourceType": null,
>       "resourceId": null,
>       "outcome": "failure",
>       "ipAddress": "203.0.113.7",
>       "userAgent": "Mozilla/5.0 ...",
>       "requestId": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a",
>       "details": {
>         "reason": "unknown_email"
>       }
>     }
>   ],
>   "searchOptions": {
>     "page": 1,
>     "pageSize": 10,
>     "ordering": "-created_at",
>     "totalCount": 1
>   }
> }
> ```
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **401 Unauthorized** (No valid session, or the session was revoked):
> ```json
> {
>   "type": "https://errors.example.com/not_authenticated",
>   "title": "Unauthenticated",
>   "status": 401,
>   "detail": "Not authenticated",
>   "instance": "<request path>",
>   "code": "not_authenticated",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **403 Forbidden** (Role lacks `audit:read`):
> ```json
> {
>   "type": "https://errors.example.com/forbidden",
>   "title": "Forbidden",
>   "status": 403,
>   "detail": "You do not have permission to perform this action",
>   "instance": "<request path>",
>   "code": "forbidden",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **429 Too Many Requests** (More than 60/minute per client IP):
> ```json
> {
>   "type": "https://errors.example.com/rate_limited",
>   "title": "Too Many Requests",
>   "status": 429,
>   "detail": "Too many requests. Please try again later.",
>   "instance": "<request path>",
>   "code": "rate_limited",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Audit Router]
>     Service[AuditService]
>     Repo[Repositories]
>     DB[(PostgreSQL)]
>
>     Client -->|1. GET /v2/audit-logs/| Router
>     Router -->|2. require_permission + AuditService.get_list| Service
>     Service -->|3. Filtered, paginated query| Repo
>     Repo -->|4. SELECT audit_logs| DB
>     Router -->|5. 200 page of entries| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef repo fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class Service service
>     class Repo repo
>     class DB db
> ```
>
> </div>
> </details>

</details>

---
## Health Endpoints

### <a id="liveness-probe"></a>Liveness Probe

<details>
<summary>Liveness Probe (GET /health/live)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/health/live` | GET | False | Process is up and the event loop responds. Never checks dependencies, so a database outage does not trigger restart storms. Use as the Kubernetes liveness probe. |

> <details>
> <summary>Request body</summary>
>
> No request body.
> </details>
>
> <details>
> <summary>Response body</summary>
>
> ```json
> {
>   "status": "alive"
> }
> ```
> </details>
>
> <details>
> <summary>Error body</summary>
>
> None: liveness only fails if the process cannot respond at all (the probe times out).
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Health Endpoints]
>
>     Client -->|1. GET /health/live| Router
>     Router -->|2. 200 alive| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef repo fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
> ```
>
> </div>
> </details>

</details>

---
### <a id="readiness-probe"></a>Readiness Probe

<details>
<summary>Readiness Probe (GET /health/ready)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/health/ready` | GET | False | Ready for traffic: PostgreSQL reachable, Redis reachable when `REDIS_URL` is set, and not shutting down. Use as the readiness probe; failing removes the instance from load balancing. `GET /health` is a deprecated alias. |

> <details>
> <summary>Request body</summary>
>
> No request body.
> </details>
>
> <details>
> <summary>Response body</summary>
>
> ```json
> {
>   "status": "ready",
>   "database": "ok",
>   "redis": "ok"
> }
> ```
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **503 Service Unavailable** (A dependency is unreachable, or the instance is draining for shutdown):
> ```json
> {
>   "type": "https://errors.example.com/service_unavailable",
>   "title": "Service Unavailable",
>   "status": 503,
>   "detail": "Database connection failed",
>   "instance": "<request path>",
>   "code": "service_unavailable",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client Frontend])
>     Router[Health Endpoints]
>     DB[(PostgreSQL)]
>
>     Client -->|1. GET /health/ready| Router
>     Router -->|2. SELECT 1 / Redis PING| DB
>     Router -->|3. 200 ready or 503| Client
>
>     classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
>     classDef route fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
>     classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000
>     classDef repo fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000
>     classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
>
>     class Client client
>     class Router route
>     class DB db
> ```
>
> </div>
> </details>

</details>

---

## Data Acquisition Endpoints

### <a id="data-acquisition-service"></a>Service contract and authentication

These endpoints belong to **data-acquisition** (`services/data-acquisition`), deployed separately from the identity service. Its machine-readable contract is [`services/data-acquisition/openapi.json`](/services/data-acquisition/openapi.json).

| Aspect | Behaviour |
| :--- | :--- |
| Authentication | `Authorization: Bearer <access token>` issued by the identity service (`/v1/auth/signin`), verified offline. Cookies are not accepted. Missing, invalid, expired or non-access tokens → 401. |
| Ownership | Owners (and admins) see, cancel and retry their jobs; anyone else gets 404 `acquisition_job_not_found`. |
| Worker role | `:start`, `:progress`, `:complete` and `:fail` require role `acquisition_worker` (or admin); otherwise 403. |
| Concurrency | Responses carry `ETag: W/"<version>"`; `If-Match` on `:cancel`/`:retry` → 412 `precondition_failed` (body has `current_etag`) when stale. |
| Errors | RFC 9457 Problem Details with stable codes: `invalid_job_name`, `invalid_source`, `invalid_max_attempts`, `invalid_progress`, `invalid_failure_reason` (422); `invalid_status_transition`, `retry_limit_reached`, `active_job_limit_reached`, `concurrent_modification` (409). |
| Transactions | One transaction per request; any 4xx/5xx rolls back. Domain events are published only after commit. |

### <a id="create-acquisition-job"></a>Create Acquisition Job

<details>
<summary>Create Acquisition Job (POST /v1/acquisition-jobs/)</summary>

| URL | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/v1/acquisition-jobs/` | POST | True (Bearer) | Queues a job for the caller. Returns 201 with `Location` and `ETag`. |

> <details>
> <summary>Request body</summary>
>
> **Fields:**
>
> - `name` (string, **Required**): 3-120 characters after whitespace normalisation.
> - `sourceType` (string, **Required**): `web` (http/https), `api` (https only) or `file` (s3/sftp).
> - `sourceUri` (string, **Required**): Must match the source type's schemes, include a host/bucket and contain no embedded credentials.
> - `maxAttempts` (integer, *Optional*, default: `3`): 1-10.
>
> ```json
> {
>   "name": "Product catalogue crawl",
>   "sourceType": "web",
>   "sourceUri": "https://example.org/catalogue",
>   "maxAttempts": 3
> }
> ```
> </details>
>
> <details>
> <summary>Response body</summary>
>
> ```json
> {
>   "id": "4b1d1f0e-2a3c-4e5f-8a9b-0c1d2e3f4a5b",
>   "ownerId": "d7e393b4-19dc-43ab-9a31-6ab9256123cb",
>   "name": "Product catalogue crawl",
>   "sourceType": "web",
>   "sourceUri": "https://example.org/catalogue",
>   "status": "queued",
>   "attempts": 0,
>   "maxAttempts": 3,
>   "canRetry": false,
>   "recordsCollected": 0,
>   "errorMessage": null,
>   "createdAt": "2026-10-20T12:00:00Z",
>   "startedAt": null,
>   "finishedAt": null,
>   "version": 1
> }
> ```
> </details>
>
> <details>
> <summary>Error body</summary>
>
> **422 Unprocessable Entity** (business rule: an `api` source must use https):
> ```json
> {
>   "type": "https://errors.example.com/invalid_source",
>   "title": "Business Rule Violation",
>   "status": 422,
>   "detail": "A api source must use one of: https",
>   "instance": "/v1/acquisition-jobs/",
>   "code": "invalid_source",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
>
> **409 Conflict** (the owner already has `ACTIVE_JOB_LIMIT_PER_OWNER` queued or running jobs):
> ```json
> {
>   "type": "https://errors.example.com/active_job_limit_reached",
>   "title": "Conflict",
>   "status": 409,
>   "detail": "You already have 10 active jobs (limit 10)",
>   "instance": "/v1/acquisition-jobs/",
>   "code": "active_job_limit_reached",
>   "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
> }
> ```
> </details>

> <details>
> <summary>Flow Diagram</summary>
>
> <div align="center">
>
> ```mermaid
> flowchart TD
>     Client([Client / BFF])
>     Router[acquisition_jobs router]
>     Auth[Bearer token verification]
>     UseCase[CreateJob use case]
>     Domain[JobName / DataSource / MaxAttempts + active-job policy]
>     Repo[SqlAlchemyJobRepository]
>     DB[(PostgreSQL schema data_acquisition)]
>     Events[EventPublisher after commit]
>
>     Client -->|1. POST /v1/acquisition-jobs/| Router
>     Router -->|2. Verify access token| Auth
>     Auth -->|3. Principal| UseCase
>     UseCase -->|4. Validate values| Domain
>     UseCase -->|5. count_active owner| Repo
>     UseCase -->|6. Apply policy, AcquisitionJob.create| Domain
>     UseCase -->|7. add| Repo
>     Repo -->|8. INSERT| DB
>     UseCase -->|9. AcquisitionJobQueued| Events
>     Router -->|10. 201 + Location + ETag| Client
> ```
>
> </div>
> </details>

</details>

---

### <a id="acquisition-job-lifecycle"></a>Job lifecycle endpoints

```
QUEUED --start--> RUNNING --complete--> COMPLETED
   |                 |
   |                 +--fail--> FAILED --retry--> QUEUED   (while attempts < maxAttempts)
   +-----cancel------+--cancel--> CANCELLED
```

| URL | Method | Caller | Body | Rule enforced by the `AcquisitionJob` aggregate |
| :--- | :--- | :--- | :--- | :--- |
| `/v1/acquisition-jobs/` | GET | owner (admin: `allOwners=true`) | — | Query: `status`, `page` (≥ 1), `pageSize` (1-100). Response `{ items, pageInfo: { page, pageSize, totalCount } }`. |
| `/v1/acquisition-jobs/{job_id}` | GET | owner/admin | — | Returns the job with `ETag`. |
| `/v1/acquisition-jobs/{job_id}:start` | POST | worker | — | Only `queued` jobs; increments `attempts`. |
| `/v1/acquisition-jobs/{job_id}:progress` | POST | worker | `{ "records": 250 }` | Only `running` jobs; `records` ≥ 1, added to `recordsCollected`. |
| `/v1/acquisition-jobs/{job_id}:complete` | POST | worker | — | Only `running` jobs; publishes `AcquisitionJobCompleted`. |
| `/v1/acquisition-jobs/{job_id}:fail` | POST | worker | `{ "reason": "Vendor returned 503" }` | Only `running` jobs; reason required (stored up to 1000 chars); publishes `AcquisitionJobFailed`. |
| `/v1/acquisition-jobs/{job_id}:retry` | POST | owner/admin (`If-Match` optional) | — | Only `failed` jobs with attempts left (else 409 `retry_limit_reached`); resets `recordsCollected`. |
| `/v1/acquisition-jobs/{job_id}:cancel` | POST | owner/admin (`If-Match` optional) | — | Only `queued`/`running` jobs; publishes `AcquisitionJobCancelled`. |

All lifecycle endpoints return the updated job (200) with its new `ETag`; a transition that is not allowed returns 409 `invalid_status_transition`.

---
