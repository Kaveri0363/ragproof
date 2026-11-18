# Diagnosing Kafka Consumer Lag

Consumer lag is alerted when the `payments-settlement` consumer group exceeds fifty
thousand messages of lag for more than ten minutes. The alert routes to the payments
on-call rota, not to the platform rota, because the usual cause is application slowness
rather than broker health.

Check three things in order. First, whether lag is growing on all partitions or just a
few: single-partition lag almost always means a hot key, most often a single high-volume
corporate debtor whose payments all hash to one partition. Second, consumer processing
time — the `payment.process.duration` histogram — because a p99 above four hundred
milliseconds means the consumer cannot keep up with peak inbound rate. Third, whether a
rebalance loop is in progress, visible as repeated `Attempt to heartbeat failed` lines in
the consumer log.

Scaling out only helps when lag is spread across partitions and the consumer count is
below the partition count. The `payments-settlement` topic has twenty-four partitions, so
adding a twenty-fifth consumer instance does nothing at all. For a hot key, the fix is a
repartition with a composite key of debtor id and settlement date, which is a planned
change and not an incident action.
