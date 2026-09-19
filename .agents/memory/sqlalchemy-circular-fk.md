---
name: SQLAlchemy circular FK pattern
description: How to model two tables that each have a nullable FK to the other (e.g. team.manager_worker_id -> worker.id and worker.team_id -> team.id) without create_all/drop_all deadlocking on table order.
---

When two tables mutually reference each other via FK (a team's manager is a
worker, but a worker belongs to a team; similarly a worker can fill a
position, but a position doesn't need to exist before the worker does),
declare the "back" reference with `ForeignKey(..., use_alter=True, name=...)`
on the nullable side.

**Why:** without `use_alter`, SQLAlchemy's `Base.metadata.create_all`/
`drop_all` cannot determine a table creation order for a real cycle and
raises a circular dependency error.

**How to apply:** put `use_alter=True` and an explicit constraint `name=` on
whichever FK is logically "the optional pointer added after both rows can
exist" (e.g. `Team.manager_worker_id -> worker.id`, `Worker.position_id ->
position.id`). SQLAlchemy then creates the tables first and adds those FK
constraints in a second pass via `ALTER TABLE`.
