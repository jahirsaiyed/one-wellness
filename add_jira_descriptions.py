#!/usr/bin/env python3
"""
Add scrum-style descriptions to all KAN issues (stories KAN-19..70 + subtasks KAN-71..381).

Each story gets:  User Story statement + Background + Acceptance Criteria
Each subtask gets: Description + Acceptance Criteria + Definition of Done
"""

import json
import os
import re
import sys
import time

import requests
from requests.auth import HTTPBasicAuth

JIRA_BASE_URL = "https://jsaiyed.atlassian.net"
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
PROJECT_KEY = "KAN"
DELAY = 0.15

if not JIRA_EMAIL or not JIRA_API_TOKEN:
    print("ERROR: Set JIRA_EMAIL and JIRA_API_TOKEN environment variables.")
    sys.exit(1)

AUTH = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# ADF helpers
# ---------------------------------------------------------------------------
def para(text: str) -> dict:
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]}


def strong_para(text: str) -> dict:
    return {"type": "paragraph", "content": [{"type": "text", "text": text, "marks": [{"type": "strong"}]}]}


def bullet_list(items: list[str]) -> dict:
    return {
        "type": "bulletList",
        "content": [
            {
                "type": "listItem",
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": item}]}],
            }
            for item in items
        ],
    }


def task_list(items: list[str]) -> dict:
    """Checkbox-style task list using ADF taskList."""
    return {
        "type": "taskList",
        "attrs": {"localId": "task-list"},
        "content": [
            {
                "type": "taskItem",
                "attrs": {"localId": str(i), "state": "TODO"},
                "content": [{"type": "text", "text": item}],
            }
            for i, item in enumerate(items)
        ],
    }


def make_doc(*nodes) -> dict:
    return {"type": "doc", "version": 1, "content": list(nodes)}


def story_doc(user_story: str, background: str, ac: list[str]) -> dict:
    return make_doc(
        strong_para("User Story"),
        para(user_story),
        strong_para("Background"),
        para(background),
        strong_para("Acceptance Criteria"),
        task_list(ac),
    )


def subtask_doc(description: str, ac: list[str]) -> dict:
    dod = [
        "Code reviewed by at least one team member",
        "Unit/integration tests written and passing in CI",
        "No new linting errors (Ruff / ESLint)",
        "Feature tested against both Arabic and English locales where applicable",
        "PR merged to feature branch",
    ]
    return make_doc(
        strong_para("Description"),
        para(description),
        strong_para("Acceptance Criteria"),
        task_list(ac),
        strong_para("Definition of Done"),
        task_list(dod),
    )


