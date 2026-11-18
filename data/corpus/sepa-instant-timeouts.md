# SEPA Instant Timeouts

SEPA Instant Credit Transfer requires an end-to-end response within twenty seconds under
the scheme rulebook. The platform enforces an internal budget of twelve seconds, leaving
headroom for the scheme leg.

A timeout is not the same as a failure. When the internal budget expires the payment
enters state `TIMEOUT_UNKNOWN` and a status inquiry is scheduled after sixty seconds. The
payment must not be retried while its outcome is unknown, because the beneficiary may
already have been credited.

Status inquiries are retried up to ten times over fifteen minutes. If the outcome is
still unknown after that, the payment is escalated to payments operations for manual
investigation with the scheme; engineering does not resolve `TIMEOUT_UNKNOWN` payments
by changing state directly in the database.

The most common cause of internal budget breach is sanctions screening latency, which is
why screening timeouts are tracked as a separate metric rather than folded into overall
processing time.
