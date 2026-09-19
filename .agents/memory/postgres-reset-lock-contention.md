---
name: Postgres drop_all/reseed lock contention with an open request session
description: A "reset demo data" (or similar) endpoint that drops and recreates all tables can hang or block if it runs on the same DB session that is servicing the HTTP request.
---

Dropping and recreating every table (e.g. via SQLAlchemy `Base.metadata.drop_all` /
`create_all`, typically wrapped in a seed-reset script) while the FastAPI
request handler's own `db: Session = Depends(get_db)` still has an open
transaction on the same connection causes lock contention against Postgres —
the DDL can hang waiting on a lock the request's own session is holding.

**Why:** discovered building a demo "reset all data" endpoint: the naive
implementation (call the reset script directly inside the route, using the
injected `db` session for anything else in the same request) intermittently
blocked.

**How to apply:** in the route/service handling a full reset, call
`db.close()` on the request's own session *before* invoking the
drop-all/reseed script, then open a fresh `SessionLocal()` afterward for
anything the response needs to read back (e.g. settings). Same pattern
applies to any endpoint that needs to run schema-level DDL mid-request.
