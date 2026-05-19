# shell

Open the Django shell inside the `nutrihelp_django` container for interactive inspection or one-off scripts.

## Usage

```
/shell [python_expression]
```

## Examples

- `/shell` — open interactive shell (user runs commands manually)
- `/shell "from accounts.models import User; print(User.objects.count())"` — run a one-liner

## Process

If a Python expression is provided in $ARGUMENTS, run it non-interactively:

```bash
docker exec -it nutrihelp_django uv run manage.py shell -c "$ARGUMENTS"
```

If no arguments, show the command for the user to run themselves (interactive mode requires a terminal):

```
Run this in your terminal:
docker exec -it nutrihelp_django uv run manage.py shell
```