# ---------------------------------------------------------------------------
# Story descriptions  (KAN-19 .. KAN-70)
# ---------------------------------------------------------------------------
STORY_DESCRIPTIONS = {
    "KAN-19": story_doc(
        "As a new user, I want to register with email or Google SSO and log in securely, so that I can access the wellness platform and book sessions.",
        "Core authentication flows for all roles. Covers email/password registration, Google OAuth2, JWT lifecycle management, refresh token rotation, and RBAC guards protecting every protected route.",
        [
            "User can register with a valid email and password; password hashed with bcrypt",
            "User can log in with Google OAuth2 and is upserted into the users table",
            "JWT access token expires in 15 minutes; refresh token expires in 30 days",
            "Each refresh token use rotates the token (old token invalidated immediately)",
            "RBAC Depends guards enforce role restrictions on all protected routes",
            "Registration and login forms are RTL-compatible and bilingual (AR/EN)",
            "Forgot password flow sends a reset link and invalidates existing sessions",
            "Tokens stored in httpOnly cookies; 401 triggers silent auto-refresh",
            "Protected route guard redirects unauthenticated users to login",
        ],
    ),
    "KAN-20": story_doc(
        "As a therapist or admin, I want to secure my account with TOTP two-factor authentication, so that patient data and admin functions remain protected even if my password is compromised.",
        "TOTP 2FA is mandatory for therapist and platform_admin roles. Clients may optionally enable it. The flow covers secret generation, QR code provisioning, TOTP verification at login, and backup code recovery.",
        [
            "TOTP setup endpoint generates a secret and returns a QR code URI for authenticator apps",
            "TOTP verify endpoint validates a 6-digit code with clock-skew tolerance of +/- 30s",
            "Therapist and admin routes return 403 if 2FA is not yet confirmed in the session",
            "Backup codes are generated at setup (8 single-use codes) and stored hashed",
            "TOTP setup screen shows QR code, backup codes, and a confirm-activation step",
            "TOTP verification screen appears between password and session issuance steps",
            "E2E: therapist who skips TOTP is blocked from reaching the dashboard",
        ],
    ),
    "KAN-21": story_doc(
        "As a user, I want to permanently delete my account and all personal health data, so that my privacy is protected and the platform complies with Saudi PDPL and UAE data protection laws.",
        "Implements a two-stage deletion: immediate soft-delete hides the account, followed by an async hard-delete job that purges health data within 30 days. Billing records are anonymized (not deleted) for financial compliance.",
        [
            "POST /users/me/delete-request sets deleted_at and immediately revokes all active tokens",
            "Soft-deleted accounts cannot log in and are excluded from all queries",
            "Async job purges ai_conversations, mood_entries, and session notes within 30 days",
            "Billing records are anonymized: name and email fields nullified, amounts retained",
            "User receives a confirmation email when deletion request is received",
            "User receives a second email when hard deletion is complete",
            "Hard-delete job is idempotent and logs completion to the audit log",
            "Compliance test: simulate 30-day window and verify all health data is absent",
        ],
    ),
    "KAN-22": story_doc(
        "As a visitor, I want to log a quick mood check-in without creating an account, so that I can experience the platform's value before committing to registration.",
        "Anonymous mood entry is the primary no-friction entry point. Rate-limited per IP to prevent abuse. No PII required. Session-scoped so entries are not linked across users.",
        [
            "POST /mood/anonymous accepts score (1-10) and optional text; no authentication required",
            "Rate limiting: maximum 5 anonymous check-ins per IP address per hour",
            "Each anonymous session is isolated; entries are not linkable across sessions",
            "Landing page hero section prominently features the mood check-in widget",
            "Mood widget completes in under 60 seconds (minimal UI, no registration prompts)",
            "After submission, user sees a gentle prompt to create an account to track progress",
            "No personal data is stored with the anonymous entry",
        ],
    ),
    "KAN-23": story_doc(
        "As a new user, I want to answer 5 intake questions and receive AI-matched therapist recommendations, so that I can quickly find the right therapist without manually browsing through all profiles.",
        "The intake form is the primary onboarding funnel. It feeds the AI matching engine which uses embedding similarity and Claude reranking to return the top 3 therapists most suited to the user's needs, language, and availability.",
        [
            "5-step intake form captures: presenting concerns, preferred language, session preference, availability, and budget",
            "Form has animated progress bar and bilingual labels (AR/EN); fully RTL-compatible",
            "POST /intake stores answers session-scoped and returns an intake_id",
            "POST /intake/{id}/match calls AI matching and returns top 3 therapists with match scores and rationale",
            "AI matching uses embedding cosine similarity on specialization + Claude reranking",
            "Top result is always language-matched to the user's stated preference",
            "Recommendation cards show photo, specializations, price, rating, and two CTAs",
            "Intake data persists through account creation so the flow is not restarted",
        ],
    ),
    "KAN-24": story_doc(
        "As an anonymous user who has completed the intake, I want to create an account and proceed to booking without restarting my journey, so that registration feels seamless rather than disruptive.",
        "When an anonymous user clicks 'Book' on a recommendation card, they are prompted to register. The intake session is attached to the new account and the booking flow continues without restart.",
        [
            "Clicking 'Book' on a recommendation card triggers a registration modal (not a page redirect)",
            "Registration modal offers Google SSO as the primary option, with email as fallback",
            "POST /auth/register accepts optional intake_id to attach the anonymous intake",
            "After registration, the user is returned to the booking flow with therapist pre-selected",
            "If registration is abandoned, the intake data remains in session for up to 24 hours",
            "The intake_id is validated server-side before attachment to prevent injection",
        ],
    ),
    "KAN-25": story_doc(
        "As a user, I want to chat with an AI companion in Arabic or English, so that I can explore my feelings, get psychoeducation, and decide if I want to speak with a therapist.",
        "The AI companion is the core product engagement feature. It uses Claude via the abstraction layer with a culturally-aware GCC system prompt. Language is auto-detected per message and maintained. Anonymous users get 3 messages before the registration gate.",
        [
            "AI companion responds in the same language as the user's message (AR or EN)",
            "Arabic responses render RTL; English responses render LTR in the same chat UI",
            "Streaming SSE delivers tokens progressively with a blinking cursor",
            "System prompt enforces clinical boundaries: no diagnosis, no treatment recommendations",
            "Anonymous users see a gate after their 3rd message prompting account creation",
            "A 'Talk to a human' button is always visible and opens the therapist booking modal",
            "Chat history is persisted per session thread_id for authenticated users",
            "Auto-scroll keeps the latest message in view during streaming",
        ],
    ),
    "KAN-26": story_doc(
        "As a platform safety officer, I want every companion chat message to be screened for crisis signals in real time, so that users at risk are immediately connected with emergency resources and their therapist is alerted.",
        "Non-negotiable safety feature that ships before launch. Two-layer pipeline: fast regex keyword check (synchronous, <5ms) followed by Claude semantic classification when keywords trigger. High-risk responses override AI output unconditionally.",
        [
            "Every companion message passes through CrisisDetectionService before response is generated",
            "Layer 1 regex runs in under 5ms and covers Arabic and English crisis phrase patterns",
            "Layer 2 Claude classification produces structured JSON: risk_level, signals[], confidence",
            "High-risk: AI response is replaced entirely with crisis protocol (emergency numbers + helplines)",
            "High-risk overlay is full-screen, requires confirmation tap to dismiss, shows country-specific numbers",
            "Medium-risk shows a persistent sticky banner with emergency session booking CTA",
            "Crisis event is written to DB synchronously before response is returned to the user",
            "Therapist alert is queued and delivered within 5 minutes if client has an assigned therapist",
            "Red-team test suite: 100 synthetic scenarios, 0% missed high-risk, >= 98% accuracy",
        ],
    ),
    "KAN-27": story_doc(
        "As a user, I want my AI companion conversations to be encrypted and inaccessible to platform admins, so that I can speak freely knowing my privacy is protected.",
        "End-to-end encryption for conversation content with per-user AES-256 derived keys. Platform admins are explicitly denied access at the service layer, not just the UI. Conversations are retained for 3 years then purged.",
        [
            "Each user has a unique AES-256 key derived from their user_id and a platform secret",
            "Message JSONB column is encrypted before every DB write",
            "Decryption happens server-side on read, scoped strictly to the authenticated user",
            "platform_admin role receives 403 on any endpoint that returns conversation content",
            "Access control enforced at the service layer (not just route guards)",
            "Key rotation policy documented and rotation procedure tested in staging",
            "Conversations are hard-deleted after 3 years or on user deletion request",
            "DB audit: ciphertext is stored (not plaintext) — verified by DB inspection test",
        ],
    ),
    "KAN-28": story_doc(
        "As a user, I want to browse and filter verified therapist profiles, so that I can find a therapist who matches my language, specialization, and budget needs.",
        "Therapist listing is the manual alternative to AI matching. Paginated, filterable by multiple dimensions. Only active therapists with available slots are shown. Profile pages display full credentials including verified license badges.",
        [
            "GET /therapists returns paginated results with filters: language, specialization, price range, gender, availability date",
            "Only therapists with status=active and at least 1 future available slot are returned",
            "Therapists with status=pending or status=suspended are never shown to users",
            "Filter sidebar is collapsible and fully RTL-compatible",
            "Profile page shows bio, DHA/SCFHS/MOH credential badge, specializations, languages, price, and rating",
            "Calendar preview on profile shows next 5 available slots",
            "Filter combination unit tests cover all parameter combinations",
        ],
    ),
    "KAN-29": story_doc(
        "As a user, I want the platform to recommend the best-matched therapists based on my intake answers, so that I don't need to manually evaluate every therapist profile.",
        "AI-powered matching engine that translates intake answers into a ranked therapist recommendation using embedding similarity and Claude reranking. Users can always override and browse manually.",
        [
            "Matching uses weighted factors: specialization match 40%, language preference 30%, availability 20%, rating 10%",
            "Embeddings computed on therapist specialization descriptions and intake concern answers",
            "Cosine similarity produces a shortlist; Claude reranks with a human-readable rationale",
            "POST /matching/recommend returns top 3 therapists with match_score and rationale string",
            "Each recommendation card shows a 'Why this therapist?' tooltip with the rationale",
            "Override path: user can dismiss all recommendations and browse the full therapist directory",
            "Edge cases tested: no language-matched therapist, no available therapist, tie-breaking",
        ],
    ),
    "KAN-30": story_doc(
        "As a user, I want to see verified credential badges on therapist profiles, so that I can trust that the therapist holds a valid license from a recognized authority.",
        "License verification is performed manually by platform admins. The verification event is recorded and displayed as a badge on the therapist profile. Unverified therapists see a pending state in their own view.",
        [
            "Verified badge displays the license authority name (DHA, SCFHS, MOH, etc.) and verification date",
            "Badge is only shown when license_verified_at is populated for the therapist",
            "Therapist's own profile view shows 'Pending Verification' if not yet verified",
            "Verification event stores: license_authority, license_verified_at, verified_by_admin_id",
            "Audit log entry created for every verification action",
            "Clients cannot see unverified therapist profiles in any listing or search",
        ],
    ),
    "KAN-31": story_doc(
        "As a user, I want to book a therapy session by chatting with an AI agent in Arabic or English, so that I can schedule an appointment conversationally without navigating a calendar UI.",
        "The AI booking agent is a tool-calling Claude model with access to real-time availability data. It handles Arabic NLU for dates and times, confirms bookings explicitly with the user, and falls back to the calendar UI after 3 failed attempts.",
        [
            "Agent supports natural language booking requests in Arabic and English",
            "Arabic date/time phrases (e.g. Tuesday evening) are parsed to structured date/time objects",
            "Agent calls query_availability, create_booking, and confirm_booking tools using real DB data",
            "Booking is never committed without the user explicitly confirming",
            "After 3 failed or unclear attempts, agent offers the calendar UI as an alternative",
            "Booking confirmation summary card shows therapist, date, time, and price before final confirm",
            "Agent UI is visually distinct from the companion chat (different color scheme, focused layout)",
            "15+ NL scenario tests pass including: specific therapist by name, next available slot, evening-only preference",
        ],
    ),
    "KAN-32": story_doc(
        "As a user, I want to browse a therapist's availability calendar and book a slot, so that I have full control over selecting the exact session time.",
        "Calendar UI is the visual alternative to the AI booking agent. It shows available, booked, and blocked slots in the user's local timezone. Atomic DB-level locking prevents double-bookings.",
        [
            "Calendar weekly view shows available slots (green), booked slots (grey), and blocked slots (striped)",
            "All times are displayed in the user's detected timezone with the timezone abbreviation shown",
            "Timezone is auto-detected using browser Intl.DateTimeFormat and sent with the booking request",
            "POST /bookings uses a DB-level advisory lock to prevent concurrent double-bookings on the same slot",
            "Booking modal flow: select slot -> payment step -> confirmation page",
            "DST edge cases are handled correctly (clocks-forward and clocks-back dates)",
            "Race condition test: two concurrent requests for the last slot — only one succeeds",
        ],
    ),
    "KAN-33": story_doc(
        "As a user, I want to receive a booking confirmation via email, SMS, and push notification and be able to add the session to my calendar, so that I don't forget my appointment.",
        "Notification pipeline triggered on booking creation. All three channels (email, SMS, push) fire within 60 seconds. Reminder jobs scheduled for 24h and 1h before the session. ICS file generated for calendar integration.",
        [
            "SendGrid email, Twilio SMS, and FCM push all fire within 60 seconds of booking creation",
            "24-hour reminder sent via email + SMS + push; 1-hour reminder via push only",
            "Confirmation email includes: therapist name, date/time in user's timezone, session link",
            "GET /bookings/{id}/export.ics returns an RFC 5545 compliant ICS file",
            "Confirmation page includes Add to Calendar options: Google one-click, Outlook ICS download, Apple Calendar ICS download",
            "ICS file validates correctly in Google Calendar, Outlook, and Apple Calendar",
            "All reminder jobs are idempotent (no duplicate notifications if job retries)",
        ],
    ),
    "KAN-34": story_doc(
        "As a user, I want to set up recurring weekly sessions and cancel individual sessions according to the platform's cancellation policy, so that I can maintain a consistent therapy schedule with clear refund rules.",
        "Supports weekly recurrence rules. Individual sessions within a series can be cancelled without affecting future slots. The cancellation policy engine evaluates timing and determines refund eligibility automatically.",
        [
            "POST /bookings with recurrence_rule creates a series of weekly sessions up to the specified end date or count",
            "Each session in the series is a separate booking record linked by a recurrence_group_id",
            "Cancelling one session does not affect other sessions in the series",
            "Cancellation policy: >48h before session = full refund; 24-48h = 50% platform credit; <24h = no refund",
            "Cancellation flow shows the calculated refund amount before user confirms",
            "Confirmation modal is required to proceed with cancellation",
            "Boundary test: cancellation at exactly 48h falls into the >48h bucket",
            "Recurring booking toggle and end options are shown in the booking flow UI",
        ],
    ),
    "KAN-35": story_doc(
        "As a platform architect, I want a reliable Agora RTC infrastructure for video sessions with token-based authentication and E2EE, so that all therapy sessions are secure and each session has a unique isolated channel.",
        "Agora RTC integration for video sessions. Each session gets a unique UUID channel. Short-lived tokens are generated server-side. E2EE is implemented via WebRTC insertable streams. Session state machine tracks lifecycle.",
        [
            "Each booking generates a unique Agora channel ID (UUID) stored in the sessions table",
            "GET /sessions/{id}/agora-token generates a token expiring 2 hours from session start time",
            "Session state machine transitions: scheduled -> in_progress (first join) -> completed/interrupted/cancelled",
            "Both therapist and client must consent to recording before any recording starts; default is OFF",
            "Consent status stored in DB; recording cannot start without both consents recorded",
            "Token expiry test: token generated >2h before session start is rejected",
            "E2EE implemented via WebRTC insertable streams as per Agora documentation",
        ],
    ),
    "KAN-36": story_doc(
        "As a user or therapist, I want a smooth video session experience with a waiting room, in-session chat, time warnings, and the ability to extend the session, so that our therapy session runs professionally.",
        "Full video session UX built on Agora RTC SDK. Includes therapist-controlled waiting room, ephemeral in-session text chat, 5-minute end warning, and one-time session extension option for therapists.",
        [
            "Video renders at minimum 720p for both local and remote participants",
            "Client sees a waiting room screen until the therapist joins the Agora channel",
            "In-session text chat is delivered via WebSocket and is ephemeral (not persisted to DB)",
            "5-minute warning overlay appears automatically when session has 5 minutes remaining",
            "Therapist-only extension button adds 15 minutes; can only be used once per session",
            "Extension requires therapist confirmation before time is added",
            "Audio mute/unmute controls are accessible with a single tap",
            "E2E test covers: join as both roles, send chat message, verify warning fires, use extension",
        ],
    ),
    "KAN-37": story_doc(
        "As a user or therapist, I want dropped connections to be handled gracefully with auto-reconnect and appropriate compensation, so that technical issues do not result in a lost session without recourse.",
        "Connection recovery handles transient drops with an auto-retry UI. If both participants are absent for more than 5 minutes the session is marked interrupted. Compensation depends on when the interruption occurred.",
        [
            "Reconnection UI overlay appears immediately on connection drop with auto-retry for 2 minutes",
            "Session is marked 'interrupted' if both participants are absent for more than 5 consecutive minutes",
            "Interrupted before 10 minutes into the session: user receives a full credit refund automatically",
            "Interrupted after 10 minutes: user receives a priority rebooking offer (no refund)",
            "Interrupted session screen shows the appropriate message based on the timing",
            "Credit or rebooking notification is delivered within 5 minutes of the session being marked interrupted",
        ],
    ),
    "KAN-38": story_doc(
        "As a user, I want to log my mood daily on a scale of 1-10 with an optional note, so that I can track my emotional wellbeing over time and share trends with my therapist if I choose.",
        "Daily mood check-in with an idempotent upsert (one entry per user per day). Notes are encrypted at rest. FCM push reminder at user-configured time. Sharing with therapist requires explicit consent.",
        [
            "POST /mood-entries requires authentication and accepts score (1-10) and optional encrypted note",
            "One entry per user per calendar day; second submission on the same day updates the existing entry",
            "Note text is encrypted with AES-256 before writing to the DB column",
            "FCM push reminder fires at the user's configured daily reminder time",
            "Mood check-in widget completes in under 60 seconds",
            "Push notification permission request is shown as opt-in (never automatic)",
            "Time picker allows users to set their preferred daily reminder time",
            "DB verification: stored note column contains ciphertext, not plaintext",
        ],
    ),
    "KAN-39": story_doc(
        "As a user, I want to view a chart of my mood history over the past 30 or 90 days, so that I can identify patterns and progress in my emotional wellbeing.",
        "Mood history page with an area chart and an entry list. Data is scoped strictly to the authenticated user. 30-day and 90-day views available. Handles empty state gracefully.",
        [
            "GET /mood-entries?days=30 returns decrypted entries for the authenticated user only",
            "Area chart renders with 30-day and 90-day toggle options",
            "Trend indicator shows direction (improving / declining / stable) based on recent entries",
            "Entry list below chart shows date, emoji score, and expandable note",
            "Empty state displays a helpful message when no entries exist",
            "Data from other users is never returned (scoped by user_id in all queries)",
        ],
    ),
    "KAN-40": story_doc(
        "As a user, I want to control whether my therapist can see my mood tracking data, so that I decide what is shared and maintain full privacy by default.",
        "Mood sharing is explicitly opt-in and defaults to OFF. The toggle is in Privacy Settings. Therapists receive a 403 on any mood data request unless the specific client has granted consent. Revocation takes effect immediately.",
        [
            "PATCH /client-profiles/mood-sharing toggles therapist access for the authenticated user",
            "Default state is OFF (therapist cannot see mood data without explicit opt-in)",
            "GET /mood-entries/client/{client_id} returns 403 for therapists if consent is not granted",
            "Privacy Settings page shows a clearly labelled toggle for mood data sharing",
            "Therapist client dashboard mood chart section is only visible when consent=true",
            "Revoking consent takes effect immediately (next API call returns 403)",
            "Consent state change is logged in the audit log",
        ],
    ),
    "KAN-41": story_doc(
        "As a user, I want to browse, search, and filter mental wellness content in Arabic or English, so that I can access articles, meditations, and videos relevant to my needs.",
        "Content library with full-text search (PostgreSQL FTS for Arabic and English), filters, and an atomic view counter. Article reader and audio player with custom controls. Draft content is never shown to users.",
        [
            "GET /content supports filters: category, format (article/audio/video), language",
            "Full-text search works for both Arabic and English content using PostgreSQL FTS",
            "Draft and under-review content is never returned to non-admin users",
            "GET /content/{id} increments view_count using an atomic DB operation",
            "Content library card grid has a RTL-compatible collapsible filter sidebar",
            "Search bar uses debounce (300ms) to avoid excessive API calls",
            "Article reader shows estimated reading time",
            "Audio player has custom controls (play/pause/seek/volume) for meditation tracks",
            "Language toggle shows AR or EN content based on user's language preference",
        ],
    ),
    "KAN-42": story_doc(
        "As an authenticated user, I want to see content recommendations tailored to my intake answers and recent mood, so that the most relevant resources surface without me having to search.",
        "Personalization engine scores content based on overlap with the user's intake category and recent mood trend. Recommended section appears on the dashboard and content library. Push notifications for new relevant content are opt-in.",
        [
            "GET /content/recommended returns top 10 scored content items for the authenticated user",
            "Scoring weights: intake category overlap (primary), recent mood trend direction (secondary)",
            "Recommended section appears on the main dashboard and at the top of the content library",
            "Push notification for new relevant content is opt-in only (daily digest maximum)",
            "Users who opt out of content push notifications receive no content-related pushes",
            "Personalization unit tests use synthetic user profiles to verify scoring logic",
        ],
    ),
    "KAN-43": story_doc(
        "As a platform admin, I want to create, edit, and publish wellness content through a CMS, so that the content library stays fresh and all content is reviewed before users can see it.",
        "Admin CMS with a rich-text editor, media upload to Cloudflare R2, and a draft -> review -> published state machine. Only platform_admin can publish. Analytics available for published content.",
        [
            "POST /admin/content creates a new content item in draft state",
            "PATCH /admin/content/{id} updates any field; DELETE removes the item",
            "Status state machine: draft -> review -> published; only platform_admin can set status=published",
            "Draft and review content is not returned by GET /content (public endpoint)",
            "GET /admin/content/analytics returns views, avg_rating, and reads per category",
            "Admin content editor has rich-text body, category/language/format tag inputs, and R2 media upload",
            "Status workflow UI shows current status badge and transition buttons with confirmation dialogs",
        ],
    ),
    "KAN-44": story_doc(
        "As a user, I want to pay for therapy sessions securely using card, mada, Apple Pay, or KNET, so that I can complete the booking process with my preferred payment method.",
        "Payment integration via Tap Payments. No raw card data touches the backend (tokenization via Tap.js). Webhook signature verification protects against replay attacks. Corporate users deduct from their credit pool instead of paying directly.",
        [
            "POST /payments/initiate creates a Tap charge intent and returns the payment URL or hosted page",
            "POST /payments/webhook verifies HMAC signature before processing any event",
            "payment.paid event confirms the booking; payment.failed triggers an error flow",
            "Corporate users deduct from their session credit pool instead of paying via Tap",
            "Credit deduction is atomic to prevent overdraft in concurrent requests",
            "Checkout modal embeds Tap Payments UI supporting card, mada, Apple Pay, and KNET",
            "Tampered webhook payload with invalid signature returns 400 and logs an alert",
            "Tap sandbox tests cover: successful payment, 3DS flow, mada, Apple Pay, failure, timeout",
        ],
    ),
    "KAN-45": story_doc(
        "As a user, I want refunds to be processed automatically based on when I cancel, and I want to see my platform credit balance clearly so I can use it on future bookings.",
        "Automated refund engine evaluates the cancellation timing against the policy table and either calls the Tap refund API or issues platform credit. Therapist no-shows trigger a full refund plus a bonus credit. Credit ledger tracks balances.",
        [
            "Refund engine automatically applies the policy: >48h = full Tap refund, 24-48h = 50% platform credit, <24h = no refund",
            "Therapist no-show: full Tap refund + AED 50 platform credit issued within 15 minutes",
            "Platform credit ledger stores: user_id, amount, reason, expires_at",
            "Credit balance is visible in the user's account settings page",
            "Credits can be applied at checkout with a clear balance display",
            "Refund status page shows pending/processed status with timeline",
            "All 5 cancellation scenarios from the PRD policy table produce correct outcomes",
        ],
    ),
    "KAN-46": story_doc(
        "As a therapist, I want to track my earnings, request payouts, and download monthly statements, so that I have full visibility into my income from the platform.",
        "Therapist earnings dashboard with 70/30 revenue split. Payout requests require a minimum balance of AED 100. Monthly statements are generated as PDFs using WeasyPrint/ReportLab.",
        [
            "GET /therapist/earnings returns: sessions completed, pending payment, total earned, platform fee (30%), and net payout",
            "Revenue split is calculated as 70% therapist / 30% platform on every completed session",
            "POST /therapist/payout-requests enforces minimum AED 100 balance before allowing submission",
            "Payout form captures bank transfer details; status tracker shows pending/processing/paid",
            "Monthly earnings PDF includes a session breakdown table, platform fee line, and net total",
            "PDF contains only the requesting therapist's data (no other therapist data in any query)",
            "Download monthly statement button is accessible from the earnings dashboard",
        ],
    ),
    "KAN-47": story_doc(
        "As a platform admin, I want to create corporate accounts, upload employee lists, and manage employee access, so that B2B clients can provide wellness sessions as an employee benefit.",
        "Corporate account management for the B2B EAP offering. Platform admin creates companies; HR admins manage their employee roster. CSV upload for bulk onboarding with row-level validation feedback.",
        [
            "POST /admin/corporate-accounts creates a new company with name, allowed_domains, and initial credit balance",
            "POST /corporate/{id}/employees supports CSV upload (email list) and single manual add",
            "CSV upload returns a partial success report identifying invalid rows (missing email, bad domain)",
            "DELETE /corporate/{id}/employees/{user_id} removes access immediately (blocks future bookings from pool)",
            "Corporate admin portal shows company settings and a searchable employee roster table",
            "Employee add/remove actions are logged in the audit log with the HR admin's user_id",
            "Removed employees cannot deduct from the corporate credit pool on their next booking attempt",
        ],
    ),
    "KAN-48": story_doc(
        "As an HR admin, I want to monitor my company's session credit pool usage and receive alerts when credits are low, so that employees always have access to sessions.",
        "Credit pool management with atomic deduction on booking to prevent overdraft. Low-credit alert sent to HR admin when fewer than 10 credits remain. Dashboard shows total, used, and remaining credits.",
        [
            "GET /corporate/{id}/credits returns total, used, and remaining credit counts",
            "Credit deduction on booking uses a DB-level atomic transaction to prevent overdraft",
            "Concurrent booking test: two simultaneous requests for the last credit — only one succeeds",
            "Low-credit alert (email + FCM) sent to HR admin when remaining credits drop below 10",
            "Alert is not repeated until credits are topped up and drop below 10 again (debounced)",
            "Credit usage dashboard shows KPI cards and a utilization progress bar",
        ],
    ),
    "KAN-49": story_doc(
        "As a corporate employee, I want to join my employer's wellness program by entering a company code or having my email domain recognized automatically, so that I can access sessions at no personal cost.",
        "Corporate employee onboarding via email domain matching or a company code. On first verified login the employee's user_id is linked to the corporate account. Standard intake and therapist pool follows.",
        [
            "Email domain is automatically checked against corporate_accounts.allowed_domains on registration",
            "If domain is not matched, user can enter a company code as an alternative verification method",
            "Company code is validated server-side against corporate_accounts.company_code",
            "user_id is linked to the corporate account on first successful verification",
            "Corporate onboarding page has both domain auto-detection messaging and a company code input field",
            "After verification, user proceeds through the standard 5-question intake",
            "E2E: enter company code -> complete intake -> book session -> credit deducted from pool",
        ],
    ),
    "KAN-50": story_doc(
        "As a corporate employee, I want to sign in with my Google Workspace account, so that I can access the wellness platform without creating a separate password.",
        "Google Workspace OAuth2 SSO for corporate users. Only email domains registered to a corporate account are allowed (personal Google accounts are blocked). PKCE and state parameter for security.",
        [
            "GET /auth/sso/google/authorize redirects to Google with state parameter and PKCE code_challenge",
            "GET /auth/sso/google/callback exchanges code, validates state, and checks email domain",
            "If email domain is not registered, user sees an error screen with contact instructions",
            "Valid domain: employee user is upserted and a platform JWT is issued",
            "Personal Google accounts (@gmail.com without a corporate domain) are blocked",
            "Mock OAuth2 server tests cover: valid domain, invalid domain, state mismatch, expired code",
        ],
    ),
    "KAN-51": story_doc(
        "As a corporate IT admin, I want to configure SAML 2.0 SSO with Azure Active Directory, so that employees can authenticate using their existing corporate credentials.",
        "SAML 2.0 SP implementation for Azure AD integration. Supports SP metadata generation for easy IdP configuration. ACS endpoint validates assertions for signature, expiry, and audience.",
        [
            "GET /auth/sso/saml/metadata returns SP metadata XML for Azure AD app registration",
            "POST /auth/sso/saml/acs validates SAML assertion: signature, expiry, and audience",
            "Valid assertion: user is upserted and a platform JWT is issued",
            "IdP metadata XML is stored encrypted in corporate_accounts.sso_config",
            "Corporate admin SSO config page allows uploading IdP metadata XML and testing the connection",
            "Mock SAML IdP tests cover: valid assertion, expired assertion, invalid signature, wrong audience",
        ],
    ),
    "KAN-52": story_doc(
        "As an HR admin, I want to view anonymized utilization reports showing session usage by department, so that I can demonstrate ROI from the wellness benefit without exposing individual employee data.",
        "Anonymized utilization reporting with k-anonymity enforcement (minimum 5 employees per department group). Departments below the threshold are suppressed into an 'Other' bucket. No individual identity or session content in any report.",
        [
            "GET /corporate/{id}/reports/utilization returns sessions_used, sessions_remaining, and by-dept breakdown",
            "Departments with fewer than 5 employees are suppressed and merged into an 'Other' bucket",
            "Response body contains no user_ids, names, or session content",
            "KPI dashboard shows total used, remaining, and utilization percentage",
            "Monthly trend chart visualizes utilization over time",
            "PDF export generates the full report in a downloadable format",
            "QA test: department with 4 employees is suppressed; response has no user identifiers",
        ],
    ),
    "KAN-53": story_doc(
        "As an HR admin, I want to receive a quarterly utilization report automatically by email, so that I stay informed without having to log in and generate reports manually.",
        "Automated quarterly report generation with cron job. Report is emailed as a PDF attachment to the HR admin on schedule. Report history is accessible in the portal.",
        [
            "Cron job generates quarterly report on the first day of each quarter",
            "Report covers: sessions_used, sessions_remaining, dept utilization, and trend vs previous quarter",
            "SendGrid delivers the PDF report to the HR admin's registered email automatically",
            "Report history table in the portal lists past reports with generated_at and a download link",
            "PDF download link is a signed URL valid for 24 hours",
            "Report contains no PHI: no names, session notes, or individual identifiers",
        ],
    ),
    "KAN-54": story_doc(
        "As a therapist, I want to manage my weekly availability schedule, block specific dates, and know the platform will prevent double-bookings automatically, so that I can maintain a consistent and conflict-free calendar.",
        "Therapist availability management with recurring weekly slots, individual date blocking, 15-minute buffer enforcement, and double-booking prevention across both the AI booking agent and calendar UI.",
        [
            "POST /therapist/availability sets recurring weekly slots with day_of_week, start_time, and end_time",
            "PATCH /therapist/availability/{id}/block blocks a specific date or slot without affecting recurrence",
            "15-minute buffer is enforced: a slot ending at 11:00 means the next bookable slot is 11:15",
            "Double-booking prevention is enforced across both the AI booking agent and the calendar UI booking paths",
            "Availability calendar UI supports drag-to-create new slots and a block-day button",
            "All slot times display the local timezone abbreviation",
            "Slot times are stored in UTC in the DB and converted to local time on display",
            "Test: double-booking attempt returns 409 Conflict",
        ],
    ),
    "KAN-55": story_doc(
        "As a therapist, I want to view my clients' intake information, session history, write private notes, and message clients securely within the platform, so that I can provide continuity of care.",
        "Therapist client dashboard with intake summaries, session history, a private notes editor with auto-save, and in-platform messaging. Notes are strictly private (therapist-only access).",
        [
            "GET /therapist/clients returns a paginated list with each client's intake summary and last session date",
            "Session notes (POST/GET/PATCH) are accessible only to the therapist who wrote them",
            "GET /therapist/session-notes/{session_id} by any other role returns 403",
            "Notes editor auto-saves draft to the server every 30 seconds using PATCH",
            "Secure messaging uses a WebSocket room scoped to the client-therapist pair",
            "Client cannot access the messaging room of another therapist-client pair",
            "In-platform messaging is the only permitted communication channel (no external contact sharing)",
        ],
    ),
    "KAN-56": story_doc(
        "As a platform admin, I want to review therapist applications, verify credentials, and approve or reject applicants, so that only licensed professionals are listed on the platform.",
        "Admin verification workflow for therapist onboarding. Applications are reviewed with document viewing via signed R2 URLs. Every action is logged to the immutable audit log. Approval activates the account; rejection sends an email with reason.",
        [
            "GET /admin/therapist-applications lists applications with status filter (pending/approved/rejected/info_requested)",
            "Document viewer shows license files using short-lived R2 signed URLs",
            "PATCH /admin/therapist-applications/{id} accepts actions: approve, reject, request_info",
            "Approve action: sets therapist status=active and sends a welcome email",
            "Reject action: sends a rejection email with the reason and appeal instructions",
            "request_info action: sends an email asking for additional documents",
            "Every action is logged to audit_log with admin_id, action, therapist_id, and timestamp",
        ],
    ),
    "KAN-57": story_doc(
        "As a compliance officer, I want an immutable audit log of all significant platform actions and automated monthly compliance reports, so that we can demonstrate regulatory compliance.",
        "Append-only audit log enforced at the DB level. Filterable via admin UI. Monthly compliance report summarizes PHI access, crisis escalations, and account deletions. CSV export available.",
        [
            "GET /admin/audit-logs supports pagination and filters: actor_id, event_type, resource_type, date range",
            "audit_log table has REVOKE UPDATE, DELETE permissions at the DB level (enforced, not just application logic)",
            "Attempt to UPDATE or DELETE an audit_log row returns a DB-level permission error",
            "Monthly compliance report counts: PHI access events, crisis escalations, and account deletions",
            "Audit log viewer in admin UI has sortable columns, a filter panel, and CSV export",
            "Compliance report page shows summary tiles and a downloadable PDF",
            "CSV export integrity: all rows are present and no data truncation occurs",
        ],
    ),
    "KAN-58": story_doc(
        "As a platform safety engineer, I want a two-layer crisis detection pipeline that is fast, accurate, and runs on every companion message, so that no high-risk message goes undetected.",
        "Performance-optimized crisis detection with a synchronous regex layer (Layer 1) and Claude semantic classification (Layer 2). Layer 2 is only invoked when Layer 1 detects keywords, minimizing latency impact.",
        [
            "Layer 1 regex runs synchronously in under 5ms on every companion message",
            "Layer 1 covers Arabic and English crisis phrase patterns (maintained as a versioned list)",
            "Layer 1 triggers Layer 2 only when at least one keyword pattern matches",
            "Layer 2 Claude classification returns structured JSON: {risk_level, signals[], confidence}",
            "CrisisDetectionService is injected as a FastAPI dependency (no separate HTTP hop)",
            "Country detection maps user.timezone to the correct emergency numbers (UAE/KSA/Kuwait/Bahrain)",
            "Unit test suite: 200+ labeled phrases (AR+EN) all produce correct Layer 1 outcomes",
            "Integration test: Layer 2 is invoked if and only if Layer 1 triggers",
        ],
    ),
    "KAN-59": story_doc(
        "As a user in crisis, I want the platform to immediately show emergency resources and alert my therapist, so that I can get help as quickly as possible.",
        "Crisis response actions for high-risk and medium-risk classifications. High-risk overrides the AI response unconditionally. Therapist alert delivered within 5-minute SLA. UI designed so the user cannot accidentally dismiss the overlay.",
        [
            "High-risk: AI companion response is replaced entirely with the crisis protocol output",
            "Crisis protocol output shows country-specific emergency numbers, helplines, and a supportive message",
            "High-risk full-screen overlay requires an explicit confirmation tap to dismiss",
            "Medium-risk shows a persistent sticky banner above the chat with emergency booking CTA",
            "Therapist alert notification is created synchronously before the HTTP response is returned",
            "Therapist alert is delivered within 5 minutes via FCM/email (SLA monitored by Better Uptime)",
            "E2E test: send a high-risk phrase, verify overlay appears + crisis_events row created + therapist notification queued — all in one request cycle",
        ],
    ),
    "KAN-60": story_doc(
        "As a safety officer, I want crisis events to be logged with full context and retained for 7 years, so that we can meet our duty-of-care obligations and legal requirements.",
        "Crisis event logging with strict access control. Only the safety_officer sub-role can read crisis logs. Hard delete requires the safety_officer plus a legal approval workflow. 7-year retention enforced at the API level.",
        [
            "Every crisis detection (any risk level) creates a crisis_events row synchronously",
            "crisis_events schema: user_id, conversation_id, risk_level, trigger_signals (JSONB), platform_response, therapist_notified, therapist_notified_at, logged_at",
            "platform_admin role without safety_officer sub-role receives 403 on crisis log endpoints",
            "safety_officer sub-role is required to read or export crisis logs",
            "Soft delete is blocked on crisis_events rows",
            "Hard delete requires safety_officer role + a legal approval ticket reference",
            "7-year retention policy is documented and enforced at the API layer (reject hard delete without approval)",
        ],
    ),
    "KAN-61": story_doc(
        "As an AI engineer, I want all AI calls to go through a provider-agnostic abstraction layer, so that we can switch between Claude, GPT-4o, and future models by changing an environment variable without touching business logic.",
        "AIProvider abstract base class with AnthropicAdapter (primary) and OpenAIAdapter (fallback). Automatic fallback on 429 rate limits. Versioned prompt templates managed centrally. No PII in prompts.",
        [
            "AIProvider abstract base class defines: generate(prompt), chat(messages), embed(text) interface",
            "AnthropicAdapter implements the full interface with streaming, token counting, and system prompt injection",
            "OpenAIAdapter implements the same interface using GPT-4o",
            "AI_PROVIDER env var switches the active provider (anthropic | openai) without code changes",
            "Rate limit detector catches 429 from the primary provider and switches to the fallback transparently",
            "Prompt template manager stores versioned templates per feature; no hardcoded prompts in route handlers",
            "get_ai_provider() FastAPI dependency reads AI_PROVIDER and returns the correct adapter instance",
            "PHI safety: user UUIDs only in prompts — no names, emails, or other identifying information",
            "QA test: mock primary provider to return 429, verify fallback activates automatically",
        ],
    ),
    "KAN-62": story_doc(
        "As a user, I want to book therapy sessions through a conversational AI agent that understands Arabic and English date/time expressions, so that scheduling feels natural and effortless.",
        "AI booking agent implementation using the provider abstraction layer with tool-calling. Arabic NLU for dates and times. Confirmation required before committing any booking. Falls back to calendar UI after 3 failures.",
        [
            "Booking agent prompt defines tool schemas for query_availability, create_booking, and confirm_booking",
            "Arabic date/time phrases are parsed to structured objects: {day, time_pref, week, specific_date}",
            "Agent asks specific clarifying questions when intent is ambiguous (max 3 clarification turns)",
            "After 3 failed or unclear attempts, agent offers a link to the calendar UI",
            "Booking is never committed without the user's explicit confirmation in the final turn",
            "POST /booking-agent/chat handler executes tool calls against the real DB (not mocked data)",
            "Confirmation card shows therapist, date/time (in user's timezone), duration, and price",
            "15+ scenario tests cover: specific therapist, next available, evening-only, Arabic input, 3-attempt fallback",
        ],
    ),
    "KAN-63": story_doc(
        "As a user, I want to get instant answers to common questions about the platform from an AI support agent, and have my issue escalated to a human when the AI is not confident, so that support is fast and reliable.",
        "AI customer support agent with knowledge base grounding. Confidence threshold of 0.7 triggers human handoff. Support tickets are created on handoff with transcript summary (no PHI). Floating chat widget accessible from all pages.",
        [
            "Support agent is grounded on a knowledge base covering: FAQ, pricing, cancellation policy, therapist application process",
            "Agent correctly answers at least 20 predefined support scenarios",
            "Confidence score below 0.7 triggers human handoff without user intervention",
            "POST /support/tickets creates a support ticket on handoff with conversation transcript",
            "Support ticket summary contains no PHI (user_id reference only, no name or health data)",
            "Scope guardrails prevent the agent from giving clinical advice or recommending specific therapists",
            "Support chat widget is accessible from all pages, floats bottom-right, and is minimizable",
            "Human handoff trigger test: verify ticket is created correctly for low-confidence responses",
        ],
    ),
    "KAN-64": story_doc(
        "As a user, I want to receive timely email and SMS notifications for bookings and reminders, and have full control over which notification channels I subscribe to, so that I stay informed without being overwhelmed.",
        "Event-driven notification service with SendGrid (email) and Twilio (SMS). Provider-agnostic interface allows swapping to SES with env var. Per-user per-channel opt-out respected by all send functions.",
        [
            "SendGrid templates cover: booking confirmation, 24h reminder, 1h reminder, payout statement, welcome email",
            "Twilio SMS covers: 24h session reminder, OTP, crisis-related alerts to safety officer",
            "NotificationPreferences model stores per-user per-channel opt-out preferences",
            "All send functions check NotificationPreferences before dispatching (no notifications to opted-out channels)",
            "Notification preferences page has a toggle per channel (email/SMS/push) per event type",
            "No PHI in notification payloads: user_id reference used in subject line templates, not name",
            "Provider interface is abstracted: swap NOTIFICATION_EMAIL_PROVIDER=ses without code changes",
        ],
    ),
    "KAN-65": story_doc(
        "As a user, I want to receive push notifications for bookings, reminders, and content recommendations on my device, so that I stay engaged with the platform even when I'm not actively using it.",
        "Firebase FCM push notification integration. Device token registration endpoint. Push triggers for key events. In-app notification bell with unread count. Permission-denied users fall back to email.",
        [
            "POST /users/push-tokens registers a device token for the authenticated user",
            "Push triggers: booking confirmation, 1h reminder, new recommended content, medium/high crisis therapist alert",
            "send_multicast sends to all registered tokens for the user (multiple devices supported)",
            "PWA service worker registration prompts for push permission on first load",
            "In-app notification bell shows an unread count badge that increments on new notifications",
            "Clicking the bell opens a notification panel with the last 20 notifications",
            "Users who deny push permission fall back to email for all push-eligible events",
        ],
    ),
    "KAN-66": story_doc(
        "As a user, I want to add my booked therapy session to my calendar app with one click, so that I never miss an appointment.",
        "ICS file generation (RFC 5545) for universal calendar compatibility. Google Calendar OAuth2 one-click add. Outlook and Apple Calendar via ICS download.",
        [
            "GET /bookings/{id}/export.ics returns an RFC 5545 compliant ICS file",
            "ICS file validates and imports correctly in Google Calendar, Outlook, and Apple Calendar",
            "Google Calendar OAuth2 flow creates the event directly in the user's calendar without requiring ICS download",
            "Add to Calendar component shows three options: Google (OAuth), Outlook (ICS download), Apple (ICS download)",
            "ICS event includes: therapist name (display only), date/time in UTC, duration, and a session link",
            "Google Calendar OAuth access token is stored per user and refreshed automatically",
        ],
    ),
    "KAN-67": story_doc(
        "As a developer, I want a Docker-based local dev environment that starts all services with a single command, so that onboarding is fast and the dev environment matches production closely.",
        "Multi-stage Dockerfiles for FastAPI and Next.js. docker-compose.yml with postgres:16, redis:7, backend, and frontend. Fully documented .env.example with all required variables.",
        [
            "docker-compose up starts all 4 services: postgres:16, redis:7, backend (FastAPI), frontend (Next.js)",
            "All 4 services report healthy status within 60 seconds of docker-compose up",
            "GET /health on the backend returns 200 with service status",
            "Frontend home page is served correctly on localhost:3000",
            "FastAPI Dockerfile uses multi-stage build, non-root user, and a HEALTHCHECK instruction",
            "Next.js Dockerfile uses multi-stage build with output: standalone and a non-root user",
            ".env.example documents every required variable with a description and example value",
        ],
    ),
    "KAN-68": story_doc(
        "As a developer, I want a GitHub Actions CI/CD pipeline that lints, tests, and deploys automatically to staging with manual approval for production, so that we catch regressions early and deploy safely.",
        "CI/CD pipeline with lint + test + build stages. Automatic staging deploy with Cypress E2E. Production deploy requires manual approval via GitHub Environments. PHI leak scanning prevents accidental exposure.",
        [
            "Ruff linting and ESLint both pass in the lint stage before any tests run",
            "pytest unit tests and integration tests run in separate parallel jobs",
            "Docker image builds successfully for both backend and frontend",
            "Staging deploy triggers after all tests pass; Cypress E2E suite runs against staging after each deploy",
            "Production deploy job requires manual approval via GitHub Environments before executing",
            "validate-env.sh fails the pipeline if any required environment variable is unset",
            "check-phi-leaks.sh scans source and log output for email/phone/name patterns and fails CI on a match",
        ],
    ),
    "KAN-69": story_doc(
        "As a DevOps engineer, I want the platform deployed on Vercel (frontend), Render (backend + DB), and Cloudflare R2 (file storage), so that we have a cost-effective, scalable production environment from day one.",
        "Production deployment configuration for Vercel + Render + Cloudflare R2. Separate staging and production environments with independent env var sets. R2 signed URLs for private license document access.",
        [
            "vercel.json correctly configures the Next.js project with domain redirects and environment variables",
            "Render services: FastAPI web service (Docker), managed PostgreSQL 16, managed Redis 7 are all running",
            "Cloudflare R2 bucket is configured with CORS and signed URL generation for private assets",
            "Staging and production use completely separate env var sets in Render and Vercel dashboards",
            "Staging smoke test: /health, /auth/register, /therapists, and /content all return correct responses",
            "R2 signed URL access test: private license document is accessible via signed URL and rejected without it",
        ],
    ),
    "KAN-70": story_doc(
        "As a platform operator, I want comprehensive monitoring, alerting, and auto-scaling configured so that the platform is reliable, observable, and responsive to traffic spikes.",
        "Sentry for error tracking (PHI scrubbed), PostHog for anonymized product analytics, Better Uptime for availability monitoring, PagerDuty for P0 alerts, and Render auto-scaling triggered at >70% CPU.",
        [
            "Sentry captures errors from Next.js (client + server) and FastAPI; PHI fields scrubbed before send",
            "PostHog events are anonymized: session_booked, companion_message_sent, crisis_detected — no user PII in props",
            "Better Uptime monitors frontend, backend /health, and Agora webhook endpoint with 1-minute check interval",
            "PagerDuty alert fires if: any monitored service is down >2 minutes, or crisis detection service fails",
            "Render scale-out triggers when CPU exceeds 70% for 2 continuous minutes",
            "Instances pre-warmed 30 minutes before peak hours (6PM–9PM GST) to avoid cold-start latency",
            "k6 load test: 500 concurrent users booking sessions; P99 response time under 500ms; error rate below 1%",
        ],
    ),
}


