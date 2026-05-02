# Sprint Plan — GCC Wellness Platform

**Scrum Master Reference:** All 52 stories (KAN-19 – KAN-70) refined, sized, and sequenced across 8 two-week sprints.

**Team capacity assumption:** 3 developers × 8 story points/sprint each = **24 pts/sprint base**.
Sprints 1-4 carry 24 pts (infra heavy). Sprints 5-8 carry 28 pts (parallel stream velocity increases).

**Fibonacci scale:** 1 | 2 | 3 | 5 | 8 (stories >8 pts are already broken into sub-stories at subtask level)

**Phase gates:**
- After Sprint 4 → internal beta milestone (booking + payments working end-to-end)
- After Sprint 6 → soft launch readiness (100 beta users)
- After Sprint 8 → Phase 2 B2B launch

---

## Story Point Summary by Epic

| Epic | Stories | Total Pts | Phase |
|---|---|---|---|
| KAN-1: Auth & Accounts | KAN-19, 20, 21 | 18 | 1 |
| KAN-2: Onboarding | KAN-22, 23, 24 | 14 | 1 |
| KAN-3: AI Companion | KAN-25, 26, 27 | 21 | 1 |
| KAN-4: Therapist Discovery | KAN-28, 29, 30 | 15 | 1 |
| KAN-5: Booking | KAN-31, 32, 33, 34 | 23 | 1 |
| KAN-6: Video Sessions | KAN-35, 36, 37 | 21 | 1 |
| KAN-7: Mood Tracking | KAN-38, 39, 40 | 11 | 1 |
| KAN-8: Content Library | KAN-41, 42, 43 | 15 | 1 |
| KAN-9: Payments | KAN-44, 45, 46 | 18 | 1 |
| KAN-10: Therapist Dashboard | KAN-54, 55 | 13 | 1 |
| KAN-11: B2B Corporate | KAN-47, 48, 49, 50, 51, 52, 53 | 29 | 2 |
| KAN-12: Admin Dashboard | KAN-56, 57 | 10 | 1 |
| KAN-13: Crisis Safety | KAN-58, 59, 60 | 16 | 1 |
| KAN-14: AI Services | KAN-61, 62, 63 | 21 | 1-2 |
| KAN-15: Notifications | KAN-64, 65, 66 | 13 | 1 |
| KAN-16: DevOps & Infra | KAN-67, 68, 69, 70 | 20 | 1 |
| **Total** | **52 stories** | **278 pts** | |

---

## Dependency Graph (Critical Path)

```
KAN-67 (Docker Dev Env)
  └─> KAN-19 (Auth)
        ├─> KAN-20 (2FA)
        ├─> KAN-21 (Account Deletion)
        ├─> KAN-22 (Anonymous Mood)
        │     └─> KAN-23 (Intake + Matching)
        │           └─> KAN-24 (Account Gate)
        ├─> KAN-25 (AI Companion) ─> KAN-26 (Crisis Detection) [NON-NEGOTIABLE before launch]
        │                         └─> KAN-27 (Conversation Encryption)
        ├─> KAN-28 (Therapist Browse)
        │     └─> KAN-29 (AI Matching)
        │           └─> KAN-30 (Credential Badge)
        ├─> KAN-32 (Calendar Booking) ─> KAN-31 (AI Booking Agent)
        │                             ├─> KAN-33 (Confirmations)
        │                             └─> KAN-34 (Recurring / Cancellation)
        ├─> KAN-35 (Agora Infra) ─> KAN-36 (Video UX) ─> KAN-37 (Recovery)
        ├─> KAN-44 (Tap Payments) ─> KAN-45 (Refunds) ─> KAN-46 (Therapist Payouts)
        ├─> KAN-54 (Therapist Availability) ─> KAN-55 (Client Dashboard)
        └─> KAN-56 (Therapist Verification) ─> KAN-57 (Audit Log)

KAN-61 (AI Abstraction Layer) [must precede all AI stories]
  ├─> KAN-25 (Companion)
  ├─> KAN-26 (Crisis)
  ├─> KAN-29 (Matching)
  ├─> KAN-62 (Booking Agent impl)
  └─> KAN-63 (Support Agent)

KAN-68 (CI/CD) ─> KAN-69 (Prod Deploy) ─> KAN-70 (Monitoring)
```

