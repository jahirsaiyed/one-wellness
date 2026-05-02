# Security Specification — GCC Wellness Platform

**Standard:** OWASP Top 10 addressed before launch.
**Regulation:** UAE PDPL (Federal Decree-Law No. 45/2021), Saudi PDPL, HIPAA-equivalent practices for health data.
**Pre-launch requirement:** OWASP ZAP automated scan + manual penetration test must both pass before any real users are onboarded.

---

## 1. Authentication Security

### JWT Configuration

```python
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30
JWT_ALGORITHM = "RS256"        # Asymmetric — private key signs, public key verifies
JWT_PRIVATE_KEY = settings.JWT_PRIVATE_KEY  # RSA-2048 private key from Secrets Manager
JWT_PUBLIC_KEY = settings.JWT_PUBLIC_KEY    # RSA-2048 public key (can be distributed)
```

**Token claims:**
```json
{
  "sub": "user-uuid",
  "role": "client",
  "totp_verified": true,
  "iat": 1746360000,
  "exp": 1746360900,
  "jti": "token-unique-id"    // For revocation tracking
}
```

**Token storage (frontend):**
- Access token: `httpOnly; Secure; SameSite=Strict` cookie
- Refresh token: `httpOnly; Secure; SameSite=Strict` cookie (separate cookie)
- Never stored in `localStorage` or `sessionStorage`

**Refresh token rotation:**
```python
# On every refresh token use:
1. Validate old refresh token (signature + expiry + not revoked in Redis)
2. Generate new access + refresh tokens
3. Invalidate old refresh token in Redis (add to revocation set)
4. Return new tokens
# Concurrent refresh with same token returns 401 (token already rotated)
```

### Rate Limiting (Redis-backed)

```python
# Implemented as FastAPI middleware using slowapi (limits library)
RATE_LIMITS = {
    "POST /auth/login": "10/15minutes",
    "POST /auth/totp/verify": "5/5minutes",
    "POST /auth/register": "5/hour",
    "POST /mood/anonymous": "5/hour",       # Per IP
    "POST /companion/chat": "60/hour",       # Per user
}
```

### Password Requirements

```python
# Enforced by Pydantic validator
PASSWORD_MIN_LENGTH = 10
PASSWORD_REQUIRES_UPPERCASE = True
PASSWORD_REQUIRES_LOWERCASE = True
PASSWORD_REQUIRES_DIGIT = True
PASSWORD_REQUIRES_SPECIAL = True
PASSWORD_BCRYPT_ROUNDS = 12
```

### TOTP (Two-Factor Authentication)

- Library: `pyotp`
- Algorithm: TOTP (RFC 6238), HMAC-SHA1
- Time step: 30 seconds
- Clock skew tolerance: ±1 step (30 seconds)
- QR code: `pyotp.totp.TOTP.provisioning_uri()` → `qrcode` library → base64 PNG
- Backup codes: 8 single-use codes, bcrypt-hashed, invalidated on use
- Mandatory for: `therapist`, `platform_admin`
- Optional for: `client`

---

## 2. Encryption

### At-Rest Encryption (Application Layer)

PHI columns encrypted before writing to PostgreSQL. Encryption is at the **application layer** (not just disk encryption) so the database engine itself cannot read plaintext PHI.

```python
from cryptography.fernet import Fernet
import base64
import hashlib

class PHIEncryption:
    """AES-256 via Fernet (AES-128-CBC under the hood; 256-bit keys via derivation)."""

    def __init__(self):
        # Master secret from environment (Secrets Manager in production)
        self.master_key = settings.PHI_ENCRYPTION_KEY  # 32-byte hex string

    def get_user_key(self, user_id: UUID) -> bytes:
        """Derive per-user key: HKDF(master_key, salt=user_id)"""
        import hashlib, hmac
        salt = str(user_id).encode()
        derived = hmac.new(self.master_key.encode(), salt, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(derived)

    def encrypt(self, plaintext: str, user_id: UUID) -> bytes:
        key = self.get_user_key(user_id)
        f = Fernet(key)
        return f.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes, user_id: UUID) -> str:
        key = self.get_user_key(user_id)
        f = Fernet(key)
        return f.decrypt(ciphertext).decode()
```

