# Transaction Service API

**Base URL (local):** `http://localhost:8003`

The Transaction Service owns the commerce domain. It manages a digital wallet per user,
coordinates product reservations (with automatic timeout expiry), and processes purchases
via atomic wallet debit operations. It also exposes transaction history.

All endpoints require authentication (`Authorization: Bearer <token>`).

---

## Health Check

### `GET /health`

```json
{ "status": "ok", "service": "transaction-service" }
```

---

## Wallet

### `GET /wallet/balance`

Returns the authenticated user's current wallet balance in EUR.

**Response 200**

```json
{ "balance": 250.00 }
```

---

### `POST /wallet/deposit`

Adds funds to the authenticated user's wallet.

**Request body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `amount` | float (> 0) | yes | Amount in EUR to deposit |

**Request example**

```json
{ "amount": 100.00 }
```

**Response 200**

```json
{ "balance": 350.00 }
```

**Response 422** — invalid amount (e.g. zero or negative)

---

## Products (Transaction View)

Products in this service mirror the inventory catalogue and track commerce-specific state.

### `GET /products`

Lists all products. Optional query parameter `state` to filter.

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `state` | `Available` \| `Reserved` \| `Sold` | Filter by state |

**Response 200** — array of `ProductResponse`

```json
[
  {
    "id": 1,
    "title": "iPhone 13 Pro 128GB",
    "price": 420.00,
    "state": "Available",
    "seller_id": "alice@example.com",
    "reserved_by": null
  }
]
```

---

### `POST /products/{product_id}/reserve`

Places a time-limited reservation on a product. Only one reservation per product is active
at a time.

**Path parameter**

| Parameter | Type | Description |
|-----------|------|-------------|
| `product_id` | integer | Product to reserve |

**Reservation timeout**

The reservation expires after `RESERVATION_TIMEOUT_SECONDS` (default: 600 s / 10 min).
A background daemon automatically releases expired reservations and transitions the product
back to `Available`.

**Response 200** — reservation created

```json
{
  "id": 1,
  "state": "Reserved",
  "reserved_by": "buyer@example.com"
}
```

**Response 404** — product not found

**Response 409** — product already reserved or sold (`ReservationConflictException`)

**Response 403** — seller cannot reserve their own product

---

### `DELETE /products/{product_id}/reserve`

Explicitly releases an active reservation. Only the buyer who reserved the product can
release it.

**Response 200** — reservation released

```json
{ "id": 1, "state": "Available" }
```

**Response 400** — product is not in `Reserved` state (`ReservationReleaseInvalidStateException`)

**Response 403** — not the reservation owner

---

### `POST /products/{product_id}/purchase`

Completes the purchase of a reserved product. The buyer's wallet is debited atomically;
the seller's wallet is credited.

**Path parameter**

| Parameter | Type | Description |
|-----------|------|-------------|
| `product_id` | integer | Product to purchase (must be `Reserved` by the caller) |

**Response 200** — purchase completed

```json
{
  "transaction_id": 17,
  "product_id": 1,
  "buyer_id": "buyer@example.com",
  "seller_id": "alice@example.com",
  "amount": 420.00,
  "created_at": "2026-05-19T11:30:00Z"
}
```

**Response 402** — insufficient wallet funds (`InsufficientFundsException`)

**Response 403** — product is reserved by a different user (`PurchaseReservedByOtherException`)

**Response 404** — product not found

**Response 409** — invalid state transition (`InvalidStateTransitionException`)

---

## Transactions

### `GET /transactions`

Returns the authenticated user's full transaction history (as buyer or seller), newest first.

**Query parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | integer | 0 | Pagination offset |
| `limit` | integer | 50 | Maximum records to return |

**Response 200** — `TransactionHistoryListResponse`

```json
{
  "total": 3,
  "transactions": [
    {
      "transaction_id": 17,
      "product_id": 1,
      "product_title": "iPhone 13 Pro 128GB",
      "buyer_id": "buyer@example.com",
      "seller_id": "alice@example.com",
      "amount": 420.00,
      "role": "buyer",
      "created_at": "2026-05-19T11:30:00Z"
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `role` | `"buyer"` or `"seller"` — the authenticated user's role in the transaction |

---

## Error Reference

| Exception class | HTTP status | Meaning |
|----------------|------------|---------|
| `ProductNotFoundException` | 404 | Product ID does not exist |
| `ProductForbiddenException` | 403 | Caller is not allowed to act on this product |
| `InvalidStateTransitionException` | 409 | Requested state transition is not allowed by the state machine |
| `InsufficientFundsException` | 402 | Buyer's wallet balance is below the product price |
| `AtomicOperationException` | 500 | Database write failed mid-transaction (rolled back) |
| `ReservationConflictException` | 409 | Product is already reserved or sold |
| `PurchaseReservedByOtherException` | 403 | Product is reserved by a different user |
| `ReservationReleaseInvalidStateException` | 400 | Cannot release — product is not currently reserved |

---

## Reservation Cleanup Daemon

A background thread runs inside the Transaction Service and periodically scans for
reservations whose `reserved_at` timestamp exceeds `RESERVATION_TIMEOUT_SECONDS`.
Expired reservations are released automatically, transitioning the product back to
`Available`. The cleanup interval is controlled by
`RESERVATION_CLEANUP_INTERVAL_SECONDS` (default: 60 s).
