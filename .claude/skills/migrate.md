# migrate

Create and apply Django migrations in the correct order.

## Usage

```
/migrate [app]
```

## Examples

- `/migrate` — makemigrations + migrate (all apps)
- `/migrate accounts` — makemigrations + migrate for accounts app only

## Process

Step 1 — create migrations:

```bash
docker exec -it nutrihelp_django uv run manage.py makemigrations $ARGUMENTS
```

Step 2 — apply migrations:

```bash
docker exec -it nutrihelp_django uv run manage.py migrate
```

Report which migrations were created and applied. If a migration already exists and nothing changed, say so.
