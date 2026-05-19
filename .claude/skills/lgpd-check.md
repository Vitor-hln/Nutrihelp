# lgpd-check

Audit the codebase for LGPD compliance issues: CPF in URLs, unmasked sensitive data in logs, missing consent fields, and UUID enforcement on patient PKs.

## Usage

```
/lgpd-check
```

## Process

1. Check for CPF in URL patterns (must never appear):

```bash
grep -rn "cpf" nutrihelp_app/ --include="*.py" | grep -iE "(path|url|pk|slug)" | grep -v test | grep -v migration
```

2. Check Patient model uses UUID as PK:

```bash
grep -rn "class PerfilPaciente\|class Patient" nutrihelp_app/ --include="*.py" -A 5 | grep -E "(UUIDField|primary_key)"
```

3. Check serializers don't expose CPF in list endpoints:

```bash
grep -rn "cpf" nutrihelp_app/ --include="serializers.py" -A 2
```

4. Check consent field exists on patient registration:

```bash
grep -rn "consentimento\|lgpd_consent\|consent" nutrihelp_app/ --include="*.py" | grep -v test
```

5. Check logging doesn't include sensitive fields:

```bash
grep -rn "logger\.\(info\|debug\|warning\)" nutrihelp_app/ --include="*.py" | grep -iE "(cpf|senha|password|health|saude|diagnostico)"
```

Report findings by category with severity: CRITICAL (data leak) / WARNING (potential issue) / OK.
