# Cross-service contracts

The models in `biomero_schema.zarr` and `biomero_schema.imports` are wire
contracts between BIOMERO-owned services. They provide shared validation while
leaving storage, OMERO access, event persistence, locking, and Zarr I/O to the
consumer that owns those operations.

The stable serialized form uses camelCase field aliases and is produced with
`to_dict()`. Each contract family carries its own integer `schema`; this is
independent of the workflow descriptor version.

## Boundaries

These contracts:

- can identify managed canonical Zarr data and its pixels;
- can snapshot the ordered canonical inputs to a workflow;
- can describe omitted image arrays in a shallow result;
- can request optional importer lifecycle operations.

They do not:

- redefine OME-NGFF or RFC-8;
- prescribe a database or storage-root implementation;
- make an embedded ISCC claim self-verifying;
- require third-party workflows to interpret BIOMERO metadata.