---

## Sprint 0 — Pre-Sprint Setup (Week 0, before development starts)

**Goal:** Environment and project scaffolding ready before Sprint 1 begins. No story points counted.

| Action | Owner | Done When |
|---|---|---|
| Provision Jira board, epics (KAN-1..18), invite team | Lead | Board accessible |
| Agree on branching strategy (feature branches → main) | Team | CONTRIBUTING.md committed |
| Create GitHub repo, enable branch protection on `main` | Lead | PR required to merge |
| Provision Render (FastAPI + PostgreSQL + Redis) staging environment | DevOps | `/health` returns 200 |
| Provision Vercel project (Next.js staging) | DevOps | Next.js default page loads |
| Create Cloudflare R2 bucket (staging) | DevOps | Bucket accessible via SDK |
| Obtain Anthropic API key (production account) | Lead | Key stored in Render secrets |
| Obtain Tap Payments sandbox credentials | Lead | Sandbox dashboard accessible |
| Obtain Agora App ID and App Certificate | Lead | SDK test call succeeds |
| Create `.env.example` with all required vars | Dev | File committed to repo |
| Sign up for SendGrid (email), Twilio (SMS), FCM (push) accounts | Lead | Credentials in secrets manager |
| Engage clinical advisor for AI prompt review | Lead | Advisor under NDA + contract |
| Set up PostHog + Sentry projects | DevOps | Both SDKs receive test events |

---

## Sprint 1 — Foundation (Weeks 1-2)

**Sprint Goal:** Local development environment working, database schema deployed, authentication complete, and CI/CD pipeline shipping to staging.

**Capacity:** 24 points

| Story | Title | Points | Dependencies | Labels |
|---|---|---|---|---|
| KAN-67 | Local Dev Environment (Docker) | 5 | None | devops, infra |
| KAN-68 | GitHub Actions CI/CD | 5 | KAN-67 | devops |
| KAN-19 | User Registration & Login | 8 | KAN-67 | backend, frontend |
| KAN-20 | Two-Factor Authentication (TOTP) | 3 | KAN-19 | backend, frontend |
| KAN-21 | Account Deletion & PDPL Compliance | 3 | KAN-19 | backend, compliance |
| **Total** | | **24** | | |

**Sprint 1 Definition of Done:**
- [ ] `docker-compose up` starts all 4 services and `/health` returns 200
- [ ] CI pipeline runs lint + unit tests + builds Docker image on every PR
- [ ] Staging deploy is automatic after merge to `main`
- [ ] User can register, log in, refresh token, and log out
- [ ] Therapist and admin accounts require TOTP before accessing any protected route
- [ ] Account deletion soft-deletes immediately and queues 30-day purge job
- [ ] All RBAC role guards pass their unit test suite

**Risk:** Agora and Tap Payments sandbox onboarding may take longer than expected. Begin those in parallel (not blocking Sprint 1).

---

## Sprint 2 — Database, Onboarding & Therapist Discovery (Weeks 3-4)

**Sprint Goal:** Database migrations complete for all core entities, anonymous user can complete the onboarding funnel, and therapist profiles are browsable with credential badges.

**Capacity:** 24 points

| Story | Title | Points | Dependencies | Labels |
|---|---|---|---|---|
| KAN-61 | AI Abstraction Layer | 8 | KAN-19 | ai-engineer, backend |
| KAN-22 | Anonymous Mood Check-In | 3 | KAN-67 | backend, frontend |
| KAN-23 | 5-Question Intake & AI Matching | 5 | KAN-61, KAN-22 | ai-engineer, backend, frontend |
| KAN-24 | Account Creation Gate | 3 | KAN-23, KAN-19 | backend, frontend |
| KAN-28 | Therapist Profile Browser | 5 | KAN-19 | backend, frontend |
| **Total** | | **24** | | |

