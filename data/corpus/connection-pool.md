# Database Connection Pool Exhaustion

The payments service uses HikariCP with a maximum pool size of thirty connections per
instance and a connection timeout of three seconds. Pool exhaustion surfaces as
`SQLTransientConnectionException: Connection is not available, request timed out after
3000ms`, usually alongside a latency spike rather than errors.

The three usual causes are a slow query holding connections, a leaked connection from a
path that does not close its resources, and simply too many instances multiplied by pool
size exceeding the database's own connection limit. Thirty connections times sixteen
instances is four hundred and eighty connections, which exceeds the primary's limit of
four hundred, so scaling out the service can itself cause exhaustion.

Check `hikaricp_connections_active` against `hikaricp_connections_max` first, then the
database's longest-running query. A single long-running reporting query has caused this
twice.

Raising the pool size is almost always the wrong fix. The pool is a queue: making it
longer increases latency instead of throughput once the database is the bottleneck.
