# GCC Wellness Platform — Architecture Reference

C4 Model diagrams covering all actors, containers, and key components of the GCC Wellness Platform. Use these as the authoritative architecture reference; the PRD section 4.1 diagram is a summary only.

---

## Level 1 — System Context

Shows the GCC Wellness Platform as a black box and all external actors and systems it interacts with.

```mermaid
C4Context
    title System Context — GCC Wellness Platform

    Person(b2c_user, "B2C User", "Individual seeking therapy or mental wellness support")
    Person(corp_employee, "Corporate Employee", "Employee accessing platform via employer benefit")
    Person(therapist, "Therapist", "Licensed mental health professional (DHA/SCFHS verified)")
    Person(hr_admin, "HR Admin", "Corporate HR manager monitoring team wellness")
    Person(platform_admin, "Platform Admin", "Internal GCC Wellness staff managing the platform")

    System(wellness_platform, "GCC Wellness Platform", "B2B2C mental health and therapy marketplace targeting UAE and Saudi Arabia. Supports Arabic/English, RTL, and GCC payment methods.")

    System_Ext(claude_api, "Anthropic Claude API", "Default LLM provider for AI companion, booking agent, matching, support, and crisis detection")
    System_Ext(openai_api, "OpenAI API", "Fallback LLM provider (GPT-4o) when Claude is unavailable")
    System_Ext(agora, "Agora RTC", "Encrypted real-time video and audio for therapy sessions")
    System_Ext(tap_payments, "Tap Payments", "Consumer payment processing and therapist payouts (GCC-native)")
    System_Ext(sendgrid, "SendGrid", "Transactional email delivery")
    System_Ext(twilio, "Twilio", "SMS notifications and OTP delivery")
    System_Ext(fcm, "Firebase FCM", "Mobile and web push notifications")
    System_Ext(google_cal, "Google Calendar API", "Therapist and user calendar sync")
    System_Ext(ms_graph, "Microsoft Graph", "Outlook calendar sync for corporate users")
    System_Ext(r2, "Cloudflare R2", "Object storage for media, license documents, and profile images")
    System_Ext(posthog, "PostHog", "Product analytics and feature flags")
    System_Ext(sentry, "Sentry", "Error tracking and performance monitoring")

    Rel(b2c_user, wellness_platform, "Books sessions, chats with AI companion, tracks mood, consumes content")
    Rel(corp_employee, wellness_platform, "Accesses platform via SSO, books sessions, views corporate benefit")
    Rel(therapist, wellness_platform, "Manages availability, conducts sessions, views client notes")
    Rel(hr_admin, wellness_platform, "Views anonymised team wellness dashboard, manages seat allocation")
    Rel(platform_admin, wellness_platform, "Manages therapists, content, billing, and platform configuration")

    Rel(wellness_platform, claude_api, "LLM inference — companion, booking, matching, support, crisis")
    Rel(wellness_platform, openai_api, "LLM inference fallback")
    Rel(wellness_platform, agora, "Video session signalling and media relay")
    Rel(wellness_platform, tap_payments, "Payment processing and payouts")
    Rel(wellness_platform, sendgrid, "Email notifications and receipts")
    Rel(wellness_platform, twilio, "SMS alerts and OTP")
    Rel(wellness_platform, fcm, "Push notifications")
    Rel(wellness_platform, google_cal, "Calendar availability sync")
    Rel(wellness_platform, ms_graph, "Corporate calendar sync")
    Rel(wellness_platform, r2, "Media upload and retrieval")
    Rel(wellness_platform, posthog, "Event tracking and analytics")
    Rel(wellness_platform, sentry, "Error and performance telemetry")
```

---

## Level 2 — Container Diagram

Internal building blocks of the GCC Wellness Platform.