**Sprint 2 Definition of Done:**
- [ ] AI abstraction layer switches provider via `AI_PROVIDER` env var with zero code changes
- [ ] Anonymous user can complete mood check-in in <60 seconds with no login
- [ ] Intake form submits 5 questions, receives top 3 therapist recommendations with rationale
- [ ] Clicking "Book" while anonymous opens registration modal without losing intake state
- [ ] Therapist listing returns only `status=active` therapists with at least one available slot
- [ ] Filters work for language, specialization, price range, gender, availability date
- [ ] Pending and suspended therapists are invisible to users in all listing endpoints

---

## Sprint 3 — AI Companion, Crisis Detection & Therapist Matching (Weeks 5-6)

**Sprint Goal:** AI companion is live with crisis detection active. Therapist matching engine complete. These are prerequisites for beta launch.

**Capacity:** 24 points

> **Non-negotiable:** KAN-26 (Crisis Detection) and KAN-58-60 (Crisis pipeline) must be complete before any real users are onboarded.

| Story | Title | Points | Dependencies | Labels |
|---|---|---|---|---|
| KAN-25 | Bilingual AI Companion Chat | 8 | KAN-61 | ai-engineer, backend, frontend |
| KAN-26 | Crisis Detection & Escalation | 8 | KAN-61, KAN-25 | ai-engineer, backend, frontend |
| KAN-29 | AI Therapist Matching Engine | 5 | KAN-61, KAN-23 | ai-engineer, backend |
| KAN-30 | Credential Verification Display | 2 | KAN-28 | backend, frontend |
| KAN-27 | Conversation Encryption & Access Control | 3 | KAN-25 | backend, architect |
| **Total** | | **26** | | |

> Sprint 3 carries 2 extra points; team has confirmed capacity.

**Sprint 3 Definition of Done:**
- [ ] AI companion responds in the same language as the user's message (Arabic or English)
- [ ] Streaming SSE delivers tokens progressively; response latency P95 <3s
- [ ] Crisis detection: Layer 1 regex runs <5ms; Layer 2 Claude runs only on keyword trigger
- [ ] High-risk detection replaces AI response with full-screen crisis overlay unconditionally
- [ ] Red-team suite passes: 0 missed high-risk classifications out of 100 synthetic scenarios
- [ ] Therapist matching returns top 3 with weighted scores and Claude-generated rationale
- [ ] Conversation messages stored as ciphertext (AES-256); plaintext never hits the DB
- [ ] `platform_admin` role receives 403 on all conversation-content endpoints

---

## Sprint 4 — Booking, Payments & Notifications (Weeks 7-8)

**Sprint Goal:** End-to-end booking flow works — user can find a therapist, book a session with AI agent or calendar UI, pay via Tap Payments, and receive all notifications.

**Capacity:** 24 points

| Story | Title | Points | Dependencies | Labels |
|---|---|---|---|---|
| KAN-31 | AI Booking Agent | 5 | KAN-61, KAN-32 | ai-engineer, backend, frontend |
| KAN-32 | Calendar UI Booking | 5 | KAN-19, KAN-28 | backend, frontend |
| KAN-44 | Tap Payments Integration | 8 | KAN-32 | backend, frontend |
| KAN-33 | Booking Confirmations & Reminders | 3 | KAN-32, KAN-64 | backend |
| KAN-34 | Recurring Bookings & Cancellation | 3 | KAN-32, KAN-44 | backend, frontend |
| **Total** | | **24** | | |

**Sprint 4 Definition of Done:**
- [ ] AI booking agent handles 15+ NL scenarios in Arabic and English; falls back to UI after 3 failed attempts
- [ ] Booking never committed without explicit user confirmation in agent flow
- [ ] Double-booking race condition test passes (concurrent requests; only one succeeds)
- [ ] Tap Payments sandbox: card, mada, Apple Pay, KNET all succeed; webhook HMAC verified
- [ ] Booking confirmation fires via email + SMS + push within 60 seconds
- [ ] ICS file validates in Google Calendar, Outlook, and Apple Calendar
- [ ] Cancellation refund engine correctly applies all 5 PRD policy scenarios
- [ ] 24h and 1h session reminders fire at correct times

