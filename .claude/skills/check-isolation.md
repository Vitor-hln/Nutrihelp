# check-isolation

Run the data isolation test suite to verify that no nutritionist can access another's patients.
This is a critical LGPD and business-logic invariant — run after any change to patient querysets or views.

## Usage

```
/check-isolation
```

## Process

Run isolation-specific tests across all apps:

```bash
docker exec -it nutrihelp_django uv run manage.py test patients.tests accounts.tests --verbosity=2 2>&1 | grep -E "(test_|ERROR|FAIL|OK|Ran)"
```

Then run a broader cross-app isolation check:

```bash
docker exec -it nutrihelp_django uv run manage.py test --verbosity=2 -k "isolation" 2>&1
```

After running, check the codebase for any unscoped patient queries (must always filter by nutritionist):

```bash
grep -rn "Patient.objects.all()" nutrihelp_app/ --include="*.py" | grep -v test | grep -v migration
grep -rn "Patient.objects.filter(" nutrihelp_app/ --include="*.py" | grep -v "nutritionist" | grep -v test | grep -v migration
```

Report:
1. Test results (pass/fail)
2. Any unscoped `Patient.objects.all()` calls found (these are bugs)
3. Any `Patient.objects.filter()` calls missing `nutritionist=` scope
