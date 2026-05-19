# test

Run Django tests inside the `nutrihelp_django` container. Supports filtering by app, module, or specific test class/method.

## Usage

```
/test [app_or_test_path]
```

## Examples

- `/test` — run all tests
- `/test accounts` — run all tests in the accounts app
- `/test patients` — run all tests in the patients app
- `/test rag` — run all tests in the rag app
- `/test accounts.tests.model_test.test_custom_user_model` — run a specific test module
- `/test accounts.tests.view_test.TestLogin.test_login_success` — run a specific test method

## Process

```bash
docker exec -it nutrihelp_django uv run manage.py test $ARGUMENTS --verbosity=2
```

If no arguments, run the full suite:

```bash
docker exec -it nutrihelp_django uv run manage.py test --verbosity=2
```

After tests complete, summarize: total tests run, failures, errors, and any relevant output.