**Internal Beta Gate (end of Sprint 4):** Invite 5 internal testers. Test full funnel: onboard → match → book → pay → receive reminder.

---

## Sprint 5 — Video Sessions, Mood Tracking & Content Library (Weeks 9-10)

**Sprint Goal:** Therapy sessions can be conducted end-to-end via Agora video. Mood tracking works. Content library is populated and browsable.

**Capacity:** 26 points

| Story | Title | Points | Dependencies | Labels |
|---|---|---|---|---|
| KAN-35 | Agora Session Infrastructure | 8 | KAN-19, KAN-32 | architect, backend |
| KAN-36 | Video Session UX | 5 | KAN-35 | frontend |
| KAN-37 | Connection Recovery & Compensation | 3 | KAN-35, KAN-44 | backend, frontend |
| KAN-38 | Daily Mood Check-In | 3 | KAN-19 | backend, frontend |
| KAN-39 | Mood History Chart | 3 | KAN-38 | backend, frontend |
| KAN-40 | Mood Sharing Consent | 2 | KAN-38 | backend, frontend |
| KAN-41 | Content Library | 2 | KAN-19 | backend, frontend |
| **Total** | | **26** | | |

**Sprint 5 Definition of Done:**
- [ ] Agora video sessions launch with unique UUID channel per booking; E2EE via insertable streams
- [ ] Both participants join at 720p minimum; therapist-controlled waiting room works
- [ ] 5-minute warning fires; therapist can extend session once by 15 minutes
- [ ] Connection drop triggers 2-minute auto-reconnect; interrupted session state and compensation logic work correctly
- [ ] Mood check-in upserts one entry per user per day; note stored as AES-256 ciphertext
- [ ] Mood chart shows 30/90-day area chart with trend indicator
- [ ] Content library returns articles/audio/video with FTS working in Arabic and English

---

## Sprint 6 — Therapist Dashboard, Admin Tools & Crisis Logging (Weeks 11-12)

**Sprint Goal:** Therapists can manage their profiles and clients. Admins can verify therapists and view audit logs. Crisis pipeline is complete with logging and access control.

**Capacity:** 28 points

| Story | Title | Points | Dependencies | Labels |
|---|---|---|---|---|
| KAN-54 | Therapist Availability Management | 5 | KAN-19, KAN-32 | backend, frontend |
| KAN-55 | Client Dashboard & Secure Messaging | 8 | KAN-54, KAN-35 | backend, frontend |
| KAN-56 | Therapist Verification Workflow | 5 | KAN-19 | backend, frontend |
| KAN-57 | Audit Log & Compliance Reports | 5 | KAN-19 | backend, frontend |
| KAN-58 | Crisis Detection Pipeline (Perf) | 3 | KAN-26 | ai-engineer, backend |
| KAN-59 | Crisis Response Actions | 2 | KAN-58 | backend, frontend |
| **Total** | | **28** | | |

**Sprint 6 Definition of Done:**
- [ ] Therapist can set recurring weekly availability; double-booking returns 409; 15-min buffer enforced
- [ ] Therapist client dashboard shows intake summary, session history, and private notes (auto-save every 30s)
- [ ] Secure messaging scoped to client-therapist pair; no cross-pair access
- [ ] Admin can approve/reject therapist applications; every action written to audit log
- [ ] `audit_log` table has DB-level `REVOKE UPDATE, DELETE` permissions
- [ ] Crisis detection unit test suite: 200+ labeled phrases (AR+EN), all correct Layer 1 outcomes

**Soft Launch Gate (end of Sprint 6):** Security scan (OWASP ZAP), clinical advisor prompt sign-off, penetration test scope defined. Onboard 100 beta users.

---

## Sprint 7 — B2B Corporate Portal, SSO & Therapist Payouts (Weeks 13-14)

