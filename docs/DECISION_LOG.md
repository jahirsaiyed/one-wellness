# Architecture Decision Log (ADL) — GCC Wellness Platform

Architecture decisions that have lasting implications. Recorded here to explain *why* we made each decision, not just what we decided.

**Format:** ADR (Architecture Decision Record) — lightweight version.

---

## ADR-001: AI Provider Abstraction Layer
**Date:** 2026-05-02 | **Status:** Accepted

**Context:** Multiple AI providers exist (Claude, GPT-4o, Gemini). Vendor lock-in risk is high in a mental health context where provider policies around data retention can change. Cost and capability differences between providers are significant.

**Decision:** All AI calls go through an `AIProvider` abstract base class. Concrete adapters for each provider. Active provider selected via `AI_PROVIDER` environment variable. Zero code changes required to switch providers.

**Consequences:**
- (+) Can switch providers in minutes if Anthropic has an outage or policy change
- (+) A/B testing of providers is possible via env var
- (-) Additional abstraction layer to maintain
- (-) Embedding provider is always OpenAI (Anthropic doesn't offer embeddings) — this is hardcoded in `AnthropicAdapter.embed()`

**Alternatives rejected:** Direct Anthropic SDK calls in business logic (rejected: lock-in), LangChain (rejected: heavy abstraction, slow to update for new Claude features)

---

## ADR-002: PostgreSQL over NoSQL for Core Data
**Date:** 2026-05-02 | **Status:** Accepted

**Context:** Platform has complex relational data (users ↔ sessions ↔ bookings ↔ payments). Health data requires ACID guarantees. pgvector extension provides vector similarity search for AI matching without a separate vector DB.

**Decision:** PostgreSQL 16 as the only persistent store for structured data. pgvector extension for therapist matching embeddings.

**Consequences:**
- (+) ACID transactions for payment and booking operations
- (+) pgvector eliminates the need for Pinecone/Weaviate (reduces operational complexity)
- (+) REVOKE UPDATE, DELETE on audit tables enforced natively at DB level
- (-) Vertical scaling limits vs. distributed NoSQL (acceptable at MVP scale)
- (-) Full-text search is good but not Elasticsearch-grade at extreme scale

**Alternatives rejected:** MongoDB (rejected: eventual consistency unacceptable for payments), DynamoDB (rejected: complex access patterns, GCC data residency uncertain)

---

## ADR-003: FastAPI over Django/Node.js for Backend
**Date:** 2026-05-02 | **Status:** Accepted

**Context:** Backend needs: async-first (streaming SSE for AI), Python for AI integrations (anthropic SDK, openai SDK), type safety, auto-generated OpenAPI docs, fast iteration.

**Decision:** FastAPI with Python 3.12+, async SQLAlchemy, and Pydantic v2.

**Consequences:**
- (+) Native async support for AI streaming and WebSockets
- (+) Pydantic v2 request/response validation is 5x faster than v1
- (+) auto-generated OpenAPI docs from route definitions
- (+) Same language as AI SDKs (Python) — no cross-language boundary
- (-) Less mature admin ecosystem than Django
- (-) No built-in ORM (SQLAlchemy configured separately)

---

## ADR-004: Next.js 14 App Router over Other Frontend Frameworks
**Date:** 2026-05-02 | **Status:** Accepted

**Context:** Need RTL support from day one, server-side rendering for SEO (therapist profiles), PWA for mobile-first GCC users, internationalization (next-intl).

**Decision:** Next.js 14 with App Router, Tailwind CSS, next-intl for i18n, PWA via `@ducanh2912/next-pwa`.

**Consequences:**
- (+) `dir` attribute set per locale enables RTL layout at CSS level
- (+) App Router enables granular loading states and streaming UI
- (+) `next-intl` integrates cleanly with App Router layouts
- (-) App Router is newer; some third-party libraries still have Pages Router assumptions
- (-) Server Components add mental model complexity for state management

---

## ADR-005: Agora over Twilio Video / Daily.co for Video
**Date:** 2026-05-02 | **Status:** Accepted

**Context:** Therapy sessions require reliable low-latency video from GCC. WebRTC insertable streams for E2EE. Native SDK for web PWA.

**Decision:** Agora RTC SDK for video/audio. Daily.co documented as fallback integration.

**Consequences:**
- (+) Agora has PoPs in Middle East (UAE, KSA); lowest latency for GCC users
- (+) WebRTC insertable streams E2EE supported in web SDK
- (+) Per-minute pricing is lower than Twilio Video for our expected volume
- (-) Agora is Chinese-owned; some enterprises may have compliance concerns
- (-) Proprietary SDK (not open standards-based like Jitsi)

**Fallback plan:** Daily.co integration documented and tested in development. Can be switched in ≤ 2 sprints if Agora is unsuitable for a specific enterprise client.

---

## ADR-006: Tap Payments over Stripe for Payments
**Date:** 2026-05-02 | **Status:** Accepted

**Context:** UAE and Saudi users expect local payment methods: mada (Saudi debit), KNET (Kuwait), Apple Pay (GCC-native), Benefit (Bahrain). Stripe supports mada but not KNET; Tap Payments supports all.

**Decision:** Tap Payments for consumer payments and therapist payouts.

**Consequences:**
- (+) Full GCC payment method coverage (mada, KNET, Benefit, Apple Pay)
- (+) UAE entity and banking relationships simplify onboarding
- (+) Webhook security comparable to Stripe (HMAC-SHA256)
- (-) Less developer-friendly documentation than Stripe
- (-) Smaller global ecosystem of integrations

**Risk mitigation:** Stripe documented as backup for UAE card payments if Tap integration is delayed beyond Sprint 4.

---

## ADR-007: Crisis Detection — Two-Layer Architecture
**Date:** 2026-05-02 | **Status:** Accepted

**Context:** Crisis detection must run on every message synchronously (not async). Claude classification alone adds ~800ms latency. False negatives are unacceptable (safety-critical). Arabic crisis expressions differ significantly from English.

**Decision:** Layer 1 = regex keyword matching (synchronous, <5ms). Layer 2 = Claude semantic classification (only when Layer 1 triggers, adds ~600ms in that branch only).

**Consequences:**
- (+) 95%+ of messages have <5ms overhead from crisis detection
- (+) Claude handles semantic ambiguity that regex cannot
- (+) Arabic and English keyword lists maintained separately
- (-) Layer 1 false positives (common phrases) trigger unnecessary Claude calls
- (-) Keyword lists require regular maintenance and cultural review

**Clinical advisor requirement:** All keyword lists must be reviewed by the clinical advisor before launch and quarterly thereafter.

---

## ADR-008: Render (MVP) → AWS Bahrain (v2) Hosting Strategy
**Date:** 2026-05-02 | **Status:** Accepted

**Context:** AWS ap-middle-east-1 (Bahrain) is the best GCC data residency option but has higher operational overhead than Render for a small team at MVP stage.

**Decision:** Render for MVP (simple, fast to deploy, managed PostgreSQL and Redis). Migrate to AWS Bahrain (ECS Fargate, RDS Multi-AZ, ElastiCache) at v2 when scale demands it.

**Consequences:**
- (+) Ship faster on Render; no AWS IAM/VPC setup overhead at MVP
- (+) Render managed DB with daily backups acceptable for beta users
- (-) Render Frankfurt is EU-hosted; technically acceptable for current UAE PDPL interpretation but not ideal
- (-) Migration at v2 requires non-trivial DevOps effort (estimated 30-day sprint)

**Trigger for migration:** 500+ DAU OR a corporate client requiring GCC data residency in contract.

---

## ADR-009: Encrypted Application-Layer PHI vs. Database Encryption Only
**Date:** 2026-05-02 | **Status:** Accepted

**Context:** PostgreSQL supports transparent data encryption (TDE) at the disk level. However, if an attacker gains DB access (e.g., via SQL injection), TDE does not protect data. Mental health data is particularly sensitive.

**Decision:** AES-256 encryption at the application layer for all PHI columns (ai_conversations.messages, mood_entries.note, session_notes.content, client_profiles.intake_data). Per-user key derivation from master key + user_id.

**Consequences:**
- (+) Compromised DB credentials do not expose plaintext PHI
- (+) Meets UAE PDPL requirement for "appropriate technical measures"
- (-) Cannot perform full-text search or index on encrypted columns
- (-) Key rotation is a manual operation (requires re-encryption script)
- (-) If master key is lost, all encrypted data is permanently unrecoverable

**Key management:** Master key in Render Secrets Manager / AWS Secrets Manager. Rotated annually or on suspected compromise. Key rotation procedure documented in SECURITY_SPEC.md.

---

## ADR-010: Monorepo vs. Microservices for Services
**Date:** 2026-05-02 | **Status:** Accepted

**Context:** PRD describes multiple services (Auth, Booking, Payment, AI, etc.) as separate containers. Team is 3 engineers. Microservices add operational overhead.

**Decision:** Single FastAPI application with service-layer separation (modules, not separate deployments). Services are Python modules that share the database connection. Deploy as one container.

**Consequences:**
- (+) Single deployment unit for MVP — simpler CI/CD, one Render web service
- (+) Service boundaries enforced at Python module level (easy to split later)
- (+) Shared database connection pool (better performance)
- (-) All services scale together (acceptable at MVP scale)
- (-) A bug in one service can affect all services (acceptable with proper testing)

**Future split trigger:** If AI service compute needs diverge (e.g., needs GPU), split `ai_service` into its own container first. The module boundary already exists.

---

## ADR-011: SSE (Server-Sent Events) for AI Streaming vs. WebSockets
**Date:** 2026-05-02 | **Status:** Accepted

**Context:** AI companion and booking agent responses should stream token-by-token for perceived performance. Both SSE and WebSocket can achieve this.

**Decision:** SSE for all AI streaming (companion chat, booking agent). WebSockets reserved for real-time bidirectional needs (in-session video chat text panel, therapist-client messaging).

**Consequences:**
- (+) SSE is simpler (unidirectional); reconnects automatically with `EventSource`
- (+) Works over standard HTTP/2 multiplexing
- (+) No WebSocket handshake overhead for AI responses
- (-) Cannot reuse SSE connection for sending messages (HTTP POST for each message)

---

## ADR-012: Append-Only Audit and Crisis Logs via DB-Level REVOKE
**Date:** 2026-05-02 | **Status:** Accepted

**Context:** Audit logs and crisis events must be tamper-evident. Application-level restrictions can be bypassed by a compromised developer or admin account with DB credentials.

**Decision:** After creating `audit_log` and `crisis_events` tables, execute `REVOKE UPDATE, DELETE ON [table] FROM app_user, app_admin`. These permissions are never granted back.

**Consequences:**
- (+) Even a compromised `app_user` DB role cannot delete audit records
- (+) Meets "tamper-evident" requirement for regulatory compliance
- (-) Correcting mistaken audit log entries requires a manual process (DBA + legal approval)
- (-) Schema changes to these tables require `app_admin` with DDL permissions (acceptable — schema changes are rare)

---

## ADR-013: i18n Architecture — next-intl with JSON Message Files
**Date:** 2026-05-02 | **Status:** Accepted

**Context:** Arabic RTL support must be correct from day one. Adding a new language (Hindi, Urdu) in v2 must require no code changes.

**Decision:** `next-intl` with `/messages/{locale}.json` files. `dir` attribute driven by locale. `Intl.DateTimeFormat` and `Intl.NumberFormat` for locale-aware formatting.

**Consequences:**
- (+) Adding a language = add a JSON file + locale config. Zero component changes.
- (+) RTL layout handled at CSS level (`[dir="rtl"]` selectors in Tailwind config)
- (+) Currency (AED) formatted via `Intl.NumberFormat` — no hardcoded currency strings
- (-) Large JSON files for all UI strings — managed with namespaces

---

## Open Decisions (Not Yet Resolved)

| # | Question | Options | Owner | Deadline |
|---|---|---|---|---|
| OD-001 | Legal entity jurisdiction | UAE DIFC / UAE Mainland / Saudi | Founder | Before Sprint 3 |
| OD-002 | Clinical advisor contract | Part-time clinician vs. advisory firm | Founder | Before Sprint 3 |
| OD-003 | DHA/SCFHS verification | Manual review vs. API integration | Lead | Sprint 4 |
| OD-004 | Tap Payments MCC code | Confirm telehealth MCC with Tap | Finance | Sprint 4 |
| OD-005 | Anthropic data processing agreement | Self-serve DPA vs. enterprise agreement | Legal | Sprint 2 |
| OD-006 | Agora regional compliance review | Internal vs. third-party audit | Lead | Before soft launch |
