# Audit Log Retention

Payment audit events are written to an append-only store and retained for seven years to
meet regulatory obligations. Records are immutable: corrections are appended as new
events referencing the original event id, and no process may update or delete an audit
row.

Audit events cover state transitions, screening decisions, manual interventions, and every
read of a payment record by a named user. The read events exist because access to customer
payment data is itself auditable.

Personal data in audit events is pseudonymised: account identifiers are stored as a
keyed hash, with the key held in the hardware security module. This allows an
investigator with the appropriate approval to resolve an identifier while keeping the
raw store free of directly identifying data.

Retention is enforced by a lifecycle policy on the underlying storage. Because deletion
is irreversible and the seven-year clock starts at event time rather than payment
creation, any change to the retention configuration requires compliance approval and is
treated as a change with regulatory impact.
