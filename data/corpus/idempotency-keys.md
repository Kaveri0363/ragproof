# Idempotency Keys

Every write endpoint on the payments API requires an `Idempotency-Key` header. The key is
a client-generated UUID and is scoped to the client id, so two different clients may use
the same key without collision.

The service stores the key with the response body and status code for twenty-four hours.
A repeated request with the same key returns the stored response without re-executing the
operation. A repeated key with a different request body returns HTTP 422 with error code
`IDEMPOTENCY_KEY_REUSE`, because silently returning the first response for a different
payload would hide a client bug.

In-flight requests are protected by a short-lived lock on the key. A second request
arriving while the first is still executing receives HTTP 409 and should be retried by the
client after a short delay.

Idempotency records are stored in the same database transaction as the payment itself.
This is the reason the payments service cannot use a separate cache-only store for
idempotency: a key written outside the transaction can survive a rolled-back payment and
permanently block a legitimate retry.