```mermaid
C4Container
    title Container Diagram — GCC Wellness Platform

    Person(b2c_user, "B2C User")
    Person(corp_employee, "Corporate Employee")
    Person(therapist, "Therapist")
    Person(hr_admin, "HR Admin")
    Person(platform_admin, "Platform Admin")

    System_Boundary(wellness_platform, "GCC Wellness Platform") {
        Container(web_client, "Web Client", "Next.js 14 PWA, Tailwind CSS, next-intl", "Server-rendered PWA. Arabic/English, RTL from day one. Offline-capable for content.")
        Container(api_gateway, "API Gateway / BFF", "FastAPI", "Single HTTPS entry point. Request routing, rate limiting, auth token validation, response shaping.")
        Container(auth_service, "Auth Service", "FastAPI, python-jose, JWT, OAuth2, SAML 2.0", "User authentication, session management, RBAC, corporate SSO (SAML for B2B).")
        Container(booking_service, "Booking Service", "FastAPI, SQLAlchemy, APScheduler", "Therapist availability management, session scheduling, calendar sync, reminder triggers.")
        Container(payment_service, "Payment Service", "FastAPI, Tap Payments SDK", "Consumer checkout, subscription billing, therapist payout calculation and transfer.")
        Container(ai_service, "AI Service", "FastAPI, AI Abstraction Layer", "Companion chat, booking agent, therapist matching, customer support. Routes to correct agent and LLM adapter.")
        Container(crisis_service, "Crisis Detection Service", "FastAPI, keyword engine, Claude API", "Real-time risk classification on all chat messages. Tiered escalation: low / medium / high / immediate.")
        Container(notification_service, "Notification Service", "FastAPI, SendGrid, Twilio, FCM", "Unified notification dispatch. Handles email, SMS, and push based on user channel preferences.")
        Container(content_service, "Content Service", "FastAPI, SQLAlchemy", "Article, audio, and video CMS. Supports Arabic and English content with tag-based recommendations.")
        Container(realtime_gateway, "Real-Time Gateway", "FastAPI WebSockets", "Persistent connections for live chat, AI streaming responses, and in-session status events.")
        ContainerDb(primary_db, "Primary Database", "PostgreSQL 16", "All persistent application data: users, sessions, bookings, payments, content, audit logs.")
        ContainerDb(cache, "Cache", "Redis 7", "Session tokens, rate limit counters, real-time presence state, AI response caching.")
        Container(object_storage, "Object Storage", "Cloudflare R2", "Profile images, therapist license documents, audio/video content files.")
    }

    System_Ext(claude_api, "Anthropic Claude API")
    System_Ext(openai_api, "OpenAI API")
    System_Ext(agora, "Agora RTC")
    System_Ext(tap_payments, "Tap Payments")
    System_Ext(sendgrid, "SendGrid")
    System_Ext(twilio, "Twilio")
    System_Ext(fcm, "Firebase FCM")
    System_Ext(google_cal, "Google Calendar API")
    System_Ext(ms_graph, "Microsoft Graph")

    Rel(b2c_user, web_client, "HTTPS / PWA")
    Rel(corp_employee, web_client, "HTTPS / SSO")
    Rel(therapist, web_client, "HTTPS")
    Rel(hr_admin, web_client, "HTTPS")
    Rel(platform_admin, web_client, "HTTPS")

    Rel(web_client, api_gateway, "REST / JSON over HTTPS")
    Rel(web_client, realtime_gateway, "WebSocket (WSS)")

    Rel(api_gateway, auth_service, "Validates JWT, delegates login/register")
    Rel(api_gateway, booking_service, "Session CRUD, availability queries")
    Rel(api_gateway, payment_service, "Checkout, subscription, payout")
    Rel(api_gateway, ai_service, "Companion, matching, support requests")
    Rel(api_gateway, content_service, "Article and media retrieval")
    Rel(api_gateway, notification_service, "Manual notification triggers")

    Rel(realtime_gateway, ai_service, "Streams AI responses to client")
    Rel(realtime_gateway, crisis_service, "Every chat message inspected in real time")

    Rel(booking_service, notification_service, "Triggers booking confirmations and reminders")
    Rel(payment_service, notification_service, "Triggers payment receipts and payout alerts")
    Rel(booking_service, google_cal, "Availability and invite sync")
    Rel(booking_service, ms_graph, "Corporate Outlook sync")

    Rel(ai_service, claude_api, "LLM inference (default)")
    Rel(ai_service, openai_api, "LLM inference (fallback)")
    Rel(crisis_service, claude_api, "Semantic risk classification")
    Rel(crisis_service, notification_service, "Escalation alerts to therapist / admin")

    Rel(payment_service, tap_payments, "Payment processing and payouts")
    Rel(notification_service, sendgrid, "Email")
    Rel(notification_service, twilio, "SMS")
    Rel(notification_service, fcm, "Push")

    Rel(web_client, agora, "Video/audio RTC (peer-to-peer relay)")

    Rel(auth_service, primary_db, "Read/write")
    Rel(booking_service, primary_db, "Read/write")
    Rel(payment_service, primary_db, "Read/write")
    Rel(ai_service, primary_db, "Read conversation history")
    Rel(content_service, primary_db, "Read/write")
    Rel(crisis_service, primary_db, "Write risk events and escalation log")

    Rel(auth_service, cache, "Session tokens, rate limits")
    Rel(api_gateway, cache, "Rate limiting")
    Rel(realtime_gateway, cache, "Presence state")
    Rel(ai_service, cache, "Response caching")

    Rel(content_service, object_storage, "Audio/video retrieval")
    Rel(auth_service, object_storage, "Profile image and license doc storage")
```