# ---------------------------------------------------------------------------
# Subtask description generator
# ---------------------------------------------------------------------------
ROLE_CONTEXT = {
    "Architect": "system design, data model, and architectural decisions",
    "Backend": "FastAPI implementation, database queries, and API contract",
    "Frontend": "Next.js UI components, RTL layout, and user interaction",
    "AI Engineer": "prompt engineering, model integration, and AI pipeline logic",
    "QA": "test cases, acceptance criteria validation, and quality assurance",
}

ROLE_DOD = {
    "Architect": [
        "Architecture decision record (ADR) written and approved",
        "Design reviewed with backend and frontend leads",
        "Security implications documented",
        "Implementation guide available for the team",
    ],
    "Backend": [
        "Endpoint implemented and returns correct status codes",
        "Unit tests and integration tests written and passing",
        "Pydantic request/response models defined",
        "Database migrations applied and tested",
        "API contract matches the agreed spec",
    ],
    "Frontend": [
        "Component renders correctly in LTR and RTL modes",
        "Tested in Chrome, Firefox, and Safari",
        "Responsive on mobile (375px) and desktop (1440px)",
        "Accessibility: keyboard navigable, correct ARIA roles",
        "No TypeScript errors or ESLint warnings",
    ],
    "AI Engineer": [
        "Prompt tested against 20+ representative inputs",
        "Output format validated and consistent",
        "Edge cases handled (empty input, unexpected language, refusal cases)",
        "Token usage documented and within budget",
        "Fallback behavior defined for model errors",
    ],
    "QA": [
        "All test scenarios pass in CI",
        "Edge cases and boundary conditions covered",
        "Test report attached to the ticket",
        "Regression suite updated with new scenarios",
        "Security and privacy checks included",
    ],
}

