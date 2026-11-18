# Secrets and Certificate Rotation

Service credentials are rotated every ninety days and scheme connectivity certificates
every twelve months. Rotation is performed by the platform team through the secrets
manager; secrets are never committed to the repository or pasted into the incident
channel.

The scheme gateway uses mutual TLS. The certificate has a thirty-day expiry warning and a
seven-day critical alert. A certificate that expires unnoticed takes the entire scheme
connection down and has historically been the single largest cause of full settlement
outages across the industry, which is why the seven-day alert pages the on-call rather
than raising a ticket.

Rotation is a two-step process: the new credential is added and both are accepted for a
twenty-four hour overlap window, then the old credential is removed. Skipping the overlap
window turns a routine rotation into an outage, because instances pick up the new secret
only on their next restart.

Verify after rotation that every instance reports the new credential version in its health
endpoint before removing the old one.
