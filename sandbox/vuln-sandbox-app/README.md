# vuln-sandbox-app

Intentionally vulnerable training project for PR security scanning. This app is unsafe by design and should never be deployed.

## Local Run

```bash
cd sandbox/vuln-sandbox-app
npm install
npm start
```

App URL: `http://localhost:3001`

## Intentional Vulnerabilities

1. Exposed secrets
- Checked-in `.env` with secret-like values.
- Hardcoded secret material in `src/server.js`.
- `/debug/secrets` returns secret values.

2. Broken access control
- `GET /api/profile/:id` is IDOR; any logged-in user can read any profile by ID.
- `GET /admin/users` has no authorization check and exposes all users.

3. SQL injection
- `POST /login` builds SQL using string interpolation with user input.

4. Command injection
- `GET /tools/ping?host=...` passes user input directly into `child_process.exec`.

5. Stored XSS
- `POST /notes` stores unsanitized content and `/` renders it directly into HTML.

## Seeded Test Users

- `admin / admin123`
- `alice / password123`
- `bob / qwerty`

## Purpose

This project exists to validate SAST/secret scanning and to support secure code review practice.