**Columns encrypted:**

| Table | Column | Why Encrypted |
|---|---|---|
| `ai_conversations` | `messages` | PHI: full conversation content |
| `mood_entries` | `note` | PHI: mental health note text |
| `session_notes` | `content` | PHI: clinical notes |
| `client_profiles` | `intake_data` | PHI: presenting concerns, preferences |
| `corporate_accounts` | `sso_config` | Confidential: IdP metadata |
| `bank_accounts` | `iban` | PCI: bank account identifiers |

**Key rotation procedure:**
1. Generate new master key
2. Run migration script: re-encrypt all PHI columns with new key
3. Update Secrets Manager
4. Deploy new application version pointing to new key
5. Verify decryption works in staging before production

### In-Transit Encryption

- All HTTPS traffic: TLS 1.3 minimum
- TLS 1.0 and 1.1 disabled at load balancer
- HTTP Strict Transport Security: `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- Certificate: Let's Encrypt (auto-renewed) or Cloudflare managed certificate
- Agora video: E2EE via WebRTC insertable streams (separate from platform TLS)

### Agora E2EE

```javascript
// Frontend: Agora SDK with insertable streams
const client = AgoraRTC.createClient({ mode: 'rtc', codec: 'vp8' });

// Enable E2EE (Agora Media SDK)
const encryption = {
    encryptionMode: "aes-128-gcm2",
    encryptionKey: sessionKey,    // Per-session AES-128 key derived from agora_channel_id
    encryptionSalt: channelSalt,  // Random bytes from server
};
await client.setEncryptionConfig(encryption.encryptionMode, encryption.encryptionKey, encryption.encryptionSalt);
```

---

## 3. Role-Based Access Control (RBAC)

### Role Hierarchy

```
platform_admin (+ optional is_safety_officer sub-role)
    ├── Full read access to all non-PHI data
    ├── Therapist verification, content management, audit log access
    └── CANNOT read: ai_conversations content, mood_entry notes, session_notes

hr_admin
    ├── Own corporate account management
    ├── Anonymized utilization reports only
    └── CANNOT see: individual session data, employee health data

therapist (+ mandatory TOTP)
    ├── Own profile, own sessions, own assigned clients
    ├── Client mood data (ONLY if client has granted consent)
    └── CANNOT access: other therapists' clients, conversation content

client
    ├── Own profile, own sessions, own conversations, own mood data
    └── CANNOT access: any other user's data
```

### FastAPI Dependency Guards

```python
from fastapi import Depends, HTTPException, status

