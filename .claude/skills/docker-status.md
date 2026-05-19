# docker-status

Show the status of all NutriChat Docker containers and verify the stack is healthy.

## Usage

```
/docker-status
```

## Process

Check running containers:

```bash
docker compose ps
```

Ping the Django API health:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3600/api/accounts/ 2>/dev/null || echo "API unreachable"
```

Check Redis connectivity from Django:

```bash
docker exec nutrihelp_django uv run python -c "import redis; r = redis.from_url('redis://nutrihelp_redis:6379'); r.ping(); print('Redis OK')" 2>/dev/null || echo "Redis not reachable"
```

Check Celery worker:

```bash
docker exec nutrihelp_celery uv run celery -A control inspect ping 2>/dev/null || echo "Celery worker not responding"
```

Report a summary table:

| Service | Status |
|---------|--------|
| Django  | UP/DOWN |
| PostgreSQL | UP/DOWN |
| Redis   | UP/DOWN |
| Celery  | UP/DOWN |
| ChromaDB | UP/DOWN |
