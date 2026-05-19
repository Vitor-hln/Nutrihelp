# manage

Run any Django management command inside the `nutrihelp_django` container via uv.

## Usage

```
/manage <command>
```

## Examples

- `/manage migrate`
- `/manage makemigrations`
- `/manage createsuperuser`
- `/manage shell`
- `/manage collectstatic --noinput`

## Process

Run the command the user provided:

```bash
docker exec -it nutrihelp_django uv run manage.py $ARGUMENTS
```

If no arguments provided, show available commands:

```bash
docker exec -it nutrihelp_django uv run manage.py help
```
