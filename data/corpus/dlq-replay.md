# Dead Letter Queue Replay

Messages land in the dead letter queue after five failed retry attempts, or immediately
if a poison-pill deserialization error occurs. The DLQ topic is
`payments.settlement.dlq` and retains messages for fourteen days.

Before replaying anything, establish why the messages failed. Replaying a batch that
failed for a business reason will simply refill the DLQ and burn a settlement window.
Group the DLQ contents by the `x-failure-reason` header first.

Replay is performed with the `dlq-replay` job, which reads a list of message ids from a
file and republishes them to the source topic with the retry counter reset and an
`x-replayed-from` header set for audit. Replay is rate limited to two hundred messages
per second by default so that a large replay does not itself cause consumer lag.

Replay requires two-person approval recorded in the incident ticket, because a replay of
already-settled payments is the fastest way to create duplicate debits. The job refuses
to run without the `--incident` flag naming a ticket. Always run with `--dry-run` first
and confirm the count matches the expected number of failures before the real run.
