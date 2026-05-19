# Auth Service API

**Base URL (local):** `http://localhost:8001`
**Base URL (production):** configured via `AUTH_SERVICE_URL` environment variable

The Auth Service owns user identity: registration, login, social OAuth, JWT issuance,
public user profiles, and the ratings system.

---

## Authentication

Most endpoints in other services require a JWT access token issued by this service.
Pass it as a Bearer token in every request:

```
Authorization: Bearer <access_token>
```

Tokens are signed with `HS256` using the shared `SECRET_KEY` environment variable and
contain `{"sub": "<user_email>"}` as the payload subject.

---

## Health Check

### `GET /health`

Returns the service liveness status. Used by Docker healthcheck probes.

**Response 200**

```json
{ "status": "ok" }
```

---

## Registration & Login

### `POST /auth/register`

Creates a new user account.

**Request body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string (email) | yes | Must be a valid e-mail address |
| `password` | string | yes | Plain-text password; hashed with bcrypt before storage |

**Request example**

```json
{
  "email": "alice@example.com",
  "password": "s3cret!"
}
```

**Response 200** — user created successfully

```json
{
  "id": 42,
  "email": "alice@example.com",
  "created_at": "2026-05-19T10:00:00Z"
}
```

**Response 400** — e-mail already registered

```json
{ "detail": "Email already registered" }
```

---

### `POST /auth/login`

Authenticates an existing user and returns a JWT access token.

**Request body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string (email) | yes | Registered e-mail address |
| `password` | string | yes | Plain-text password |

**Request example**

```json
{
  "email": "alice@example.com",
  "password": "s3cret!"
}
```

**Response 200**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Response 401** — invalid credentials

```json
{ "detail": "Invalid credentials" }
```

---

### `GET /auth/protected`

Protected test endpoint. Returns the authenticated user's identity.
Requires a valid `Authorization: Bearer <token>` header.

**Response 200**

```json
{
  "message": "acceso permitido",
  "user": "alice@example.com"
}
```

**Response 401** — missing or invalid token

```json
{ "detail": "Not authenticated" }
```

---

## Social Authentication (OAuth)

The social auth flow redirects users through the provider's consent screen and
issues a Wallabot JWT on success.

### `GET /auth/social/login/{provider}`

Initiates the OAuth redirect to the specified provider.

**Path parameter**

| Parameter | Values | Description |
|-----------|--------|-------------|
| `provider` | `google`, `facebook` | OAuth provider to redirect to |

**Response 302** — redirect to provider consent screen

---

### `GET /auth/social/callback/{provider}`

OAuth callback URL. The provider redirects the user here after consent.
Exchanges the authorization code for a Wallabot JWT.

**Path parameter**

| Parameter | Values | Description |
|-----------|--------|-------------|
| `provider` | `google`, `facebook` | Must match the `login` call |

**Response 200** — login or registration succeeded

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## User Profiles

### `GET /users/{user_id}/profile`

Returns the public profile of a user.

**Path parameter**

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | integer | Unique user identifier |

**Response 200**

```json
{
  "username": "alice@example.com",
  "member_since": "2026-01-10T08:30:00Z",
  "avg_rating": 4.7,
  "active_listing_count": 3
}
```

| Field | Description |
|-------|-------------|
| `username` | User's e-mail address (used as display name) |
| `member_since` | Account creation timestamp (ISO 8601) |
| `avg_rating` | Average star rating received; `null` if not yet rated |
| `active_listing_count` | Products currently `Available` or `Reserved` in Inventory Service |

**Response 404** — user not found

```json
{ "detail": "Usuario no encontrado" }
```

---

### `GET /users/{user_id}/ratings`

Returns paginated ratings received by a user.

**Path parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | integer | Unique user identifier |

**Query parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | integer | 0 | Number of records to skip (pagination offset) |
| `limit` | integer | 20 | Maximum records to return |

**Response 200**

```json
[
  {
    "reviewer_username": "bob@example.com",
    "stars": 5,
    "review_text": "Great seller, fast shipping!",
    "created_at": "2026-03-15T14:22:00Z"
  }
]
```

---

## Ratings

### `POST /ratings`

Submits a star rating for another user after a completed transaction.
Requires authentication.

**Request body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `to_user_id` | integer | yes | ID of the user being rated |
| `stars` | integer | yes | Rating from 1 to 5 |
| `review_text` | string | no | Optional free-text review |

**Request example**

```json
{
  "to_user_id": 7,
  "stars": 5,
  "review_text": "Excellent transaction!"
}
```

**Response 201** — rating recorded

```json
{ "id": 88, "stars": 5, "review_text": "Excellent transaction!" }
```