---

## Level 3 — Component Diagram: AI Service

Zooms into the AI Service container showing individual agents, the abstraction layer, and LLM adapters.

```mermaid
C4Component
    title Component Diagram — AI Service

    Container_Boundary(ai_service, "AI Service") {
        Component(ai_router, "AI Router", "FastAPI router", "Inspects incoming requests and dispatches to the correct agent based on feature type (companion / booking / matching / support).")

        Component(ai_abstraction, "AI Abstraction Layer", "Python adapter pattern", "Unified generate() and chat() interface. Selects provider adapter at runtime via AI_PROVIDER env var. No code changes needed to swap LLMs.")

        Component(anthropic_adapter, "AnthropicAdapter", "anthropic Python SDK", "Default provider. Streams responses from Claude API. Handles prompt formatting, retry logic, and token budgeting.")
        Component(openai_adapter, "OpenAIAdapter", "openai Python SDK", "Fallback provider. Activated when Claude is unavailable or AI_PROVIDER=openai. API-compatible response normalisation.")
        Component(gemini_adapter, "GeminiAdapter", "google-generativeai SDK", "Future provider stub. Not active in MVP. Interface already defined for zero-friction addition in v2.")

        Component(companion_agent, "Companion Agent", "LangChain / direct Claude", "24/7 emotional support, reflective journaling prompts, psychoeducation. Maintains conversation history. Aware of user mood history.")
        Component(booking_agent, "Booking Agent", "Tool-calling LLM", "Natural language session booking. Queries therapist availability, confirms slots, creates bookings via Booking Service API. Handles rescheduling and cancellation.")
        Component(matching_agent, "Therapist Matching Agent", "Structured output LLM", "Analyses intake questionnaire responses and session history. Returns ranked therapist recommendations with rationale.")
        Component(support_agent, "Customer Support Agent", "RAG + LLM", "Handles FAQ, billing queries, and cancellation requests. Retrieves answers from knowledge base. Escalates complex cases to human support.")
        Component(crisis_detector, "Crisis Detector", "keyword engine + Claude", "Two-layer detection: (1) fast keyword/regex pass on every message, (2) Claude semantic classification on flagged messages. Returns tiered risk level: none / low / medium / high / immediate. Triggers escalation via Notification Service.")
    }

    System_Ext(claude_api, "Anthropic Claude API", "claude-sonnet-4-6 / claude-opus-4-6")
    System_Ext(openai_api, "OpenAI API", "GPT-4o")
    System_Ext(gemini_api, "Google Gemini API", "Future — not active in MVP")

    Container(realtime_gateway, "Real-Time Gateway", "FastAPI WebSockets")
    Container(api_gateway, "API Gateway / BFF", "FastAPI")
    Container(booking_service, "Booking Service", "FastAPI")
    Container(notification_service, "Notification Service", "FastAPI")
    ContainerDb(primary_db, "Primary Database", "PostgreSQL 16")
    ContainerDb(cache, "Cache", "Redis 7")

    Rel(api_gateway, ai_router, "Feature requests (matching, support, companion init)")
    Rel(realtime_gateway, ai_router, "Streaming chat messages (companion, booking)")
    Rel(realtime_gateway, crisis_detector, "Every inbound chat message")

    Rel(ai_router, companion_agent, "Companion chat requests")
    Rel(ai_router, booking_agent, "Booking-intent messages")
    Rel(ai_router, matching_agent, "Intake analysis requests")
    Rel(ai_router, support_agent, "Support queries")

    Rel(companion_agent, ai_abstraction, "chat()")
    Rel(booking_agent, ai_abstraction, "chat() with tool calls")
    Rel(matching_agent, ai_abstraction, "generate() structured output")
    Rel(support_agent, ai_abstraction, "chat() with RAG context")
    Rel(crisis_detector, ai_abstraction, "generate() semantic classification")

    Rel(ai_abstraction, anthropic_adapter, "Default route")
    Rel(ai_abstraction, openai_adapter, "Fallback route")
    Rel(ai_abstraction, gemini_adapter, "Future route")

    Rel(anthropic_adapter, claude_api, "HTTPS API calls")
    Rel(openai_adapter, openai_api, "HTTPS API calls")
    Rel(gemini_adapter, gemini_api, "HTTPS API calls")

    Rel(booking_agent, booking_service, "Availability queries and booking creation via internal API")
    Rel(crisis_detector, notification_service, "Escalation alerts — tiered severity")

    Rel(companion_agent, primary_db, "Read/write conversation history and mood entries")
    Rel(support_agent, primary_db, "Read knowledge base and billing records")
    Rel(matching_agent, primary_db, "Read therapist profiles and intake responses")
    Rel(crisis_detector, primary_db, "Write risk events and escalation log")

    Rel(ai_abstraction, cache, "Cache recent responses, token usage counters")
```