def require_role(*roles: str):
    async def checker(token: dict = Depends(verify_jwt)):
        if token["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return token
    return checker

def require_totp():
    async def checker(token: dict = Depends(verify_jwt)):
        if not token.get("totp_verified"):
            raise HTTPException(status_code=403, detail="TOTP verification required")
        return token
    return checker

def require_safety_officer():
    async def checker(token: dict = Depends(verify_jwt)):
        if token["role"] != "platform_admin" or not token.get("is_safety_officer"):
            raise HTTPException(status_code=403, detail="Safety officer role required")
        return token
    return checker

# Usage in routes:
@router.get("/therapist/dashboard", dependencies=[Depends(require_role("therapist")), Depends(require_totp())])
@router.get("/admin/crisis-logs", dependencies=[Depends(require_safety_officer())])
```

### Resource-Level Authorization

Beyond role guards, every data-fetching endpoint enforces ownership:

```python
# Example: client can only read own mood entries
async def get_mood_entries(user_id: UUID = Path(...), current_user: dict = Depends(verify_jwt)):
    if str(current_user["sub"]) != str(user_id):
        if current_user["role"] != "therapist":
            raise HTTPException(403, "Access denied")
        # Therapist path: check consent
        consent = await db.get_mood_consent(client_id=user_id, therapist_id=current_user["sub"])
        if not consent:
            raise HTTPException(403, "Client has not granted mood data access")
```

---

## 4. Input Validation & Injection Prevention

### SQL Injection
- All DB queries via SQLAlchemy ORM or `text()` with bound parameters
- **No string interpolation in SQL queries — ever**
- Raw SQL only in migration files where parameterized queries are not available

```python
# CORRECT
result = await db.execute(
    select(User).where(User.email == email)
)

# CORRECT (raw SQL with params)
await db.execute(text("SELECT * FROM users WHERE email = :email"), {"email": email})

# NEVER DO THIS
await db.execute(f"SELECT * FROM users WHERE email = '{email}'")
```

### XSS Prevention
- React/Next.js default escaping prevents reflected XSS
- `dangerouslySetInnerHTML` prohibited in codebase (`eslint-plugin-react` rule)
- Content Security Policy header:
  ```
  Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-{random}'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://r2.example.com; connect-src 'self' https://api.gcc-wellness.com wss://rtm.agora.io
  ```

### CSRF Prevention
- SameSite=Strict cookies: CSRF protection for form submissions from cross-origin
- Double-submit cookie pattern for state-changing API calls from JavaScript:
  ```http
  X-CSRF-Token: {token from cookie}
  ```
- API endpoints also accept Bearer token auth (no cookies needed for API clients)

### File Upload Security
- Files accepted: PDF, JPG, PNG (license docs), MP3, MP4 (content)
- MIME type verified server-side (not trusting `Content-Type` header)
- File size limit: 10MB for documents, 200MB for content media
- Files stored in Cloudflare R2 with randomized UUIDs — never original filenames
- Virus scanning: ClamAV scan before committing file to permanent storage (Sprint 6+)

---

## 5. Data Privacy & PDPL Compliance

### UAE PDPL Article 29 — Right to Erasure

```python
class AccountDeletionService:
    async def initiate_deletion(self, user_id: UUID):
        # 1. Soft delete — immediate
        await db.execute(
            update(User).where(User.id == user_id).values(deleted_at=datetime.utcnow())
        )
        # 2. Revoke all active JWT tokens
        await redis.set(f"revoked:user:{user_id}", "1", ex=86400 * 30)
        # 3. Queue hard-delete job
        await task_queue.enqueue(hard_delete_user, user_id, schedule_in=timedelta(days=30))
        # 4. Log to audit_log
        await audit_log.write("user_deletion_requested", user_id)

    async def hard_delete(self, user_id: UUID):
        # Purge PHI tables
        await db.execute(delete(AiConversation).where(AiConversation.user_id == user_id))
        await db.execute(delete(MoodEntry).where(MoodEntry.user_id == user_id))
        await db.execute(delete(SessionNote).where(SessionNote.therapist_id == user_id))
        await db.execute(delete(ClientProfile).where(ClientProfile.user_id == user_id))
        # Anonymize billing (keep for legal compliance)
        await db.execute(
            update(Payment).where(Payment.client_id == user_id)
            .values(client_id=None)
        )
        await db.execute(
            update(User).where(User.id == user_id)
            .values(email=f"deleted_{user_id}@deleted.invalid", full_name="[Deleted]", hashed_password=None)
        )
        await audit_log.write("user_deleted", user_id)
```

### Data Minimization

| Principle | Implementation |
|---|---|
| Collect minimum data | Intake form: 5 questions only; no demographic data beyond language/timezone |
| Purpose limitation | Intake data used only for matching; not shared with therapists without explicit consent |
| Anonymization | PostHog events: `user_id` hashed; no names or emails in analytics events |
| AI prompts | User identified only by opaque UUID in all AI provider calls |
| Logs | No PHI in application logs; `user_id` used, not email or name |

### Data Residency
- MVP: Render Frankfurt (EU) — acceptable for UAE/KSA under current guidance
- v2: AWS ap-middle-east-1 (Bahrain) — data stays in GCC region
- R2: Cloudflare R2 with jurisdiction binding to EU until v2, then Middle East

### Consent Records

```python
class ConsentService:
    async def record_consent(self, user_id: UUID, consent_type: str, granted: bool):
        # consent_type: "mood_sharing", "recording", "marketing_emails"
        await audit_log.write(
            event_type=f"consent_{consent_type}_{'granted' if granted else 'revoked'}",
            actor_id=user_id,
            resource_type="consent",
            metadata={"consent_type": consent_type, "value": granted}
        )
```

---

## 6. API Security Headers

Applied via FastAPI middleware to all responses:

```python
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(self)"
    # CSP set per route (strict on API, more permissive on video session page)
    return response
```

---

## 7. Webhook Security (Tap Payments)

```python
import hmac, hashlib

def verify_tap_webhook(payload: bytes, signature_header: str) -> bool:
    """
    Tap sends HMAC-SHA256 of the payload using the webhook secret.
    Returns False and logs a security alert if signature is invalid.
    """
    expected = hmac.new(
        settings.TAP_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature_header):
        await audit_log.write("invalid_webhook_signature", metadata={"source": "tap_payments"})
        return False
    return True
```

---

## 8. PHI Logging Prevention

### Server-Side
```python
# logging_config.py
class PHIScrubber(logging.Filter):
    PHI_PATTERNS = [
        re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        re.compile(r'\+?[\d\s\-\(\)]{10,15}'),  # Phone numbers
    ]

    def filter(self, record):
        msg = str(record.getMessage())
        for pattern in self.PHI_PATTERNS:
            msg = pattern.sub('[REDACTED]', msg)
        record.msg = msg
        return True
```

### CI Pipeline Check
```bash
# check-phi-leaks.sh — runs on every CI build
# Scans staged log output and source files for PII/PHI patterns
if grep -rE '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' \
   --include="*.log" --include="*.py" \
   --exclude-dir=".git" \
   --exclude="*.env.example" .; then
    echo "PHI LEAK DETECTED in source or logs — build failed"
    exit 1
fi
echo "PHI check passed"
```

---

## 9. Dependency Security

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
```

- Dependabot PRs with critical/high CVEs are auto-merged after CI passes
- Manual review required for major version bumps
- `pip-audit` runs in CI to catch known vulnerabilities before deploy

---

## 10. Penetration Test Scope (Pre-Launch)

**Methodology:** OWASP Testing Guide v4

**In scope:**
- All API endpoints (`/v1/**`)
- Authentication flows (JWT, OAuth2, SAML, TOTP)
- Payment webhook receiver
- File upload endpoints
- WebSocket connections

**Out of scope (for initial pen test):**
- Agora video infrastructure (separate Agora security review)
- Cloudflare R2 (cloud provider's responsibility)

**Expected test categories:**
- A01: Broken Access Control — test RBAC, IDOR on all resource endpoints
- A02: Cryptographic failures — verify ciphertext in DB, TLS config
- A03: Injection — SQL, command injection
- A05: Security misconfiguration — headers, CORS, debug mode off
- A07: Authentication failures — brute force, token replay, session fixation
- A08: Software integrity — dependency scanning
- A10: SSRF — any URL-fetching functionality

**Sign-off required from:** External penetration tester + platform security officer before public launch.

---

## 11. Incident Response

### P0 Incidents (crisis service failure or data breach)

| Step | Action | Owner | SLA |
|---|---|---|---|
| 1 | PagerDuty alert fires automatically | System | < 2 min |
| 2 | On-call engineer acknowledges | Engineer | < 5 min |
| 3 | Assess scope; if data breach: activate Data Breach Protocol | Lead | < 15 min |
| 4 | Contain: revoke tokens, disable affected endpoints if needed | Engineer | < 30 min |
| 5 | Notify affected users (UAE PDPL: within 72 hours of discovery) | Legal/Lead | < 72 hours |
| 6 | Post-incident report | Lead | < 7 days |

### Data Breach Protocol
1. Identify what data was accessed (use audit_log)
2. Identify which users are affected
3. Rotate all JWT signing keys (forces all users to re-login)
4. Rotate PHI encryption keys and re-encrypt affected data
5. Notify UAE Telecommunications and Digital Government Regulatory Authority (TDRA) within 72 hours
6. Notify affected users within the notification window required by UAE PDPL
