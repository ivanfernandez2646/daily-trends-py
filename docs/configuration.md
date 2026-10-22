# Configuration

Settings are read from environment variables, then from a `.env` file in the working directory
(see `.env.example`), then from the defaults below. The test suite never reads `.env`. Invalid
settings stop the API at startup with exit code 1.

| Variable | Default | Description |
|---|---|---|
| `ENV` | `dev` | `production`, `dev` or `test`; selects the default `MONGO_URL` |
| `MONGO_URL` | `dev`: `mongodb://localhost:27017/daily-trends-dev`, `test`: `mongodb://localhost:27017/daily-trends-test`, `production`: required | MongoDB connection string |
| `PORT` | `5000` | HTTP port |
| `TIMEZONE` | `Europe/Madrid` | IANA zone that decides when a business day starts; the server's `TZ` is ignored |
| `SCRAPE_TIMEOUT_SECONDS` | `10` | Timeout of each request to a scraped site, > 0 |
| `SCRAPE_SCHEDULE_ENABLED` | `true` | Scrape every source at startup and then every `SCRAPE_INTERVAL_SECONDS`; `false` leaves only `/feed/scrap` |
| `SCRAPE_INTERVAL_SECONDS` | `7200` | Time from the end of a scheduled run to the start of the next one, > 0 |
| `AUTH_SECRET_KEY` | `dev` and `test`: a fixed development key, `production`: required | Signs the access tokens (HS256), at least 32 characters, never shown in errors or logs. Changing it invalidates every token. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `AUTH_TOKEN_TTL_SECONDS` | `28800` (8 hours) | How long an access token stays valid after login, > 0 |

On macOS, port 5000 is used by AirPlay Receiver. Either turn the receiver off or put `PORT=5123` in a
local `.env` (git-ignored): both the API and `docker compose` read it.

## Administrators

Administrators manage the CMS. There is no registration endpoint: create one from the command line,
against the database of `MONGO_URL` (pending migrations are applied first, so an empty database
works):

```bash
uv run daily-trends-py create-admin --email admin@example.com
```

The password is asked twice without echo and needs at least 12 characters. The email is asked
for when `--email` is missing, and is stored trimmed and lowercased. Scripts pass the password on
standard input instead, read once from its first line (`--email` is then required):

```bash
printf '%s\n' "$ADMIN_PASSWORD" | uv run daily-trends-py create-admin --email admin@example.com --password-stdin
```

The command exits with code 1 and creates nothing for an invalid email, a short password, passwords
that do not match or an email that already exists. Changing passwords and removing users are done
directly in MongoDB ([S11](../specs/users/S11-authentication.md)). To create one in production, see
[R5](deployment.md#runbook).
