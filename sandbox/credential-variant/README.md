# Credential Variant Smoke Test

This sandbox project is a second PR-scan smoke test.

It intentionally uses:
- a different project folder name
- different credential values
- different variable names from the first sample

Expected outcome:
- hardcoded secret findings still appear cleanly
- TLS verification disabled is reported cleanly