DEFAULT_DOD = [
    "Code reviewed by at least one team member",
    "All tests passing in CI pipeline",
    "No new linting or type errors introduced",
    "Tested in both Arabic and English locales where applicable",
    "PR merged to feature branch",
]


def extract_role(summary: str) -> str:
    """Extract role prefix from task summary like '[Backend] ...'"""
    match = re.match(r"\[([^\]]+)\]", summary)
    return match.group(1).strip() if match else ""


def strip_role(summary: str) -> str:
    """Remove the [Role] prefix from summary."""
    return re.sub(r"^\[[^\]]+\]\s*", "", summary).strip()


def generate_subtask_description(summary: str) -> dict:
    role = extract_role(summary)
    clean = strip_role(summary)

    # Build a clear description sentence
    description = f"Implement: {clean}."

    # Generate acceptance criteria from the task content
    # Split on common delimiters to extract individual items
    parts = re.split(r"[,;]|\s+and\s+|\s+\+\s+", clean)
    parts = [p.strip(" .") for p in parts if len(p.strip()) > 10]

    ac = []
    for part in parts[:4]:  # up to 4 criteria
        ac.append(f"Completed: {part}")

    if not ac:
        ac = [f"Feature implemented as described: {clean[:100]}"]

    # Add role-specific quality criterion
    role_lower = role.lower()
    if "backend" in role_lower:
        ac.append("Endpoint returns correct HTTP status codes and response schema")
        ac.append("Input validation rejects malformed requests with 422")
    elif "frontend" in role_lower:
        ac.append("UI renders correctly in both LTR (English) and RTL (Arabic) layouts")
        ac.append("Component is responsive and accessible (keyboard navigable)")
    elif "ai engineer" in role_lower:
        ac.append("Output validated against 10+ representative test inputs")
        ac.append("Prompt handles edge cases without hallucination or out-of-scope responses")
    elif "architect" in role_lower:
        ac.append("Design documented and reviewed by engineering lead")
        ac.append("Security and privacy implications addressed in the design")
    elif "qa" in role_lower:
        ac.append("All test scenarios pass in the CI pipeline")
        ac.append("Test coverage report attached to the ticket")

    dod = ROLE_DOD.get(role, DEFAULT_DOD)

    return subtask_doc(description, ac[:5])


