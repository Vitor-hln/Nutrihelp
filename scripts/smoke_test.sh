#!/bin/sh
set -e
echo "== 1. Stack up =="
docker compose ps

echo "== 2. Django admin (espera 200/302) =="
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3600/admin/

echo "== 3. pgvector extension =="
docker exec nutrihelp_postgres psql -U nutrihelp_user -d nutrihelp -c "\dx" | grep vector

echo "== 4. Celery -> Redis ping =="
docker exec nutrihelp_celery uv run celery -A control inspect ping

echo "== 5. Persistencia (down + up preserva dados) =="
echo "Rodar manualmente: docker compose down && docker compose up -d, depois conferir registros no Postgres"

echo "SMOKE TEST OK"
