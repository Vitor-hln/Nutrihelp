# rag-smoke-test

Run a quick end-to-end smoke test of the RAG pipeline: index a test document, query it, and verify a coherent response is returned.

## Usage

```
/rag-smoke-test
```

## Process

Run the RAG integration tests:

```bash
docker exec -it nutrihelp_django uv run manage.py test rag --verbosity=2
```

Then check that Celery can process an indexing task (verify worker is alive):

```bash
docker exec -it nutrihelp_celery uv run celery -A control inspect active
```

Check vector store connectivity (pgvector or chroma):

```bash
docker exec -it nutrihelp_django uv run manage.py shell -c "
from rag.vector_store import get_vector_store
vs = get_vector_store()
print('Vector store OK:', type(vs).__name__)
"
```

Report:
1. RAG test results
2. Celery worker status (active tasks or idle)
3. Vector store connection status
4. Any errors or misconfigurations