# ---------------------------------------------------------------------------
# Jira update
# ---------------------------------------------------------------------------
def update_description(issue_key: str, adf_description: dict) -> bool:
    payload = {"fields": {"description": adf_description}}
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}"
    resp = requests.put(url, auth=AUTH, headers=HEADERS, data=json.dumps(payload))
    if resp.status_code == 204:
        print(f"  OK  {issue_key}")
        return True
    else:
        print(f"  ERR {issue_key}: {resp.status_code} {resp.text[:120]}")
        return False


# ---------------------------------------------------------------------------
# Subtask data (same as create_jira_subtasks.py, with keys resolved)
# ---------------------------------------------------------------------------
STORIES_WITH_TASKS = [
    {"key": "KAN-19", "tasks": [
        "[Architect] Design auth service: JWT lifecycle (15min access/30day refresh), refresh rotation, RBAC model",
        "[Backend] POST /auth/register — Pydantic v2 validation, bcrypt password hashing",
        "[Backend] POST /auth/login — JWT access + refresh token issuance",
        "[Backend] GET /auth/google/callback — Google OAuth2 handler, upsert user",
        "[Backend] POST /auth/token/refresh — rotate refresh token",
        "[Backend] RBAC FastAPI Depends guards for all 4 roles (client/therapist/hr_admin/platform_admin)",
        "[Frontend] Registration form (email + Google SSO button), RTL-aware layout",
        "[Frontend] Login form with Forgot Password flow",
        "[Frontend] Auth token in httpOnly cookie, auto-refresh on 401, protected route guard",
        "[QA] Unit tests: JWT generation/validation, RBAC guards per role; E2E: registration to login flow",
    ]},
    {"key": "KAN-20", "tasks": [
        "[Backend] POST /auth/totp/setup — TOTP secret generation, QR code URI",
        "[Backend] POST /auth/totp/verify — TOTP code verification",
        "[Backend] TOTP enforcement middleware: block therapist/admin routes without 2FA confirmed",
        "[Frontend] TOTP setup screen: QR code display, backup codes, confirm activation",
        "[Frontend] TOTP verification screen at login (after password step)",
        "[QA] E2E: therapist login blocked without TOTP; backup code recovery flow",
    ]},
    {"key": "KAN-21", "tasks": [
        "[Architect] PDPL workflow: soft-delete then async hard-delete after 30 days, retain anonymized billing",
        "[Backend] POST /users/me/delete-request — set deleted_at flag, queue async cleanup job",
        "[Backend] Async hard-delete job: purge health data within 30 days (ai_conversations, mood_entries, session notes)",
        "[Backend] Anonymize billing records: nullify identifying fields, retain amounts for legal compliance",
        "[QA] Compliance test: health data absent from DB after 30-day simulation; billing records retain only anonymized amounts",
    ]},
    {"key": "KAN-22", "tasks": [
        "[Backend] POST /mood/anonymous — rate-limited (5/hour per IP), session-scoped, no auth required",
        "[Frontend] Landing page: hero, Start for free CTA, trust signals (licensed therapists, encrypted data)",
        "[Frontend] Mood check-in widget: emoji scale (1-10), optional text, under 60s completion",
        "[QA] Rate limit test; verify no PII required; session isolation between users",
    ]},
    {"key": "KAN-23", "tasks": [
        "[AI Engineer] Intake-to-matching prompt: map 5 intake answers to ranked therapist list with match rationale",
        "[AI Engineer] Hybrid matching: semantic embedding similarity (specialization) + Claude reranking",
        "[Backend] POST /intake — 5-question form, session-scoped storage, returns intake_id",
        "[Backend] POST /intake/{id}/match — intake_id to AI matching service, returns top 3 therapists with scores",
        "[Frontend] 5-step intake form: animated progress bar, bilingual labels (AR/EN), RTL-compatible",
        "[Frontend] Therapist recommendation cards (3): photo, specializations, price, rating, Book + Chat with AI first CTAs",
        "[QA] Matching accuracy tests with synthetic intake profiles; assert top result is language-matched",
    ]},
    {"key": "KAN-24", "tasks": [
        "[Backend] POST /auth/register — accept intake_id param to attach anonymous intake to new account",
        "[Frontend] Account creation gate: intercept Book click, show registration modal with Google SSO option",
        "[Frontend] Seamless continue-to-booking after registration (no flow restart)",
        "[QA] E2E: anonymous to intake to book click to register to booking continues with intake preserved",
    ]},
    {"key": "KAN-25", "tasks": [
        "[AI Engineer] System prompt: warm, GCC-culturally-aware, clinical boundaries (no diagnosis/treatment), defers clinical questions to therapists",
        "[AI Engineer] Streaming chat via AnthropicAdapter (SSE), language detection per message, consistency within session",
        "[Backend] POST /companion/chat — SSE streaming endpoint, crisis layer called synchronously first",
        "[Backend] Conversation session management (thread_id per conversation, max history context)",
        "[Backend] Anonymous gate: return 3-message limit prompt after 3 unauthenticated messages",
        "[Frontend] Chat UI: message bubbles, streaming text with cursor, auto-scroll to latest",
        "[Frontend] Bidi-aware text rendering: Arabic bubbles RTL, English bubbles LTR",
        "[Frontend] Talk to a human button always visible, opens therapist booking modal",
        "[QA] Streaming response integrity test; language-switch mid-conversation; anonymous 3-message gate",
    ]},
    {"key": "KAN-26", "tasks": [
        "[AI Engineer] Two-layer pipeline: (1) keyword regex fast-check (AR+EN, synchronous), (2) Claude semantic classification to risk_level/signals/confidence",
        "[AI Engineer] High-risk response override: AI response replaced with crisis protocol output regardless of AI content",
        "[Backend] CrisisDetectionService as FastAPI dependency — runs before every companion response",
        "[Backend] crisis_events insert (user_id, risk_level, signals, platform_response, timestamp) on every trigger",
        "[Backend] Therapist alert: POST to notification queue within 5 min if client has assigned therapist",
        "[Frontend] High-risk overlay: full-screen, country-specific emergency numbers (UAE/KSA/Kuwait/Bahrain), Call now tel links, dismiss requires confirmation",
        "[Frontend] Medium-risk sticky banner: Talk to someone now CTA + emergency session booking shortcut",
        "[QA] Red-team suite: 100 synthetic crisis scenarios (AR+EN), verify 0% missed high-risk, 98%+ correct classification",
    ]},
    {"key": "KAN-27", "tasks": [
        "[Architect] Encryption key management: per-user AES-256 derived keys, key rotation policy, keys in secrets manager",
        "[Backend] Encrypt messages JSONB with AES-256 before DB write; decrypt on read (user-scoped only)",
        "[Backend] Access control: platform_admin has NO access to conversation content (403 at service layer)",
        "[Backend] Retention enforcement: conversations purged after 3 years or on deletion request",
        "[QA] Assert ciphertext stored in DB (not plaintext); platform_admin GET /companion/conversations returns 403",
    ]},
    {"key": "KAN-28", "tasks": [
        "[Backend] GET /therapists — paginated, filters: language, specialization, price_min/max, gender, availability_date",
        "[Backend] GET /therapists/{id} — full profile with availability preview, rating, reviews",
        "[Backend] Filter: only return therapists with status=active and at least 1 available slot",
        "[Frontend] Therapist listing: filter sidebar (RTL-compatible collapsible), responsive card grid",
        "[Frontend] Therapist profile page: bio, credential badge (DHA/SCFHS/MOH), specializations, languages, price, rating, calendar preview",
        "[QA] Filter combination unit tests; assert status=pending/suspended therapists excluded from listings",
    ]},
    {"key": "KAN-29", "tasks": [
        "[AI Engineer] Matching algorithm: intake_answers to specialization embeddings to cosine similarity to Claude reranking with rationale",
        "[AI Engineer] Weighted factors: specialization match (40%), language preference (30%), availability (20%), rating (10%)",
        "[Backend] POST /matching/recommend — intake_id to top 3 therapist IDs + match_score + rationale",
        "[Backend] Override path: user can dismiss AI recommendations, browse all active therapists",
        "[Frontend] Recommendation UI: 3 cards with Why this therapist? tooltip showing rationale",
        "[QA] Unit tests: edge cases (no language match, no availability, tie-breaking logic)",
    ]},
    {"key": "KAN-30", "tasks": [
        "[Backend] License verification event stored: license_authority, license_verified_at, verified_by_admin_id",
        "[Frontend] Verified badge component: green checkmark, license authority name, verified date",
        "[Frontend] Pending Verification state for unverified profiles (therapist sees this in their own view)",
        "[QA] Unverified therapist shows pending state; verified badge shows correct authority name",
    ]},
    {"key": "KAN-31", "tasks": [
        "[AI Engineer] Booking agent prompt with tool definitions: query_availability, create_booking, confirm_booking",
        "[AI Engineer] Arabic NLU: date/time extraction, ambiguity resolution with clarifying questions",
        "[AI Engineer] Fallback trigger: calendar UI offered after 3 failed booking attempts",
        "[Backend] POST /booking-agent/chat — function-call handler, real-time DB availability queries",
        "[Backend] Never commit booking without explicit user confirmation",
        "[Frontend] Booking agent chat UI: minimal, focused, RTL-aware, distinct from companion chat",
        "[Frontend] Booking confirmation summary card before final confirm button",
        "[QA] 15+ NL booking scenarios (AR+EN): specific therapist, next available, evening slots, 3-attempt fallback",
    ]},
    {"key": "KAN-32", "tasks": [
        "[Backend] GET /therapists/{id}/availability?start=&end= — slots in user's detected timezone",
        "[Backend] POST /bookings — atomic slot reservation with double-booking prevention (DB-level lock)",
        "[Backend] Timezone auto-detection: use browser Intl.DateTimeFormat resolved timezone passed on booking",
        "[Frontend] Calendar weekly view: available (green), booked (grey), blocked (striped) slots",
        "[Frontend] Booking modal: select slot then payment step then confirmation",
        "[Frontend] Timezone label on all time displays e.g. 3:00 PM GST",
        "[QA] Double-booking race condition test (concurrent requests to same slot); DST edge cases",
    ]},
    {"key": "KAN-33", "tasks": [
        "[Backend] Booking created event triggers async: SendGrid confirmation email + Twilio SMS + FCM push (within 60s)",
        "[Backend] Scheduled reminder jobs: 24h before (email+SMS+push), 1h before (push only)",
        "[Backend] GET /bookings/{id}/export.ics — ICS calendar file generation",
        "[Frontend] Confirmation page: session details, Add to Calendar (Google one-click, Outlook ICS, Apple ICS)",
        "[QA] All 3 channels fire on booking; ICS validates in Google Calendar, Outlook, Apple Calendar",
    ]},
    {"key": "KAN-34", "tasks": [
        "[Backend] POST /bookings with recurrence_rule (weekly, start_date, count/until)",
        "[Backend] DELETE /bookings/{id} — single cancellation from series without breaking future slots",
        "[Backend] Cancellation policy engine: >48h full refund, 24-48h 50% credit, <24h no refund",
        "[Frontend] Recurring booking toggle + end-date/count options in booking flow",
        "[Frontend] Cancellation flow: show refund amount before confirming, confirmation modal",
        "[QA] Cancellation timing boundary tests against PRD policy; recurring series integrity after single cancel",
    ]},
    {"key": "KAN-35", "tasks": [
        "[Architect] Agora channel architecture: unique channel ID per session (UUID), short-lived token generation, E2EE via WebRTC insertable streams",
        "[Backend] GET /sessions/{id}/agora-token — Agora RTC token, expires 2h from session start",
        "[Backend] Session lifecycle state machine: scheduled to in_progress (on join) to completed/interrupted/cancelled",
        "[Backend] Recording consent check: both parties must consent; default OFF; consent stored in DB",
        "[QA] Token expiry test; state transition tests; recording consent enforcement",
    ]},
    {"key": "KAN-36", "tasks": [
        "[Frontend] Video session page: Agora RTC SDK, local + remote video tiles (720p min), audio controls, mute/unmute",
        "[Frontend] Therapist-controlled waiting room: client sees Your therapist will join shortly until therapist joins",
        "[Frontend] In-session text chat panel (WebSocket, session-scoped, ephemeral — not persisted)",
        "[Frontend] 5-minute end warning: overlay banner with session time remaining",
        "[Frontend] Session extension button (therapist only): +15 min, one per session, requires confirmation",
        "[QA] E2E: join session as client + therapist, text chat, 5-min warning fires, extension flow",
    ]},
    {"key": "KAN-37", "tasks": [
        "[Backend] Connection drop detection: mark session interrupted if both participants absent >5 min",
        "[Backend] Interrupted before 10 min: auto full-credit refund; after 10 min: priority rebooking offer",
        "[Frontend] Reconnection UI: Reconnecting overlay, auto-retry for 2 minutes",
        "[Frontend] Interrupted session screen: credit/rebooking notification based on timing",
        "[QA] Simulate drop before 10 min (assert full credit issued); after 10 min (assert rebooking offered, no refund)",
    ]},
    {"key": "KAN-38", "tasks": [
        "[Backend] POST /mood-entries — auth required, score 1-10, note (AES-256 encrypted before storage)",
        "[Backend] Idempotency: one entry per user per day (upsert by user_id + date)",
        "[Backend] FCM push trigger for daily reminder at user-configured time",
        "[Frontend] Mood check-in widget: emoji scale (1-10), optional text note field, submit in under 60s",
        "[Frontend] Push notification permission request + time picker for daily reminder (opt-in only)",
        "[QA] Encrypted note in DB (verify ciphertext); idempotency test (second check-in same day updates, not duplicates)",
    ]},
    {"key": "KAN-39", "tasks": [
        "[Backend] GET /mood-entries?days=30|90 — decrypted entries for authenticated user only",
        "[Frontend] Mood timeline page: area chart with 30/90-day toggle, trend indicator",
        "[Frontend] Entry list below chart: date, emoji score, note (expandable)",
        "[QA] Chart with 0 entries (empty state), 1 entry, 90 entries; data scoped to authenticated user only",
    ]},
    {"key": "KAN-40", "tasks": [
        "[Backend] PATCH /client-profiles/mood-sharing — toggle therapist access (explicit opt-in, defaults to OFF)",
        "[Backend] GET /mood-entries/client/{client_id} for therapists — return 403 without explicit consent",
        "[Frontend] Share mood data with therapist toggle in Privacy Settings page",
        "[Frontend] Therapist client dashboard: mood chart section visible only when consent=true",
        "[QA] Without consent: therapist API returns 403; with consent: mood data accessible; revoke consent triggers immediate 403",
    ]},
    {"key": "KAN-41", "tasks": [
        "[Backend] GET /content — filters: category, format (article/audio/video), language, full-text search (PostgreSQL FTS)",
        "[Backend] GET /content/{id} — increment view_count atomically",
        "[Frontend] Content library page: card grid with filter sidebar (RTL-compatible), search bar with debounce",
        "[Frontend] Article reader with reading time estimate; audio player (custom controls) for meditations",
        "[Frontend] Language toggle: show AR or EN content based on user preference",
        "[QA] Full-text search relevance (AR+EN); draft content not visible to end users; view_count increments",
    ]},
    {"key": "KAN-42", "tasks": [
        "[Backend] Personalization scoring: rank by intake category overlap + recent mood trend",
        "[Backend] GET /content/recommended — auth required, returns top 10 scored items",
        "[Frontend] Recommended for you section on dashboard and content library",
        "[Frontend] Push notification for new relevant content (opt-in, daily digest max)",
        "[QA] Personalization unit tests with synthetic user profiles; verify opt-out respected for push",
    ]},
    {"key": "KAN-43", "tasks": [
        "[Backend] POST /admin/content, PATCH /admin/content/{id}, DELETE /admin/content/{id}",
        "[Backend] Status state machine: draft to review to published (only platform_admin can publish)",
        "[Backend] GET /admin/content/analytics — views, avg_rating, reads per category",
        "[Frontend] Admin content editor: rich-text body, category/language/format tags, media upload to R2",
        "[Frontend] Status workflow UI: draft/review/publish badges, transition buttons with confirmation",
        "[QA] State machine: draft not visible to users; only platform_admin can transition to published",
    ]},
    {"key": "KAN-44", "tasks": [
        "[Architect] Payment architecture: card tokenization via Tap.js (no raw card data on backend), webhook signature verification",
        "[Backend] POST /payments/initiate — create Tap charge intent, return payment_url or hosted payment page",
        "[Backend] POST /payments/webhook — verify Tap HMAC signature, handle payment.paid/payment.failed events",
        "[Backend] Corporate credit path: deduct from corporate_accounts.session_credits_used (atomic transaction)",
        "[Frontend] Checkout modal: Tap Payments UI embed (card, mada, Apple Pay, KNET)",
        "[Frontend] Payment success and failure screens with clear next action",
        "[QA] Tap sandbox: success, 3DS, mada, Apple Pay, failure, timeout; webhook signature rejection on tampered payload",
    ]},
    {"key": "KAN-45", "tasks": [
        "[Backend] Refund engine: cancellation event, evaluate timing rule, call Tap refund API or issue platform credit",
        "[Backend] Therapist no-show: full refund via Tap + AED 50 platform credit issuance",
        "[Backend] Platform credit ledger: credits table (user_id, amount, reason, expires_at)",
        "[Frontend] Refund status page in user account: pending/processed status, timeline",
        "[Frontend] Platform credit balance display in account + apply credit at checkout",
        "[QA] All 5 cancellation scenarios from PRD policy table; credit balance applied correctly at next booking",
    ]},
    {"key": "KAN-46", "tasks": [
        "[Backend] GET /therapist/earnings — completed sessions, pending, total_earned, platform_fee (30%), net_payout",
        "[Backend] POST /therapist/payout-requests — minimum AED 100 balance, store bank_details_ref",
        "[Backend] Monthly earnings PDF generation (WeasyPrint/ReportLab): sessions breakdown, platform fee, net",
        "[Frontend] Therapist earnings dashboard: KPI cards (earned, pending, available for payout)",
        "[Frontend] Payout request form: bank transfer details, submit, status tracker (pending/processing/paid)",
        "[Frontend] Download monthly statement PDF button",
        "[QA] 70/30 revenue split accuracy; payout below AED 100 rejected; PDF contains no other therapist data",
    ]},
    {"key": "KAN-47", "tasks": [
        "[Architect] Data model: corporate_accounts to employees (identity isolated from reports), credit pool, HR admin role",
        "[Backend] POST /admin/corporate-accounts — platform admin creates company account",
        "[Backend] POST /corporate/{id}/employees — CSV upload (email list) + single manual add",
        "[Backend] DELETE /corporate/{id}/employees/{user_id} — remove employee access",
        "[Frontend] Corporate admin portal: company settings, employee roster table with add/remove",
        "[Frontend] CSV upload UI with row-level validation error display",
        "[QA] CSV with malformed rows (missing email, invalid domain): partial success with error report; employee removal blocks future access",
    ]},
    {"key": "KAN-48", "tasks": [
        "[Backend] Credit deduction: atomic transaction on booking creation (prevent overdraft)",
        "[Backend] GET /corporate/{id}/credits — total, used, remaining",
        "[Backend] Low-credit alert: FCM/email to HR admin when fewer than 10 credits remaining",
        "[Frontend] Credit usage dashboard: total/used/remaining KPI cards, utilization bar",
        "[QA] Concurrent booking test: 2 simultaneous requests for last credit — only 1 succeeds (no overdraft)",
    ]},
    {"key": "KAN-49", "tasks": [
        "[Backend] Email domain verification: check user email domain against corporate_accounts allowed domains",
        "[Backend] Company code path: alternative to domain verification for companies with multiple domains",
        "[Backend] Link user_id to corporate_accounts on first verified login",
        "[Frontend] Corporate onboarding page: company code entry field, domain auto-detection",
        "[Frontend] Post-SSO onboarding: standard 5-question intake then standard therapist pool",
        "[QA] E2E: employee enters company code, takes intake, books session, credit deducted from pool",
    ]},
    {"key": "KAN-50", "tasks": [
        "[Architect] OAuth2 corporate flow: state param + PKCE, email domain to corporate account lookup, no personal Google accounts",
        "[Backend] GET /auth/sso/google/authorize — redirect to Google with state param",
        "[Backend] GET /auth/sso/google/callback — exchange code, validate domain, upsert employee user, issue platform JWT",
        "[Frontend] Sign in with Google Workspace button on corporate login page",
        "[Frontend] Error screen: Your email domain is not registered with any corporate account",
        "[QA] Mock OAuth2 server tests: valid domain, invalid domain, state mismatch, expired code",
    ]},
    {"key": "KAN-51", "tasks": [
        "[Architect] SAML 2.0 SP design: metadata generation, ACS endpoint, assertion validation (signature, expiry, audience)",
        "[Backend] GET /auth/sso/saml/metadata — SP metadata XML for Azure AD configuration",
        "[Backend] POST /auth/sso/saml/acs — assertion consumer, validate + parse claims, issue platform JWT",
        "[Backend] corporate_accounts.sso_config: store IdP metadata XML (encrypted at rest)",
        "[Frontend] Corporate admin SSO config page: upload IdP metadata XML, test connection button",
        "[QA] Mock SAML IdP tests: valid assertion, expired assertion, invalid signature, wrong audience",
    ]},
    {"key": "KAN-52", "tasks": [
        "[Architect] Anonymization: k-anonymity model (min 5 employees per dept), report contains NO session content or individual identity",
        "[Backend] GET /corporate/{id}/reports/utilization — sessions used/remaining, by-dept breakdown with k-anonymity enforcement",
        "[Backend] Suppress department rows with fewer than 5 employees (replace with Other bucket)",
        "[Frontend] Utilization dashboard: KPI cards (total used, remaining, utilization %), monthly trend chart",
        "[Frontend] Department breakdown table: suppressed depts show fewer than 5 employees label",
        "[Frontend] PDF export for full utilization report",
        "[QA] K-anonymity: dept with 4 employees suppressed; assert response body contains no user IDs or names",
    ]},
    {"key": "KAN-53", "tasks": [
        "[Backend] Cron job: quarterly report generation (sessions_used, sessions_remaining, dept utilization, trends)",
        "[Backend] SendGrid: auto-email PDF report to HR admin email on schedule",
        "[Frontend] Report history table: past reports with generated_at date and download link",
        "[QA] Cron test: report generated and email triggered; PDF download link works; report contains no PHI",
    ]},
    {"key": "KAN-54", "tasks": [
        "[Backend] POST /therapist/availability — set recurring weekly slots (day_of_week, start_time, end_time)",
        "[Backend] PATCH /therapist/availability/{id}/block — block specific date/slot without affecting recurrence",
        "[Backend] 15-minute buffer enforcement: reject slot overlapping with existing session + 15 min buffer",
        "[Backend] Double-booking prevention across all booking entry points (AI agent + calendar UI)",
        "[Frontend] Availability calendar UI: weekly view, drag-to-create slots, block-day button",
        "[Frontend] Timezone label on all slots; local time stored, UTC in DB",
        "[QA] 15-min buffer enforced (slot 10:00-11:00 means next allowed at 11:15); double-booking attempt returns 409",
    ]},
    {"key": "KAN-55", "tasks": [
        "[Backend] GET /therapist/clients — paginated list with intake summary, last session date",
        "[Backend] POST/GET/PATCH /therapist/session-notes/{session_id} — private notes, therapist-only access",
        "[Backend] Secure messaging: WebSocket room per client-therapist pair (in-platform only)",
        "[Frontend] Client dashboard: intake answers, session history list, notes editor panel",
        "[Frontend] Session notes: rich-text editor with auto-save draft every 30s",
        "[Frontend] In-platform messaging thread UI per client",
        "[QA] Client cannot read therapist private notes via API (403); messaging room isolated between client pairs",
    ]},
    {"key": "KAN-56", "tasks": [
        "[Backend] GET /admin/therapist-applications — list with status filter (pending/approved/rejected/info_requested)",
        "[Backend] PATCH /admin/therapist-applications/{id} — approve/reject/request_info with email notifications",
        "[Backend] Every verification action logged in audit_log: admin_id, action, therapist_id, timestamp",
        "[Frontend] Admin verification dashboard: application list, document viewer (R2 signed URLs for license docs)",
        "[Frontend] Approve/reject/request-info modal with required reason text field",
        "[QA] Approval activates therapist account; rejection sends email; all actions in audit log with correct actor_id",
    ]},
    {"key": "KAN-57", "tasks": [
        "[Backend] GET /admin/audit-logs — paginated, filters: actor_id, event_type, resource_type, date range",
        "[Backend] DB constraint: audit_log table has no UPDATE/DELETE permissions (append-only enforced)",
        "[Backend] Monthly compliance report: PHI access count, crisis escalations count, account deletions count",
        "[Frontend] Audit log viewer: sortable table, filter panel, CSV export",
        "[Frontend] Compliance report page: summary tiles + downloadable PDF",
        "[QA] Attempt UPDATE on audit_log row returns DB error; filter accuracy; CSV export integrity",
    ]},
    {"key": "KAN-58", "tasks": [
        "[AI Engineer] Layer 1: regex keyword matcher (Arabic + English crisis phrases, runs in under 5ms, synchronous)",
        "[AI Engineer] Layer 2: Claude prompt for semantic risk classification returning structured JSON with risk_level, signals, confidence",
        "[AI Engineer] Layer 1 short-circuits to Layer 2 only when keywords detected (performance optimization)",
        "[Backend] CrisisDetectionService: injected as FastAPI dependency in companion route, no async HTTP hop",
        "[Backend] Country detection: user timezone mapped to UAE/KSA/Kuwait/Bahrain emergency numbers",
        "[QA] 200+ unit test phrases (AR+EN) for keyword layer; integration test: Layer 2 invoked only when Layer 1 triggers",
    ]},
    {"key": "KAN-59", "tasks": [
        "[AI Engineer] High-risk response template: emergency numbers, helplines, You are not alone message (AR+EN)",
        "[Backend] High-risk: AI response replaced unconditionally with crisis protocol output",
        "[Backend] Therapist alert: create urgent notification for assigned therapist (delivered within 5 min SLA)",
        "[Backend] Crisis event creation before response is returned (synchronous, not fire-and-forget)",
        "[Frontend] High-risk overlay: full-screen modal, cannot dismiss with single tap (requires confirmation), Call now tel links",
        "[Frontend] Medium-risk sticky banner: above chat, Talk to someone now leads to emergency session booking",
        "[QA] E2E: high-risk message triggers overlay + crisis event in DB + therapist notification — all within single request cycle",
    ]},
    {"key": "KAN-60", "tasks": [
        "[Architect] Crisis log access control: separate safety_officer sub-role, platform_admin (non-officer) gets 403 on crisis log reads",
        "[Backend] crisis_events schema: user_id, conversation_id, risk_level, trigger_signals (JSONB), platform_response, therapist_notified, logged_at",
        "[Backend] 7-year retention: soft-delete blocked on crisis_events; hard-delete requires safety_officer + legal approval workflow",
        "[QA] Every risk level creates crisis event; platform_admin (non-officer) gets 403; verify retention policy enforced at API level",
    ]},
    {"key": "KAN-61", "tasks": [
        "[AI Engineer] Abstract base class: AIProvider with generate(prompt), chat(messages), embed(text) interface methods",
        "[AI Engineer] AnthropicAdapter: Claude API, streaming support, token counting, system prompt injection",
        "[AI Engineer] OpenAIAdapter: GPT-4o, same interface, used as automatic fallback",
        "[AI Engineer] Rate limit detector: catch 429 and switch to fallback provider transparently",
        "[AI Engineer] Prompt template manager: versioned templates per feature (companion_v1, booking_v1, etc.), no hardcoded prompts in route handlers",
        "[Backend] Provider factory: get_ai_provider() FastAPI dependency reads AI_PROVIDER env var",
        "[Backend] PHI safety: user IDs anonymized in all prompts (UUID only, no identifying info sent to AI)",
        "[QA] Swap AI_PROVIDER=openai via env var without code change; fallback triggers on mocked 429; no PII in prompt strings",
    ]},
    {"key": "KAN-62", "tasks": [
        "[AI Engineer] Booking agent prompt: tool-calling schema for query_availability, create_booking, confirm_booking",
        "[AI Engineer] Arabic date/time NLU: next Tuesday evening maps to structured date/time/week object",
        "[AI Engineer] Clarification loop: ask specific questions when intent is ambiguous (under 3 turns before fallback)",
        "[Backend] POST /booking-agent/chat — tool call handler executes real DB queries, returns structured tool results to AI",
        "[Frontend] Booking agent chat interface: minimal, conversational, shows confirmation card before final commit",
        "[QA] 15+ booking scenarios: specific therapist, next available, evening preference, Arabic input, 3-attempt fallback",
    ]},
    {"key": "KAN-63", "tasks": [
        "[AI Engineer] Support agent prompt: knowledge base (FAQ, pricing, cancellation policy, therapist application steps)",
        "[AI Engineer] Confidence threshold: if below 0.7 escalate to human support ticket",
        "[AI Engineer] Scope guardrails: no clinical advice, no specific therapist recommendations in support context",
        "[Backend] POST /support/chat — message handler with confidence-based human handoff",
        "[Backend] POST /support/tickets — create ticket on handoff with conversation transcript (no PHI in ticket summary)",
        "[Frontend] Support chat widget: floating bottom-right, accessible from all pages, minimizable",
        "[QA] 20+ support scenarios (billing, cancellation, account, therapist application); human handoff triggers correctly; ticket created without PHI",
    ]},
    {"key": "KAN-64", "tasks": [
        "[Architect] Notification service: event-driven async queue, provider-agnostic interface (swap SendGrid to SES with env var)",
        "[Backend] SendGrid: transactional email templates (booking confirmation, 24h/1h reminder, payout statement, welcome)",
        "[Backend] Twilio SMS: session reminders (24h), OTP, crisis-related alerts to safety officer",
        "[Backend] NotificationPreferences model: per-user per-channel opt-out, respected by all send functions",
        "[Frontend] Notification preferences page: toggle per channel (email/SMS/push) per event type",
        "[QA] All triggers fire correct channel; opt-out respected; no PHI in notification payloads",
    ]},
    {"key": "KAN-65", "tasks": [
        "[Backend] Firebase Admin SDK: send_multicast to registered device tokens per user",
        "[Backend] POST /users/push-tokens — register device token for authenticated user",
        "[Backend] Push triggers: booking confirmation, 1h reminder, new recommended content, therapist alert on medium/high crisis",
        "[Frontend] Push permission request prompt (PWA service worker registration)",
        "[Frontend] In-app notification bell with unread count badge",
        "[QA] Push delivery test in PWA context; unread count increments; permission-denied fallback to email",
    ]},
    {"key": "KAN-66", "tasks": [
        "[Backend] ICS generation: RFC 5545 compliant calendar file for any booking",
        "[Backend] Google Calendar OAuth2 flow: /calendar/google/authorize to /calendar/google/callback to create event",
        "[Frontend] Add to Calendar component: Google one-click OAuth, Outlook download ICS, Apple Calendar download ICS",
        "[QA] ICS validates in Google Calendar, Outlook, Apple Calendar; Google OAuth creates event in user calendar",
    ]},
    {"key": "KAN-67", "tasks": [
        "[Architect] FastAPI Dockerfile: multi-stage (build + runtime), non-root user, EXPOSE 8000, HEALTHCHECK",
        "[Architect] Next.js Dockerfile: multi-stage, output standalone in next.config.js, non-root user",
        "[Architect] docker-compose.yml: postgres:16, redis:7, backend, frontend with volume mounts and env_file",
        "[Architect] .env.example: all required vars documented (DATABASE_URL, AI_PROVIDER, AGORA_APP_ID, TAP_SECRET_KEY, SENDGRID_API_KEY, TWILIO_AUTH_TOKEN, FCM_CREDENTIALS, CLOUDFLARE_R2_KEY)",
        "[QA] docker-compose up: all 4 services healthy; backend /health returns 200; frontend serves home page",
    ]},
    {"key": "KAN-68", "tasks": [
        "[Architect] Workflow file: lint (Ruff + ESLint) then pytest unit then pytest integration then Docker build",
        "[Architect] Staging deploy job: deploy to Render staging + run Cypress E2E then notify on failure",
        "[Architect] Production deploy job: manual approval gate (GitHub Environments) then deploy to Render + Vercel prod",
        "[Architect] validate-env.sh: fail pipeline if any required env var is unset before deploy step",
        "[Architect] check-phi-leaks.sh: scan log output and source for PHI patterns (email regex, phone regex, name fields), fail CI on match",
        "[QA] Verify manual approval gate blocks auto-deploy to prod; Cypress E2E runs against staging after each staging deploy",
    ]},
    {"key": "KAN-69", "tasks": [
        "[Architect] vercel.json: Next.js framework, env vars config, domain redirect (www to apex or vice versa)",
        "[Architect] Render services: FastAPI web service (Docker), managed PostgreSQL 16, managed Redis 7",
        "[Architect] Cloudflare R2: bucket creation, CORS config, signed URL generation for private assets (license docs)",
        "[Architect] Environment variable management: staging vs prod separation in Render + Vercel dashboards",
        "[QA] Staging smoke test: /health, /auth/register, /therapists, /content all respond correctly; R2 signed URL access works",
    ]},
    {"key": "KAN-70", "tasks": [
        "[Architect] Sentry: Next.js client + server, FastAPI — scrub PHI from error payloads before send",
        "[Architect] PostHog: anonymized events (session_booked, companion_message_sent, crisis_detected) — no user PII in event props",
        "[Architect] Better Uptime: monitors for frontend, backend /health, Agora webhook endpoint",
        "[Architect] PagerDuty: P0 alerts (service down >2 min, crisis detection service failure)",
        "[Architect] Render scaling config: scale-out trigger at >70% CPU for 2 min; pre-warm 30 min before peak hours (6PM-9PM GST)",
        "[QA] k6 load test: 500 concurrent users simulating session booking flow; assert API P99 under 500ms; no errors above 1%",
    ]},
]


def build_subtask_map() -> dict:
    """Build a map of {issue_key: description_adf} for all subtasks.
    Keys are assigned sequentially starting at KAN-71."""
    result = {}
    current_key = 71
    for story in STORIES_WITH_TASKS:
        for task_summary in story["tasks"]:
            key = f"KAN-{current_key}"
            result[key] = generate_subtask_description(task_summary)
            current_key += 1
    return result


def main():
    ok = 0
    errors = 0

    # --- Update stories (KAN-19 to KAN-70) ---
    print(f"Updating {len(STORY_DESCRIPTIONS)} story descriptions...\n")
    for key, description in STORY_DESCRIPTIONS.items():
        if update_description(key, description):
            ok += 1
        else:
            errors += 1
        time.sleep(DELAY)

    # --- Update subtasks (KAN-71 to KAN-381) ---
    subtask_map = build_subtask_map()
    print(f"\nUpdating {len(subtask_map)} subtask descriptions...\n")
    for key, description in subtask_map.items():
        if update_description(key, description):
            ok += 1
        else:
            errors += 1
        time.sleep(DELAY)

    print(f"\n{'='*60}")
    print(f"DONE  —  Updated: {ok}  |  Errors: {errors}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