**Sprint Goal:** Corporate clients can be onboarded, employees can join via SSO, utilization reports are generated, and therapists can request payouts.

**Capacity:** 28 points

| Story | Title | Points | Dependencies | Labels |
|---|---|---|---|---|
| KAN-45 | Refunds & Platform Credits | 5 | KAN-44 | backend |
| KAN-46 | Therapist Earnings & Payouts | 5 | KAN-44 | backend, frontend |
| KAN-47 | Corporate Account Management | 5 | KAN-19 | backend, frontend |
| KAN-48 | Credit Pool Management | 3 | KAN-47 | backend, frontend |
| KAN-49 | Corporate Employee Onboarding | 3 | KAN-47 | backend, frontend |
| KAN-50 | Google Workspace SSO | 3 | KAN-47 | backend |
| KAN-51 | SAML 2.0 Azure AD SSO | 5 | KAN-47 | backend |
| **Total** | | **29** | | |

> Sprint 7 carries 1 extra point; SAML implementation is complex, team has 1 sprint-over capacity buffer.

**Sprint 7 Definition of Done:**
- [ ] Refund engine auto-applies all 5 PRD cancellation policy scenarios correctly
- [ ] Therapist earnings shows 70/30 split; payout request enforces AED 100 minimum balance
- [ ] Corporate admin can create company, upload employee CSV, add/remove employees
- [ ] Credit deduction is atomic; concurrent booking test with last credit succeeds for only one
- [ ] Employee joins via email domain auto-detection or company code
- [ ] Google Workspace OAuth2 SSO: personal gmail.com blocked; corporate domain accepted
- [ ] SAML 2.0 ACS endpoint validates signature, expiry, and audience against mock IdP

---

## Sprint 8 — Reporting, AI Support Agent, Notifications, Monitoring & Launch Polish (Weeks 15-16)

**Sprint Goal:** All remaining B2B features complete, AI support agent live, full notification system active, monitoring configured, and platform production-ready.

**Capacity:** 28 points

| Story | Title | Points | Dependencies | Labels |
|---|---|---|---|---|
| KAN-52 | Anonymized HR Utilization Reports | 5 | KAN-47, KAN-48 | backend, frontend |
| KAN-53 | Automated Quarterly Reports | 3 | KAN-52 | backend |
| KAN-42 | Personalized Content Recommendations | 3 | KAN-41, KAN-38 | backend |
| KAN-43 | Admin Content CMS | 3 | KAN-41 | backend, frontend |
| KAN-60 | Crisis Event Logging & Access Control | 3 | KAN-58, KAN-59 | backend |
| KAN-62 | AI Booking Agent (Full Impl) | 3 | KAN-31, KAN-61 | ai-engineer |
| KAN-63 | AI Customer Support Agent | 5 | KAN-61 | ai-engineer, backend, frontend |
| KAN-64 | Email & SMS Notifications | 3 | KAN-33 | backend |
| KAN-65 | Push Notifications (FCM) | 3 | KAN-64 | backend, frontend |
| KAN-66 | Calendar Export (ICS + Google) | 2 | KAN-33 | backend, frontend |
| KAN-69 | Production Deployment | 2 | KAN-68 | devops |
| KAN-70 | Monitoring & Alerting | 3 | KAN-69 | devops |
| **Total** | | **38** | | |

> Sprint 8 is heavy; team may carry 2-3 lowest-priority stories (KAN-53, KAN-66, KAN-42) into a hardening sprint if needed.

**Sprint 8 Definition of Done:**
- [ ] Utilization reports suppress departments with <5 employees into "Other"
- [ ] No user_id, name, or session content appears in any HR report endpoint response
- [ ] AI support agent answers 20+ predefined support scenarios; confidence <0.7 triggers human handoff
- [ ] Support ticket created on handoff contains no PHI
- [ ] Notification preferences respected: opted-out channels never receive messages
- [ ] k6 load test: 500 concurrent users, P99 <500ms, error rate <1%
- [ ] PagerDuty alert fires if crisis service is down >2 minutes
- [ ] Production Vercel + Render + R2 deployment is live and healthy

