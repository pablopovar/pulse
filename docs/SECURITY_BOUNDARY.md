# Pulse application security boundary

Pulse has three explicit deployment modes, configured with `PULSE_SECURITY_MODE`.

## Application-authenticated mode

`PULSE_SECURITY_MODE=application`

This is the default and is required whenever direct access to Pulse cannot be ruled out.
All management routes require Pulse HTTP Basic authentication.

```env
PULSE_SECURITY_MODE=application
PULSE_ADMIN_USERNAME=pablo
PULSE_ADMIN_PASSWORD=<long-random-password>
PULSE_SECRET_KEY=<long-random-secret>
PULSE_SECURE_COOKIES=1
```

If the username or password is missing, management routes fail closed with HTTP 503.

## Reverse-proxy-authenticated mode

`PULSE_SECURITY_MODE=reverse_proxy`

Use this only when the reverse proxy is the authentication boundary and direct network access to Pulse's application port is blocked.

```env
PULSE_SECURITY_MODE=reverse_proxy
PULSE_PROXY_AUTH_HEADER=X-Pulse-Authenticated
PULSE_PROXY_AUTH_VALUE=<proxy-controlled-secret-or-assertion>
PULSE_SECRET_KEY=<long-random-secret>
PULSE_SECURE_COOKIES=1
```

The proxy must authenticate the operator, strip any client-supplied assertion header, inject the configured assertion only after authentication, terminate HTTPS, and prevent direct Internet access to Pulse's application port.

## Internal mode

`PULSE_SECURITY_MODE=internal`

This disables application-level management authentication and is valid only on a genuinely isolated trusted network.

## CSRF protection

All state-changing browser requests using `POST`, `PUT`, `PATCH`, or `DELETE` require a per-session CSRF token.

Pulse supplies it to forms as `_csrf_token` and to same-origin `fetch()` mutations as `X-CSRF-Token`.
The session cookie is HttpOnly, SameSite=Strict, and Secure when `PULSE_SECURE_COOKIES=1`.

## Explicit public report capability

The only routes intentionally outside management authentication are:

- `GET /reports/<report_id>`
- `GET /reports/_static/<path>`
- `POST /reports/<report_id>/reply`

The reply route remains CSRF-protected and still obeys the report's discussion-enabled rule.
A report ID is an explicit bearer capability, not management authentication and not security by obscurity.

Disable all public reports with:

```env
PULSE_PUBLIC_REPORTS_ENABLED=0
```

Revoke individual report capabilities with:

```env
PULSE_REVOKED_REPORT_IDS=id1,id2,id3
```

Disabled or revoked report IDs return HTTP 404.

Everything not explicitly listed as public is management/internal surface.
