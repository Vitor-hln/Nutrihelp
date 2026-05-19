# logs

View logs from NutriChat containers. Defaults to the Django app container.

## Usage

```
/logs [container] [--tail N]
```

## Containers

- `django` (default) → `nutrihelp_django`
- `celery` → `nutrihelp_celery`
- `redis` → `nutrihelp_redis`
- `chroma` → `nutrihelp_chromadb`

## Examples

- `/logs` — last 100 lines from Django container
- `/logs celery` — last 100 lines from Celery worker
- `/logs django --tail 50` — last 50 lines from Django

## Process

Map the container alias from $ARGUMENTS (default: django → nutrihelp_django), extract --tail N if present (default 100):

```bash
docker logs nutrihelp_django --tail 100
```

Highlight any ERROR or WARNING lines in the summary.
