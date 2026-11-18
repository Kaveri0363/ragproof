# Schema Registry Compatibility

All Avro schemas for payment events are registered with the schema registry under
`BACKWARD_TRANSITIVE` compatibility. That means a new schema version must be readable by
consumers using any previous version, not merely the immediately preceding one.

In practice this permits adding an optional field with a default and removing a field
that already had a default. It forbids adding a required field, renaming a field, or
narrowing a type such as changing a long to an int. Renaming is the mistake most often
attempted; the correct approach is to add the new field, migrate consumers, and remove
the old field in a later release.

Compatibility is enforced twice: in the build, where the `schema-check` Gradle task fails
the pipeline, and at publish time by the registry itself. The build check exists because
discovering an incompatible schema at deploy time means a rollback rather than a failed
build.

Never delete a schema version from the registry to work around a failing check. Consumers
replaying from an older offset will fail to deserialize, which surfaces as poison-pill
messages in the dead letter queue rather than as an obvious registry error.
