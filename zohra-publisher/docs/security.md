# Security

## Principles

1. **Secrets from environment only** — never hardcoded in source code
2. **Least privilege** — future agents get only the credentials they need
3. **Defense in depth** — multiple layers of protection

## Authentication

- Admin login via HTTP Basic Auth → returns JWT token
- JWT tokens used for subsequent API requests
- Tokens expire (configurable, default 60 minutes)
- Design allows future OAuth2/SSO replacement

## Secrets Management

- All secrets loaded from environment variables
- `.env` file excluded from git via `.gitignore`
- `.env.example` contains only placeholders
- Application passwords (WordPress) stored separately from main credentials

## Logging Security

- Sensitive-data redaction in all log output
- Patterns matched: password, secret, token, api_key, app_password, authorization
- Stack traces logged internally but NEVER exposed in API responses

## API Security

- CORS origins configurable (not wildcarded in production)
- Request-ID correlation for debugging
- Input validation via Pydantic
- SQL injection protection through SQLAlchemy ORM
- No `eval()` or shell execution from user-controlled values
- Custom exceptions map to safe API error codes

## Prompt Injection Defense

The system architecturally separates:
- **System instructions** — trusted prompts that control agent behavior
- **Untrusted external content** — web pages, RSS feeds, user input

External content MUST NEVER become executable system-level instructions. This is enforced at the architectural level, not just through prompt engineering.

## Future Security (planned)

- Role-based access control
- API key authentication for service-to-service
- Rate limiting per client/endpoint
- Request size limits
- Audit trail for all administrative actions
