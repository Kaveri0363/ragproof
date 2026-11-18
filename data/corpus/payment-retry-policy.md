# Payment Retry Policy

Transient failures are retried with exponential backoff. The base delay is two seconds
and the multiplier is three, giving delays of 2s, 6s, 18s, 54s and 162s. After five
attempts the payment moves to the dead letter queue. Jitter of up to twenty percent is
added to every delay to prevent thundering-herd behaviour when a downstream service
recovers.

Only errors classified as retryable are retried: connection timeouts, HTTP 502, 503 and
504 from the clearing gateway, and Kafka producer timeouts. Business rejections are never
retried, because the outcome will not change and each attempt consumes a settlement
window slot. A payment that has already been debited is never retried without an
explicit reversal, to avoid double debits.

The retry counter is stored on the payment record itself rather than in the message
header, so that a consumer restart does not reset it. Retry state survives redeployment.

If the clearing gateway is fully down, suppress retries entirely by setting
`payments.retry.enabled=false` in the config map and draining to the dead letter queue.
Retrying against a known-down dependency multiplies load on recovery and has twice caused
a secondary incident during the recovery window.