---

## Notes

### MVP vs v2 Infrastructure

| Concern | MVP (Months 1-7) | v2 (Month 8+) |
|---|---|---|
| Frontend hosting | Vercel | Vercel or AWS CloudFront |
| Backend hosting | Render (FastAPI containers) | AWS ECS / EKS, ap-middle-east-1 (Bahrain) |
| Database | Render PostgreSQL (managed) | AWS RDS Multi-AZ |
| Cache | Render Redis | AWS ElastiCache |
| Object storage | Cloudflare R2 | Cloudflare R2 (no change — cost-efficient) |
| AI provider | Claude API (primary), OpenAI (fallback) | Same — extend with Gemini adapter |
| Mobile | PWA only | React Native (iOS + Android) |
| Languages | Arabic (MSA + Gulf) + English | + Hindi + Urdu |
| Calendar sync | Google Calendar only | + Microsoft Graph (Outlook) for B2B |
| Therapist onboarding | Manual DHA/SCFHS verification | Semi-automated document verification |
| Crisis escalation | Keyword + Claude, alert to admin | Full MHFA-trained on-call integration |

### Key Architecture Constraints

- **Data residency:** All PostgreSQL data must remain in the GCC region. Use Render's Frankfurt region as interim; migrate to AWS Bahrain (ap-middle-east-1) in v2.
- **E2EE video:** Agora sessions are end-to-end encrypted. No recording by default. Any future recording feature requires explicit therapist and client consent with separate consent log.
- **AI provider swap:** The `AI_PROVIDER` environment variable controls which adapter is active. Valid values: `anthropic` (default), `openai`, `gemini`. No code deployment required to switch.
- **Crisis detection is non-negotiable:** The Crisis Detection Service must be live and passing all escalation tests before the platform opens to any real users.
- **RBAC roles:** `b2c_user`, `corporate_employee`, `therapist`, `hr_admin`, `platform_admin`. Enforced at API Gateway and validated in each service.
