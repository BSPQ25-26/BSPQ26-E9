# Inventory Service API

**Base URL (local):** `http://localhost:8002`

The Inventory Service owns the product catalogue: creating, reading, updating, and deleting
listings, plus image uploads. Products stored here represent the *listing* view; the
Transaction Service maintains a separate copy for commerce state.

---

## Health Check

### `GET /health`

```json
{ "status": "ok" }
```

---

## Products

### `GET /api/v1/products`

Returns a list of all products, optionally filtered. No authentication required.

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `state` | `Available` \| `Reserved` \| `Sold` | Filter by availability state |
| `category` | string (min 1 char) | Filter by category name (case-insensitive) |
| `min_price` | float (≥ 0) | Minimum product price in EUR |
| `max_price` | float (≥ 0) | Maximum product price in EUR |
| `condition` | `New` \| `Like New` \| `Good` \| `Fair` \| `Poor` | Filter by item condition |
| `q` | string (min 1 char) | Full-text keyword search across title and description |

**Response 200** — array of `ProductOut`

```json
[
  {
    "id": 1,
    "title": "iPhone 13 Pro 128GB",
    "description": "Used for one year, minor screen scratches, battery at 87%.",
    "price": 420.00,
    "category": "Electronics",
    "condition": "Good",
    "state": "Available",
    "seller_id": "alice@example.com",
    "image_url": "/uploads/abc123.jpg",
    "created_at": "2026-04-01T12:00:00Z"
  }
]
```

---

### `POST /api/v1/products`

Creates a new product listing. Requires authentication.

**Request** — `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | yes | Product title |
| `description` | string | yes | Detailed description |
| `price` | float | yes | Asking price in EUR |
| `category` | string | yes | Product category |
| `condition` | enum | yes | `New`, `Like New`, `Good`, `Fair`, or `Poor` |
| `image` | file | no | JPEG/PNG image; stored locally or on Supabase Storage |

**Response 201** — `ProductOut` (see schema above)

**Response 401** — not authenticated

---

### `GET /api/v1/products/{product_id}`

Returns a single product by ID.

**Path parameter**

| Parameter | Type | Description |
|-----------|------|-------------|
| `product_id` | integer | Unique product identifier |

**Response 200** — `ProductOut`

**Response 404**

```json
{ "detail": "Product not found" }
```

---

### `PUT /api/v1/products/{product_id}`

Updates a product listing. The authenticated user must be the seller.

**Request body** — `ProductUpdate` (all fields optional)

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | New title |
| `description` | string | New description |
| `price` | float | New price in EUR |
| `category` | string | New category |
| `condition` | enum | New condition |
| `state` | enum | New state (`Available`, `Reserved`, `Sold`) |

**Response 200** — updated `ProductOut`

**Response 403** — not the seller

**Response 404** — product not found

---

### `DELETE /api/v1/products/{product_id}`

Deletes a product listing. The authenticated user must be the seller.

**Response 204** — deleted successfully

**Response 403** — not the seller

**Response 404** — product not found

---

## Image Uploads

Static image files are served at `/uploads/<filename>`.

When the `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` environment variables are set,
images are uploaded to Supabase Storage and their public URL is stored in `image_url`.
Otherwise images are stored on the local filesystem under `data/uploads/`.

---

## ProductOut Schema

```json
{
  "id": 1,
  "title": "string",
  "description": "string",
  "price": 0.0,
  "category": "string",
  "condition": "Good",
  "state": "Available",
  "seller_id": "user@example.com",
  "image_url": "string | null",
  "created_at": "2026-01-01T00:00:00Z"
}
```

### State enum

| Value | Meaning |
|-------|---------|
| `Available` | Listing is visible and can be reserved |
| `Reserved` | A buyer has an active reservation |
| `Sold` | Sale completed; listing is closed |

### Condition enum

| Value | Meaning |
|-------|---------|
| `New` | Never used, in original packaging |
| `Like New` | Used briefly, no visible wear |
| `Good` | Normal signs of use, fully functional |
| `Fair` | Noticeable wear but still functional |
| `Poor` | Heavy wear or minor defects |
