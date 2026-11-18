# API Rate Limiting

The public payments API applies a token bucket per client id with a sustained rate of one
hundred requests per second and a burst capacity of two hundred. Limits are enforced at
the gateway, before authentication, so that an unauthenticated flood cannot reach the
service.

A throttled request receives HTTP 429 with a `Retry-After` header in seconds. Clients are
expected to honour it; repeated ignoring of `Retry-After` by one client is grounds for a
temporary limit reduction, applied by the API platform team.

Limits are per client id and not per IP address, because several large clients route
through shared infrastructure and IP-based limits punished them collectively.

Batch submission endpoints have a separate, lower limit of ten requests per second
because each batch may carry up to five thousand payments. A client migrating from single
to batch submission must be told about this, as the higher single-payment limit does not
apply and the migration otherwise looks like a regression to them.