---

## Hardening Sprint (Buffer — Weeks 17-18 if needed)

**Goal:** Address any carry-over stories, run full regression suite, pen test remediation, and clinical advisor final sign-off.

| Buffer | Action |
|---|---|
| Carry-over | Any stories not completed in Sprint 8 |
| Security | OWASP ZAP full scan + penetration test remediation |
| Clinical | Clinical advisor final prompt review (companion + crisis) |
| Load testing | Agora: 50 concurrent video sessions from GCC network locations |
| Documentation | Update ARCHITECTURE.md and API_SPEC.md with any changes from implementation |
| Compliance | UAE PDPL Article 29 deletion test + PHI leak scan in CI |

---

## Velocity & Capacity Reference

| Sprint | Weeks | Planned Pts | Notes |
|---|---|---|---|
| Sprint 0 | Pre-sprint | 0 (setup) | Environment provisioning |
| Sprint 1 | 1-2 | 24 | Foundation |
| Sprint 2 | 3-4 | 24 | Onboarding + Discovery |
| Sprint 3 | 5-6 | 26 | AI Companion + Crisis |
| Sprint 4 | 7-8 | 24 | Booking + Payments |
| Sprint 5 | 9-10 | 26 | Video + Mood + Content |
| Sprint 6 | 11-12 | 28 | Therapist + Admin + Crisis Logging |
| Sprint 7 | 13-14 | 29 | B2B Corporate + Payouts |
| Sprint 8 | 15-16 | 38 | Reporting + Agents + Launch |
| **Total** | 16 weeks | **219 pts core** | Remaining in hardening |

> Note: Sprint 8 is intentionally loaded. If velocity suggests 28 pts max, move KAN-53 (Quarterly Reports), KAN-66 (ICS), and KAN-42 (Recommendations) to the hardening sprint — none are launch blockers.

---

## Story Refinement Notes (Scrum Master Review)

### Stories that required sizing adjustment

| Story | Original Risk | Refinement Action |
|---|---|---|
| KAN-25 (AI Companion) | Could be 13 pts (full feature) | Split: backend streaming endpoint + frontend chat UI + system prompt kept as subtasks within 8-pt story; frontend subtask is self-contained |
| KAN-26 (Crisis Detection) | Non-negotiable; complex 2-layer pipeline | Kept at 8 pts; KAN-58 (performance refinement) is a separate 3-pt story in Sprint 6 after the core is live |
| KAN-35 (Agora Infra) | External SDK risk | 8 pts; architect subtask required before backend implementation starts |
| KAN-44 (Tap Payments) | External SDK + webhook | 8 pts; sandbox integration begins in Sprint 0 to de-risk |
| KAN-51 (SAML 2.0) | SAML complexity often underestimated | Bumped from 3 to 5 pts; mock IdP required for testing |
| KAN-55 (Client Dashboard) | WebSocket + notes + messaging | 8 pts; most complex therapist-facing story |
| KAN-61 (AI Abstraction) | Foundation for all AI stories | Moved to Sprint 2, week 1 — must complete before any AI story starts |

### Stories safe to parallelize in the same sprint

- KAN-38/39/40 (Mood) can be split across backend and frontend engineers simultaneously
- KAN-41 (Content Library) is read-heavy; frontend can build off stub data while backend finalizes FTS
- KAN-64/65/66 (Notifications) are all wired to the same `NotificationService`; build in order

### Launch blockers (P0 — cannot launch without these)

1. KAN-26 + KAN-58 + KAN-59 — Crisis detection must be live and passing red-team tests
2. KAN-35 + KAN-36 — Video sessions must work reliably in GCC network conditions
3. KAN-44 — Payments must process successfully in Tap Production environment
4. KAN-19 + KAN-20 — Auth with mandatory 2FA for therapists
5. KAN-56 + KAN-57 — Therapist verification and audit log for compliance
6. KAN-27 — Conversation encryption (PHI protection)
