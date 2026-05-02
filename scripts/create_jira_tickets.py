#!/usr/bin/env python3
"""
Create Jira Stories & Tasks for GCC Wellness Platform (ONE_WELLNESS / KAN project).

Usage:
    JIRA_EMAIL=you@example.com JIRA_API_TOKEN=your_token python3 create_jira_tickets.py

Epics KAN-1 through KAN-18 must already exist.
"""

import json
import os
import sys
import time

import requests
from requests.auth import HTTPBasicAuth

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
JIRA_BASE_URL = "https://jsaiyed.atlassian.net"
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
PROJECT_KEY = "KAN"
DELAY_BETWEEN_CALLS = 0.15  # seconds — stay well within Jira rate limits

if not JIRA_EMAIL or not JIRA_API_TOKEN:
    print("ERROR: Set JIRA_EMAIL and JIRA_API_TOKEN environment variables before running.")
    sys.exit(1)

AUTH = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

# ---------------------------------------------------------------------------
# Issue type IDs — fetched dynamically
# ---------------------------------------------------------------------------
def get_issue_type_ids():
    url = f"{JIRA_BASE_URL}/rest/api/3/issuetype"
    resp = requests.get(url, auth=AUTH, headers=HEADERS)
    resp.raise_for_status()
    types = {t["name"]: t["id"] for t in resp.json()}
    return types


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------
def create_issue(summary: str, issue_type_id: str, parent_key: str, labels: list) -> str:
    """Create a Jira issue and return its key."""
    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "summary": summary,
            "issuetype": {"id": issue_type_id},
            "parent": {"key": parent_key},
            "labels": labels,
        }
    }
    url = f"{JIRA_BASE_URL}/rest/api/3/issue"
    resp = requests.post(url, auth=AUTH, headers=HEADERS, data=json.dumps(payload))
    if resp.status_code not in (200, 201):
        print(f"  ERROR creating '{summary[:60]}': {resp.status_code} {resp.text[:200]}")
        return ""
    key = resp.json()["key"]
    print(f"  + {key}  {summary[:80]}")
    return key


# ---------------------------------------------------------------------------
# Ticket data  —  Epic -> [Story -> [Task]]
# ---------------------------------------------------------------------------
EPICS = [
    # -----------------------------------------------------------------------
    # KAN-1  User Auth & Account Management
    # -----------------------------------------------------------------------
    {
        "key": "KAN-1",
        "stories": [
            {
                "summary": "User Registration & Login",
                "labels": [],
                "tasks": [
                    {"summary": "[Architect] Design auth service: JWT lifecycle (15min access/30day refresh), refresh rotation, RBAC model", "labels": ["architect"]},
                    {"summary": "[Backend] POST /auth/register — Pydantic v2 validation, bcrypt password hashing", "labels": ["backend"]},
                    {"summary": "[Backend] POST /auth/login — JWT access + refresh token issuance", "labels": ["backend"]},
                    {"summary": "[Backend] GET /auth/google/callback — Google OAuth2 handler, upsert user", "labels": ["backend"]},
                    {"summary": "[Backend] POST /auth/token/refresh — rotate refresh token", "labels": ["backend"]},
                    {"summary": "[Backend] RBAC FastAPI Depends guards for all 4 roles (client/therapist/hr_admin/platform_admin)", "labels": ["backend"]},
                    {"summary": "[Frontend] Registration form (email + Google SSO button), RTL-aware layout", "labels": ["frontend"]},
                    {"summary": "[Frontend] Login form with Forgot Password flow", "labels": ["frontend"]},
                    {"summary": "[Frontend] Auth token in httpOnly cookie, auto-refresh on 401, protected route guard", "labels": ["frontend"]},
                    {"summary": "[QA] Unit tests: JWT generation/validation, RBAC guards per role; E2E: registration to login flow", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Two-Factor Authentication (TOTP)",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] POST /auth/totp/setup — TOTP secret generation, QR code URI", "labels": ["backend"]},
                    {"summary": "[Backend] POST /auth/totp/verify — TOTP code verification", "labels": ["backend"]},
                    {"summary": "[Backend] TOTP enforcement middleware: block therapist/admin routes without 2FA confirmed", "labels": ["backend"]},
                    {"summary": "[Frontend] TOTP setup screen: QR code display, backup codes, confirm activation", "labels": ["frontend"]},
                    {"summary": "[Frontend] TOTP verification screen at login (after password step)", "labels": ["frontend"]},
                    {"summary": "[QA] E2E: therapist login blocked without TOTP; backup code recovery flow", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Account Deletion & PDPL Compliance",
                "labels": [],
                "tasks": [
                    {"summary": "[Architect] PDPL workflow: soft-delete then async hard-delete after 30 days, retain anonymized billing", "labels": ["architect"]},
                    {"summary": "[Backend] POST /users/me/delete-request — set deleted_at flag, queue async cleanup job", "labels": ["backend"]},
                    {"summary": "[Backend] Async hard-delete job: purge health data within 30 days (ai_conversations, mood_entries, session notes)", "labels": ["backend"]},
                    {"summary": "[Backend] Anonymize billing records: nullify name/email, retain amounts for legal compliance", "labels": ["backend"]},
                    {"summary": "[QA] Compliance test: health data absent from DB after 30-day simulation; billing records retain only anonymized amounts", "labels": ["qa"]},
                ],
            },
        ],
    },

    # -----------------------------------------------------------------------
    # KAN-2  Anonymous Entry & Onboarding
    # -----------------------------------------------------------------------
    {
        "key": "KAN-2",
        "stories": [
            {
                "summary": "Anonymous Mood Check-In",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] POST /mood/anonymous — rate-limited (5/hour per IP), session-scoped, no auth required", "labels": ["backend"]},
                    {"summary": "[Frontend] Landing page: hero, Start for free CTA, trust signals (licensed therapists, encrypted data)", "labels": ["frontend"]},
                    {"summary": "[Frontend] Mood check-in widget: emoji scale (1-10), optional text, under 60s completion", "labels": ["frontend"]},
                    {"summary": "[QA] Rate limit test; verify no PII required; session isolation between users", "labels": ["qa"]},
                ],
            },
            {
                "summary": "5-Question Intake & AI Therapist Matching",
                "labels": [],
                "tasks": [
                    {"summary": "[AI Engineer] Intake-to-matching prompt: map 5 intake answers to ranked therapist list with match rationale", "labels": ["ai-engineer"]},
                    {"summary": "[AI Engineer] Hybrid matching: semantic embedding similarity (specialization) + Claude reranking", "labels": ["ai-engineer"]},
                    {"summary": "[Backend] POST /intake — 5-question form, session-scoped storage, returns intake_id", "labels": ["backend"]},
                    {"summary": "[Backend] POST /intake/{id}/match — intake_id to AI matching service to top 3 therapists with scores", "labels": ["backend"]},
                    {"summary": "[Frontend] 5-step intake form: animated progress bar, bilingual labels (AR/EN), RTL-compatible", "labels": ["frontend"]},
                    {"summary": "[Frontend] Therapist recommendation cards (3): photo, specializations, price, rating, Book + Chat with AI first CTAs", "labels": ["frontend"]},
                    {"summary": "[QA] Matching accuracy tests with synthetic intake profiles; assert top result is language-matched", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Account Creation Gate",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] POST /auth/register — accept intake_id param to attach anonymous intake to new account", "labels": ["backend"]},
                    {"summary": "[Frontend] Account creation gate: intercept Book click, show registration modal with Google SSO option", "labels": ["frontend"]},
                    {"summary": "[Frontend] Seamless continue-to-booking after registration (no flow restart)", "labels": ["frontend"]},
                    {"summary": "[QA] E2E: anonymous to intake to book click to register to booking continues with intake preserved", "labels": ["qa"]},
                ],
            },
        ],
    },

    # -----------------------------------------------------------------------
    # KAN-3  AI Companion Chat
    # -----------------------------------------------------------------------
    {
        "key": "KAN-3",
        "stories": [
            {
                "summary": "Bilingual Chat Interface",
                "labels": [],
                "tasks": [
                    {"summary": "[AI Engineer] System prompt: warm, GCC-culturally-aware, clinical boundaries (no diagnosis/treatment), defers clinical questions to therapists", "labels": ["ai-engineer"]},
                    {"summary": "[AI Engineer] Streaming chat via AnthropicAdapter (SSE), language detection per message, consistency within session", "labels": ["ai-engineer"]},
                    {"summary": "[Backend] POST /companion/chat — SSE streaming endpoint, crisis layer called synchronously first", "labels": ["backend"]},
                    {"summary": "[Backend] Conversation session management (thread_id per conversation, max history context)", "labels": ["backend"]},
                    {"summary": "[Backend] Anonymous gate: return 3-message limit prompt after 3 unauthenticated messages", "labels": ["backend"]},
                    {"summary": "[Frontend] Chat UI: message bubbles, streaming text with cursor, auto-scroll to latest", "labels": ["frontend"]},
                    {"summary": "[Frontend] Bidi-aware text rendering: Arabic bubbles RTL, English bubbles LTR", "labels": ["frontend"]},
                    {"summary": "[Frontend] Talk to a human button always visible, opens therapist booking modal", "labels": ["frontend"]},
                    {"summary": "[QA] Streaming response integrity test; language-switch mid-conversation; anonymous 3-message gate", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Crisis Detection & Escalation",
                "labels": [],
                "tasks": [
                    {"summary": "[AI Engineer] Two-layer pipeline: (1) keyword regex fast-check (AR+EN, synchronous), (2) Claude semantic classification to risk_level/signals/confidence", "labels": ["ai-engineer"]},
                    {"summary": "[AI Engineer] High-risk response override: AI response replaced with crisis protocol output regardless of AI content", "labels": ["ai-engineer"]},
                    {"summary": "[Backend] CrisisDetectionService as FastAPI dependency — runs before every companion response", "labels": ["backend"]},
                    {"summary": "[Backend] crisis_events insert (user_id, risk_level, signals, platform_response, timestamp) on every trigger", "labels": ["backend"]},
                    {"summary": "[Backend] Therapist alert: POST to notification queue within 5 min if client has assigned therapist", "labels": ["backend"]},
                    {"summary": "[Frontend] High-risk overlay: full-screen, country-specific emergency numbers (UAE/KSA/Kuwait/Bahrain), Call now tel links, dismiss requires confirmation", "labels": ["frontend"]},
                    {"summary": "[Frontend] Medium-risk sticky banner: Talk to someone now CTA + emergency session booking shortcut", "labels": ["frontend"]},
                    {"summary": "[QA] Red-team suite: 100 synthetic crisis scenarios (AR+EN), verify 0% missed high-risk, 98%+ correct classification", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Conversation Encryption & Access Control",
                "labels": [],
                "tasks": [
                    {"summary": "[Architect] Encryption key management: per-user AES-256 derived keys, key rotation policy, keys in secrets manager", "labels": ["architect"]},
                    {"summary": "[Backend] Encrypt messages JSONB with AES-256 before DB write; decrypt on read (user-scoped only)", "labels": ["backend"]},
                    {"summary": "[Backend] Access control: platform_admin has NO access to conversation content (403 at service layer)", "labels": ["backend"]},
                    {"summary": "[Backend] Retention enforcement: conversations purged after 3 years or on deletion request", "labels": ["backend"]},
                    {"summary": "[QA] Assert ciphertext stored in DB (not plaintext); platform_admin GET /companion/conversations returns 403", "labels": ["qa"]},
                ],
            },
        ],
    },

    # -----------------------------------------------------------------------
    # KAN-4  Therapist Discovery & AI Matching
    # -----------------------------------------------------------------------
    {
        "key": "KAN-4",
        "stories": [
            {
                "summary": "Therapist Profile Browser",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] GET /therapists — paginated, filters: language, specialization, price_min/max, gender, availability_date", "labels": ["backend"]},
                    {"summary": "[Backend] GET /therapists/{id} — full profile with availability preview, rating, reviews", "labels": ["backend"]},
                    {"summary": "[Backend] Filter: only return therapists with status=active and at least 1 available slot", "labels": ["backend"]},
                    {"summary": "[Frontend] Therapist listing: filter sidebar (RTL-compatible collapsible), responsive card grid", "labels": ["frontend"]},
                    {"summary": "[Frontend] Therapist profile page: bio, credential badge (DHA/SCFHS/MOH), specializations, languages, price, rating, calendar preview", "labels": ["frontend"]},
                    {"summary": "[QA] Filter combination unit tests; assert status=pending/suspended therapists excluded from listings", "labels": ["qa"]},
                ],
            },
            {
                "summary": "AI Therapist Matching Engine",
                "labels": [],
                "tasks": [
                    {"summary": "[AI Engineer] Matching algorithm: intake_answers to specialization embeddings to cosine similarity to Claude reranking with rationale", "labels": ["ai-engineer"]},
                    {"summary": "[AI Engineer] Weighted factors: specialization match (40%), language preference (30%), availability (20%), rating (10%)", "labels": ["ai-engineer"]},
                    {"summary": "[Backend] POST /matching/recommend — intake_id to top 3 therapist IDs + match_score + rationale", "labels": ["backend"]},
                    {"summary": "[Backend] Override path: user can dismiss AI recommendations, browse all active therapists", "labels": ["backend"]},
                    {"summary": "[Frontend] Recommendation UI: 3 cards with Why this therapist? tooltip showing rationale", "labels": ["frontend"]},
                    {"summary": "[QA] Unit tests: edge cases (no language match, no availability, tie-breaking logic)", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Credential Verification Display",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] License verification event stored: license_authority, license_verified_at, verified_by_admin_id", "labels": ["backend"]},
                    {"summary": "[Frontend] Verified badge component: green checkmark, license authority name, verified date", "labels": ["frontend"]},
                    {"summary": "[Frontend] Pending Verification state for unverified profiles (therapist sees this in their own view)", "labels": ["frontend"]},
                    {"summary": "[QA] Unverified therapist shows pending state; verified badge shows correct authority name", "labels": ["qa"]},
                ],
            },
        ],
    },

    # -----------------------------------------------------------------------
    # KAN-5  Session Booking & Scheduling
    # -----------------------------------------------------------------------
    {
        "key": "KAN-5",
        "stories": [
            {
                "summary": "AI Booking Agent",
                "labels": [],
                "tasks": [
                    {"summary": "[AI Engineer] Booking agent prompt with tool definitions: query_availability, create_booking, confirm_booking", "labels": ["ai-engineer"]},
                    {"summary": "[AI Engineer] Arabic NLU: date/time extraction, ambiguity resolution with clarifying questions", "labels": ["ai-engineer"]},
                    {"summary": "[AI Engineer] Fallback trigger: calendar UI offered after 3 failed booking attempts", "labels": ["ai-engineer"]},
                    {"summary": "[Backend] POST /booking-agent/chat — function-call handler, real-time DB availability queries", "labels": ["backend"]},
                    {"summary": "[Backend] Never commit booking without explicit user confirmation", "labels": ["backend"]},
                    {"summary": "[Frontend] Booking agent chat UI: minimal, focused, RTL-aware, distinct from companion chat", "labels": ["frontend"]},
                    {"summary": "[Frontend] Booking confirmation summary card before final confirm button", "labels": ["frontend"]},
                    {"summary": "[QA] 15+ NL booking scenarios (AR+EN): specific therapist, next available, evening slots, 3-attempt fallback", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Calendar UI Booking",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] GET /therapists/{id}/availability?start=&end= — slots in user's detected timezone", "labels": ["backend"]},
                    {"summary": "[Backend] POST /bookings — atomic slot reservation with double-booking prevention (DB-level lock)", "labels": ["backend"]},
                    {"summary": "[Backend] Timezone auto-detection: use browser Intl.DateTimeFormat resolved timezone passed on booking", "labels": ["backend"]},
                    {"summary": "[Frontend] Calendar weekly view: available (green), booked (grey), blocked (striped) slots", "labels": ["frontend"]},
                    {"summary": "[Frontend] Booking modal: select slot then payment step then confirmation", "labels": ["frontend"]},
                    {"summary": "[Frontend] Timezone label on all time displays e.g. 3:00 PM GST", "labels": ["frontend"]},
                    {"summary": "[QA] Double-booking race condition test (concurrent requests to same slot); DST edge cases", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Booking Confirmation & Reminders",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] Booking created event triggers async: SendGrid confirmation email + Twilio SMS + FCM push (within 60s)", "labels": ["backend"]},
                    {"summary": "[Backend] Scheduled reminder jobs: 24h before (email+SMS+push), 1h before (push only)", "labels": ["backend"]},
                    {"summary": "[Backend] GET /bookings/{id}/export.ics — ICS calendar file generation", "labels": ["backend"]},
                    {"summary": "[Frontend] Confirmation page: session details, Add to Calendar (Google one-click, Outlook ICS, Apple ICS)", "labels": ["frontend"]},
                    {"summary": "[QA] All 3 channels fire on booking; ICS validates in Google Calendar, Outlook, Apple Calendar", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Recurring Bookings & Cancellation Policy",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] POST /bookings with recurrence_rule (weekly, start_date, count/until)", "labels": ["backend"]},
                    {"summary": "[Backend] DELETE /bookings/{id} — single cancellation from series without breaking future slots", "labels": ["backend"]},
                    {"summary": "[Backend] Cancellation policy engine: >48h full refund, 24-48h 50% credit, <24h no refund", "labels": ["backend"]},
                    {"summary": "[Frontend] Recurring booking toggle + end-date/count options in booking flow", "labels": ["frontend"]},
                    {"summary": "[Frontend] Cancellation flow: show refund amount before confirming, confirmation modal", "labels": ["frontend"]},
                    {"summary": "[QA] Cancellation timing boundary tests against PRD policy; recurring series integrity after single cancel", "labels": ["qa"]},
                ],
            },
        ],
    },

    # -----------------------------------------------------------------------
    # KAN-6  Video Sessions (Agora RTC)
    # -----------------------------------------------------------------------
    {
        "key": "KAN-6",
        "stories": [
            {
                "summary": "Agora Session Infrastructure",
                "labels": [],
                "tasks": [
                    {"summary": "[Architect] Agora channel architecture: unique channel ID per session (UUID), short-lived token generation, E2EE via WebRTC insertable streams", "labels": ["architect"]},
                    {"summary": "[Backend] GET /sessions/{id}/agora-token — Agora RTC token, expires 2h from session start", "labels": ["backend"]},
                    {"summary": "[Backend] Session lifecycle state machine: scheduled to in_progress (on join) to completed/interrupted/cancelled", "labels": ["backend"]},
                    {"summary": "[Backend] Recording consent check: both parties must consent; default OFF; consent stored in DB", "labels": ["backend"]},
                    {"summary": "[QA] Token expiry test; state transition tests; recording consent enforcement", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Video Session UX",
                "labels": [],
                "tasks": [
                    {"summary": "[Frontend] Video session page: Agora RTC SDK, local + remote video tiles (720p min), audio controls, mute/unmute", "labels": ["frontend"]},
                    {"summary": "[Frontend] Therapist-controlled waiting room: client sees Your therapist will join shortly until therapist joins", "labels": ["frontend"]},
                    {"summary": "[Frontend] In-session text chat panel (WebSocket, session-scoped, ephemeral — not persisted)", "labels": ["frontend"]},
                    {"summary": "[Frontend] 5-minute end warning: overlay banner with session time remaining", "labels": ["frontend"]},
                    {"summary": "[Frontend] Session extension button (therapist only): +15 min, one per session, requires confirmation", "labels": ["frontend"]},
                    {"summary": "[QA] E2E: join session as client + therapist, text chat, 5-min warning fires, extension flow", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Connection Recovery & Interrupted Sessions",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] Connection drop detection: mark session interrupted if both participants absent >5 min", "labels": ["backend"]},
                    {"summary": "[Backend] Interrupted before 10 min: auto full-credit refund; after 10 min: priority rebooking offer", "labels": ["backend"]},
                    {"summary": "[Frontend] Reconnection UI: Reconnecting overlay, auto-retry for 2 minutes", "labels": ["frontend"]},
                    {"summary": "[Frontend] Interrupted session screen: credit/rebooking notification based on timing", "labels": ["frontend"]},
                    {"summary": "[QA] Simulate drop before 10 min (assert full credit issued); after 10 min (assert rebooking offered, no refund)", "labels": ["qa"]},
                ],
            },
        ],
    },

    # -----------------------------------------------------------------------
    # KAN-7  Mood Tracking
    # -----------------------------------------------------------------------
    {
        "key": "KAN-7",
        "stories": [
            {
                "summary": "Daily Mood Check-In",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] POST /mood-entries — auth required, score 1-10, note (AES-256 encrypted before storage)", "labels": ["backend"]},
                    {"summary": "[Backend] Idempotency: one entry per user per day (upsert by user_id + date)", "labels": ["backend"]},
                    {"summary": "[Backend] FCM push trigger for daily reminder at user-configured time", "labels": ["backend"]},
                    {"summary": "[Frontend] Mood check-in widget: emoji scale (1-10), optional text note field, submit in under 60s", "labels": ["frontend"]},
                    {"summary": "[Frontend] Push notification permission request + time picker for daily reminder (opt-in only)", "labels": ["frontend"]},
                    {"summary": "[QA] Encrypted note in DB (verify ciphertext); idempotency test (second check-in same day updates, not duplicates)", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Mood History & Analytics",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] GET /mood-entries?days=30|90 — decrypted entries for authenticated user only", "labels": ["backend"]},
                    {"summary": "[Frontend] Mood timeline page: area chart with 30/90-day toggle, trend indicator", "labels": ["frontend"]},
                    {"summary": "[Frontend] Entry list below chart: date, emoji score, note (expandable)", "labels": ["frontend"]},
                    {"summary": "[QA] Chart with 0 entries (empty state), 1 entry, 90 entries; data scoped to authenticated user only", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Therapist Mood Sharing Consent",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] PATCH /client-profiles/mood-sharing — toggle therapist access (explicit opt-in, defaults to OFF)", "labels": ["backend"]},
                    {"summary": "[Backend] GET /mood-entries/client/{client_id} for therapists — return 403 without explicit consent", "labels": ["backend"]},
                    {"summary": "[Frontend] Share mood data with therapist toggle in Privacy Settings page", "labels": ["frontend"]},
                    {"summary": "[Frontend] Therapist client dashboard: mood chart section visible only when consent=true", "labels": ["frontend"]},
                    {"summary": "[QA] Without consent: therapist API returns 403; with consent: mood data accessible; revoke consent triggers immediate 403", "labels": ["qa"]},
                ],
            },
        ],
    },

    # -----------------------------------------------------------------------
    # KAN-8  Content Library
    # -----------------------------------------------------------------------
    {
        "key": "KAN-8",
        "stories": [
            {
                "summary": "Content Browsing & Search",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] GET /content — filters: category, format (article/audio/video), language, full-text search (PostgreSQL FTS)", "labels": ["backend"]},
                    {"summary": "[Backend] GET /content/{id} — increment view_count atomically", "labels": ["backend"]},
                    {"summary": "[Frontend] Content library page: card grid with filter sidebar (RTL-compatible), search bar with debounce", "labels": ["frontend"]},
                    {"summary": "[Frontend] Article reader with reading time estimate; audio player (custom controls) for meditations", "labels": ["frontend"]},
                    {"summary": "[Frontend] Language toggle: show AR or EN content based on user preference", "labels": ["frontend"]},
                    {"summary": "[QA] Full-text search relevance (AR+EN); draft content not visible to end users; view_count increments", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Personalized Content Recommendations",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] Personalization scoring: rank by intake category overlap + recent mood trend", "labels": ["backend"]},
                    {"summary": "[Backend] GET /content/recommended — auth required, returns top 10 scored items", "labels": ["backend"]},
                    {"summary": "[Frontend] Recommended for you section on dashboard and content library", "labels": ["frontend"]},
                    {"summary": "[Frontend] Push notification for new relevant content (opt-in, daily digest max)", "labels": ["frontend"]},
                    {"summary": "[QA] Personalization unit tests with synthetic user profiles; verify opt-out respected for push", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Content CMS (Admin)",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] POST /admin/content, PATCH /admin/content/{id}, DELETE /admin/content/{id}", "labels": ["backend"]},
                    {"summary": "[Backend] Status state machine: draft to review to published (only platform_admin can publish)", "labels": ["backend"]},
                    {"summary": "[Backend] GET /admin/content/analytics — views, avg_rating, reads per category", "labels": ["backend"]},
                    {"summary": "[Frontend] Admin content editor: rich-text body, category/language/format tags, media upload to R2", "labels": ["frontend"]},
                    {"summary": "[Frontend] Status workflow UI: draft/review/publish badges, transition buttons with confirmation", "labels": ["frontend"]},
                    {"summary": "[QA] State machine: draft not visible to users; only platform_admin can transition to published", "labels": ["qa"]},
                ],
            },
        ],
    },

    # -----------------------------------------------------------------------
    # KAN-9  Payments & Billing (Tap Payments)
    # -----------------------------------------------------------------------
    {
        "key": "KAN-9",
        "stories": [
            {
                "summary": "Session Payment Flow",
                "labels": [],
                "tasks": [
                    {"summary": "[Architect] Payment architecture: card tokenization via Tap.js (no raw card data on backend), webhook signature verification", "labels": ["architect"]},
                    {"summary": "[Backend] POST /payments/initiate — create Tap charge intent, return payment_url or hosted payment page", "labels": ["backend"]},
                    {"summary": "[Backend] POST /payments/webhook — verify Tap HMAC signature, handle payment.paid/payment.failed events", "labels": ["backend"]},
                    {"summary": "[Backend] Corporate credit path: deduct from corporate_accounts.session_credits_used (atomic transaction)", "labels": ["backend"]},
                    {"summary": "[Frontend] Checkout modal: Tap Payments UI embed (card, mada, Apple Pay, KNET)", "labels": ["frontend"]},
                    {"summary": "[Frontend] Payment success and failure screens with clear next action", "labels": ["frontend"]},
                    {"summary": "[QA] Tap sandbox: success, 3DS, mada, Apple Pay, failure, timeout; webhook signature rejection on tampered payload", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Refunds & Cancellation Credits",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] Refund engine: cancellation event, evaluate timing rule, call Tap refund API or issue platform credit", "labels": ["backend"]},
                    {"summary": "[Backend] Therapist no-show: full refund via Tap + AED 50 platform credit issuance", "labels": ["backend"]},
                    {"summary": "[Backend] Platform credit ledger: credits table (user_id, amount, reason, expires_at)", "labels": ["backend"]},
                    {"summary": "[Frontend] Refund status page in user account: pending/processed status, timeline", "labels": ["frontend"]},
                    {"summary": "[Frontend] Platform credit balance display in account + apply credit at checkout", "labels": ["frontend"]},
                    {"summary": "[QA] All 5 cancellation scenarios from PRD policy table; credit balance applied correctly at next booking", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Therapist Earnings & Payouts",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] GET /therapist/earnings — completed sessions, pending, total_earned, platform_fee (30%), net_payout", "labels": ["backend"]},
                    {"summary": "[Backend] POST /therapist/payout-requests — minimum AED 100 balance, store bank_details_ref", "labels": ["backend"]},
                    {"summary": "[Backend] Monthly earnings PDF generation (WeasyPrint/ReportLab): sessions breakdown, platform fee, net", "labels": ["backend"]},
                    {"summary": "[Frontend] Therapist earnings dashboard: KPI cards (earned, pending, available for payout)", "labels": ["frontend"]},
                    {"summary": "[Frontend] Payout request form: bank transfer details, submit, status tracker (pending/processing/paid)", "labels": ["frontend"]},
                    {"summary": "[Frontend] Download monthly statement PDF button", "labels": ["frontend"]},
                    {"summary": "[QA] 70/30 revenue split accuracy; payout below AED 100 rejected; PDF contains no other therapist data", "labels": ["qa"]},
                ],
            },
        ],
    },

    # -----------------------------------------------------------------------
    # KAN-10  Corporate Portal & EAP
    # -----------------------------------------------------------------------
    {
        "key": "KAN-10",
        "stories": [
            {
                "summary": "Corporate Account & Employee Management",
                "labels": [],
                "tasks": [
                    {"summary": "[Architect] Data model: corporate_accounts to employees (identity isolated from reports), credit pool, HR admin role", "labels": ["architect"]},
                    {"summary": "[Backend] POST /admin/corporate-accounts — platform admin creates company account", "labels": ["backend"]},
                    {"summary": "[Backend] POST /corporate/{id}/employees — CSV upload (email list) + single manual add", "labels": ["backend"]},
                    {"summary": "[Backend] DELETE /corporate/{id}/employees/{user_id} — remove employee access", "labels": ["backend"]},
                    {"summary": "[Frontend] Corporate admin portal: company settings, employee roster table with add/remove", "labels": ["frontend"]},
                    {"summary": "[Frontend] CSV upload UI with row-level validation error display", "labels": ["frontend"]},
                    {"summary": "[QA] CSV with malformed rows (missing email, invalid domain): partial success with error report; employee removal blocks future access", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Session Credit Pool Management",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] Credit deduction: atomic transaction on booking creation (prevent overdraft)", "labels": ["backend"]},
                    {"summary": "[Backend] GET /corporate/{id}/credits — total, used, remaining", "labels": ["backend"]},
                    {"summary": "[Backend] Low-credit alert: FCM/email to HR admin when fewer than 10 credits remaining", "labels": ["backend"]},
                    {"summary": "[Frontend] Credit usage dashboard: total/used/remaining KPI cards, utilization bar", "labels": ["frontend"]},
                    {"summary": "[QA] Concurrent booking test: 2 simultaneous requests for last credit — only 1 succeeds (no overdraft)", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Corporate Employee Onboarding",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] Email domain verification: check user email domain against corporate_accounts allowed domains", "labels": ["backend"]},
                    {"summary": "[Backend] Company code path: alternative to domain verification for companies with multiple domains", "labels": ["backend"]},
                    {"summary": "[Backend] Link user_id to corporate_accounts on first verified login", "labels": ["backend"]},
                    {"summary": "[Frontend] Corporate onboarding page: company code entry field, domain auto-detection", "labels": ["frontend"]},
                    {"summary": "[Frontend] Post-SSO onboarding: standard 5-question intake then standard therapist pool", "labels": ["frontend"]},
                    {"summary": "[QA] E2E: employee enters company code, takes intake, books session, credit deducted from pool", "labels": ["qa"]},
                ],
            },
        ],
    },

    # -----------------------------------------------------------------------
    # KAN-11  SSO Integration
    # -----------------------------------------------------------------------
    {
        "key": "KAN-11",
        "stories": [
            {
                "summary": "Google Workspace OAuth2 SSO",
                "labels": [],
                "tasks": [
                    {"summary": "[Architect] OAuth2 corporate flow: state param + PKCE, email domain to corporate account lookup, no personal Google accounts", "labels": ["architect"]},
                    {"summary": "[Backend] GET /auth/sso/google/authorize — redirect to Google with state param", "labels": ["backend"]},
                    {"summary": "[Backend] GET /auth/sso/google/callback — exchange code, validate domain, upsert employee user, issue platform JWT", "labels": ["backend"]},
                    {"summary": "[Frontend] Sign in with Google Workspace button on corporate login page", "labels": ["frontend"]},
                    {"summary": "[Frontend] Error screen: Your email domain is not registered with any corporate account", "labels": ["frontend"]},
                    {"summary": "[QA] Mock OAuth2 server tests: valid domain, invalid domain, state mismatch, expired code", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Azure AD SAML 2.0 SSO",
                "labels": [],
                "tasks": [
                    {"summary": "[Architect] SAML 2.0 SP design: metadata generation, ACS endpoint, assertion validation (signature, expiry, audience)", "labels": ["architect"]},
                    {"summary": "[Backend] GET /auth/sso/saml/metadata — SP metadata XML for Azure AD configuration", "labels": ["backend"]},
                    {"summary": "[Backend] POST /auth/sso/saml/acs — assertion consumer, validate + parse claims, issue platform JWT", "labels": ["backend"]},
                    {"summary": "[Backend] corporate_accounts.sso_config: store IdP metadata XML (encrypted at rest)", "labels": ["backend"]},
                    {"summary": "[Frontend] Corporate admin SSO config page: upload IdP metadata XML, test connection button", "labels": ["frontend"]},
                    {"summary": "[QA] Mock SAML IdP tests: valid assertion, expired assertion, invalid signature, wrong audience", "labels": ["qa"]},
                ],
            },
        ],
    },

    # -----------------------------------------------------------------------
    # KAN-12  HR Analytics Dashboard
    # -----------------------------------------------------------------------
    {
        "key": "KAN-12",
        "stories": [
            {
                "summary": "Utilization Reports & Anonymization",
                "labels": [],
                "tasks": [
                    {"summary": "[Architect] Anonymization: k-anonymity model (min 5 employees per dept), report contains NO session content or individual identity", "labels": ["architect"]},
                    {"summary": "[Backend] GET /corporate/{id}/reports/utilization — sessions used/remaining, by-dept breakdown with k-anonymity enforcement", "labels": ["backend"]},
                    {"summary": "[Backend] Suppress department rows with fewer than 5 employees (replace with Other bucket)", "labels": ["backend"]},
                    {"summary": "[Frontend] Utilization dashboard: KPI cards (total used, remaining, utilization %), monthly trend chart", "labels": ["frontend"]},
                    {"summary": "[Frontend] Department breakdown table: suppressed depts show fewer than 5 employees label", "labels": ["frontend"]},
                    {"summary": "[Frontend] PDF export for full utilization report", "labels": ["frontend"]},
                    {"summary": "[QA] K-anonymity: dept with 4 employees suppressed; assert response body contains no user IDs or names", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Automated Quarterly Reports",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] Cron job: quarterly report generation (sessions_used, sessions_remaining, dept utilization, trends)", "labels": ["backend"]},
                    {"summary": "[Backend] SendGrid: auto-email PDF report to HR admin email on schedule", "labels": ["backend"]},
                    {"summary": "[Frontend] Report history table: past reports with generated_at date and download link", "labels": ["frontend"]},
                    {"summary": "[QA] Cron test: report generated and email triggered; PDF download link works; report contains no PHI", "labels": ["qa"]},
                ],
            },
        ],
    },

    # -----------------------------------------------------------------------
    # KAN-13  Therapist Portal
    # -----------------------------------------------------------------------
    {
        "key": "KAN-13",
        "stories": [
            {
                "summary": "Availability Calendar Management",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] POST /therapist/availability — set recurring weekly slots (day_of_week, start_time, end_time)", "labels": ["backend"]},
                    {"summary": "[Backend] PATCH /therapist/availability/{id}/block — block specific date/slot without affecting recurrence", "labels": ["backend"]},
                    {"summary": "[Backend] 15-minute buffer enforcement: reject slot overlapping with existing session + 15 min buffer", "labels": ["backend"]},
                    {"summary": "[Backend] Double-booking prevention across all booking entry points (AI agent + calendar UI)", "labels": ["backend"]},
                    {"summary": "[Frontend] Availability calendar UI: weekly view, drag-to-create slots, block-day button", "labels": ["frontend"]},
                    {"summary": "[Frontend] Timezone label on all slots; local time stored, UTC in DB", "labels": ["frontend"]},
                    {"summary": "[QA] 15-min buffer enforced (slot 10:00-11:00 means next allowed at 11:15); double-booking attempt returns 409", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Client Dashboard & Session Notes",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] GET /therapist/clients — paginated list with intake summary, last session date", "labels": ["backend"]},
                    {"summary": "[Backend] POST/GET/PATCH /therapist/session-notes/{session_id} — private notes, therapist-only access", "labels": ["backend"]},
                    {"summary": "[Backend] Secure messaging: WebSocket room per client-therapist pair (in-platform only)", "labels": ["backend"]},
                    {"summary": "[Frontend] Client dashboard: intake answers, session history list, notes editor panel", "labels": ["frontend"]},
                    {"summary": "[Frontend] Session notes: rich-text editor with auto-save draft every 30s", "labels": ["frontend"]},
                    {"summary": "[Frontend] In-platform messaging thread UI per client", "labels": ["frontend"]},
                    {"summary": "[QA] Client cannot read therapist private notes via API (403); messaging room isolated between client pairs", "labels": ["qa"]},
                ],
            },
        ],
    },

    # -----------------------------------------------------------------------
    # KAN-14  Admin Portal & Compliance
    # -----------------------------------------------------------------------
    {
        "key": "KAN-14",
        "stories": [
            {
                "summary": "Therapist Verification Workflow",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] GET /admin/therapist-applications — list with status filter (pending/approved/rejected/info_requested)", "labels": ["backend"]},
                    {"summary": "[Backend] PATCH /admin/therapist-applications/{id} — approve/reject/request_info with email notifications", "labels": ["backend"]},
                    {"summary": "[Backend] Every verification action logged in audit_log: admin_id, action, therapist_id, timestamp", "labels": ["backend"]},
                    {"summary": "[Frontend] Admin verification dashboard: application list, document viewer (R2 signed URLs for license docs)", "labels": ["frontend"]},
                    {"summary": "[Frontend] Approve/reject/request-info modal with required reason text field", "labels": ["frontend"]},
                    {"summary": "[QA] Approval activates therapist account; rejection sends email; all actions in audit log with correct actor_id", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Audit Log & Compliance Reports",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] GET /admin/audit-logs — paginated, filters: actor_id, event_type, resource_type, date range", "labels": ["backend"]},
                    {"summary": "[Backend] DB constraint: audit_log table has no UPDATE/DELETE permissions (append-only enforced)", "labels": ["backend"]},
                    {"summary": "[Backend] Monthly compliance report: PHI access count, crisis escalations count, account deletions count", "labels": ["backend"]},
                    {"summary": "[Frontend] Audit log viewer: sortable table, filter panel, CSV export", "labels": ["frontend"]},
                    {"summary": "[Frontend] Compliance report page: summary tiles + downloadable PDF", "labels": ["frontend"]},
                    {"summary": "[QA] Attempt UPDATE on audit_log row returns DB error; filter accuracy; CSV export integrity", "labels": ["qa"]},
                ],
            },
        ],
    },

    # -----------------------------------------------------------------------
    # KAN-15  Crisis Detection & Safety
    # -----------------------------------------------------------------------
    {
        "key": "KAN-15",
        "stories": [
            {
                "summary": "Crisis Detection Pipeline",
                "labels": [],
                "tasks": [
                    {"summary": "[AI Engineer] Layer 1: regex keyword matcher (Arabic + English crisis phrases, runs in under 5ms, synchronous)", "labels": ["ai-engineer"]},
                    {"summary": "[AI Engineer] Layer 2: Claude prompt for semantic risk classification returning structured JSON with risk_level, signals, confidence", "labels": ["ai-engineer"]},
                    {"summary": "[AI Engineer] Layer 1 short-circuits to Layer 2 only when keywords detected (performance optimization)", "labels": ["ai-engineer"]},
                    {"summary": "[Backend] CrisisDetectionService: injected as FastAPI dependency in companion route, no async HTTP hop", "labels": ["backend"]},
                    {"summary": "[Backend] Country detection: user timezone mapped to UAE/KSA/Kuwait/Bahrain emergency numbers", "labels": ["backend"]},
                    {"summary": "[QA] 200+ unit test phrases (AR+EN) for keyword layer; integration test: Layer 2 invoked only when Layer 1 triggers", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Crisis Response & Therapist Escalation",
                "labels": [],
                "tasks": [
                    {"summary": "[AI Engineer] High-risk response template: emergency numbers, helplines, You are not alone message (AR+EN)", "labels": ["ai-engineer"]},
                    {"summary": "[Backend] High-risk: AI response replaced unconditionally with crisis protocol output", "labels": ["backend"]},
                    {"summary": "[Backend] Therapist alert: create urgent notification for assigned therapist (delivered within 5 min SLA)", "labels": ["backend"]},
                    {"summary": "[Backend] Crisis event creation before response is returned (synchronous, not fire-and-forget)", "labels": ["backend"]},
                    {"summary": "[Frontend] High-risk overlay: full-screen modal, cannot dismiss with single tap (requires confirmation), Call now tel links", "labels": ["frontend"]},
                    {"summary": "[Frontend] Medium-risk sticky banner: above chat, Talk to someone now leads to emergency session booking", "labels": ["frontend"]},
                    {"summary": "[QA] E2E: high-risk message triggers overlay + crisis event in DB + therapist notification — all within single request cycle", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Crisis Event Logging & Retention",
                "labels": [],
                "tasks": [
                    {"summary": "[Architect] Crisis log access control: separate safety_officer sub-role, platform_admin (non-officer) gets 403 on crisis log reads", "labels": ["architect"]},
                    {"summary": "[Backend] crisis_events schema: user_id, conversation_id, risk_level, trigger_signals (JSONB), platform_response, therapist_notified, logged_at", "labels": ["backend"]},
                    {"summary": "[Backend] 7-year retention: soft-delete blocked on crisis_events; hard-delete requires safety_officer + legal approval workflow", "labels": ["backend"]},
                    {"summary": "[QA] Every risk level creates crisis event; platform_admin (non-officer) gets 403; verify retention policy enforced at API level", "labels": ["qa"]},
                ],
            },
        ],
    },

    # -----------------------------------------------------------------------
    # KAN-16  AI Services & Abstraction Layer
    # -----------------------------------------------------------------------
    {
        "key": "KAN-16",
        "stories": [
            {
                "summary": "AI Provider Abstraction Layer",
                "labels": [],
                "tasks": [
                    {"summary": "[AI Engineer] Abstract base class: AIProvider with generate(prompt), chat(messages), embed(text) interface methods", "labels": ["ai-engineer"]},
                    {"summary": "[AI Engineer] AnthropicAdapter: Claude API, streaming support, token counting, system prompt injection", "labels": ["ai-engineer"]},
                    {"summary": "[AI Engineer] OpenAIAdapter: GPT-4o, same interface, used as automatic fallback", "labels": ["ai-engineer"]},
                    {"summary": "[AI Engineer] Rate limit detector: catch 429 and switch to fallback provider transparently", "labels": ["ai-engineer"]},
                    {"summary": "[AI Engineer] Prompt template manager: versioned templates per feature (companion_v1, booking_v1, etc.), no hardcoded prompts in route handlers", "labels": ["ai-engineer"]},
                    {"summary": "[Backend] Provider factory: get_ai_provider() FastAPI dependency reads AI_PROVIDER env var", "labels": ["backend"]},
                    {"summary": "[Backend] PHI safety: user IDs anonymized in all prompts (UUID only, no names/emails sent to AI)", "labels": ["backend"]},
                    {"summary": "[QA] Swap AI_PROVIDER=openai via env var without code change; fallback triggers on mocked 429; no PII in prompt strings", "labels": ["qa"]},
                ],
            },
            {
                "summary": "AI Booking Agent Implementation",
                "labels": [],
                "tasks": [
                    {"summary": "[AI Engineer] Booking agent prompt: tool-calling schema for query_availability, create_booking, confirm_booking", "labels": ["ai-engineer"]},
                    {"summary": "[AI Engineer] Arabic date/time NLU: next Tuesday evening maps to structured date/time/week object", "labels": ["ai-engineer"]},
                    {"summary": "[AI Engineer] Clarification loop: ask specific questions when intent is ambiguous (under 3 turns before fallback)", "labels": ["ai-engineer"]},
                    {"summary": "[Backend] POST /booking-agent/chat — tool call handler executes real DB queries, returns structured tool results to AI", "labels": ["backend"]},
                    {"summary": "[Frontend] Booking agent chat interface: minimal, conversational, shows confirmation card before final commit", "labels": ["frontend"]},
                    {"summary": "[QA] 15+ booking scenarios: specific therapist, next available, evening preference, Arabic input, 3-attempt fallback", "labels": ["qa"]},
                ],
            },
            {
                "summary": "AI Customer Support Agent",
                "labels": [],
                "tasks": [
                    {"summary": "[AI Engineer] Support agent prompt: knowledge base (FAQ, pricing, cancellation policy, therapist application steps)", "labels": ["ai-engineer"]},
                    {"summary": "[AI Engineer] Confidence threshold: if below 0.7 escalate to human support ticket", "labels": ["ai-engineer"]},
                    {"summary": "[AI Engineer] Scope guardrails: no clinical advice, no specific therapist recommendations in support context", "labels": ["ai-engineer"]},
                    {"summary": "[Backend] POST /support/chat — message handler with confidence-based human handoff", "labels": ["backend"]},
                    {"summary": "[Backend] POST /support/tickets — create ticket on handoff with conversation transcript (no PHI in ticket summary)", "labels": ["backend"]},
                    {"summary": "[Frontend] Support chat widget: floating bottom-right, accessible from all pages, minimizable", "labels": ["frontend"]},
                    {"summary": "[QA] 20+ support scenarios (billing, cancellation, account, therapist application); human handoff triggers correctly; ticket created without PHI", "labels": ["qa"]},
                ],
            },
        ],
    },

    # -----------------------------------------------------------------------
    # KAN-17  Notifications & Integrations
    # -----------------------------------------------------------------------
    {
        "key": "KAN-17",
        "stories": [
            {
                "summary": "Email & SMS (SendGrid + Twilio)",
                "labels": [],
                "tasks": [
                    {"summary": "[Architect] Notification service: event-driven async queue, provider-agnostic interface (swap SendGrid to SES with env var)", "labels": ["architect"]},
                    {"summary": "[Backend] SendGrid: transactional email templates (booking confirmation, 24h/1h reminder, payout statement, welcome)", "labels": ["backend"]},
                    {"summary": "[Backend] Twilio SMS: session reminders (24h), OTP, crisis-related alerts to safety officer", "labels": ["backend"]},
                    {"summary": "[Backend] NotificationPreferences model: per-user per-channel opt-out, respected by all send functions", "labels": ["backend"]},
                    {"summary": "[Frontend] Notification preferences page: toggle per channel (email/SMS/push) per event type", "labels": ["frontend"]},
                    {"summary": "[QA] All triggers fire correct channel; opt-out respected; no PHI in notification payloads", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Push Notifications (Firebase FCM)",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] Firebase Admin SDK: send_multicast to registered device tokens per user", "labels": ["backend"]},
                    {"summary": "[Backend] POST /users/push-tokens — register device token for authenticated user", "labels": ["backend"]},
                    {"summary": "[Backend] Push triggers: booking confirmation, 1h reminder, new recommended content, therapist alert on medium/high crisis", "labels": ["backend"]},
                    {"summary": "[Frontend] Push permission request prompt (PWA service worker registration)", "labels": ["frontend"]},
                    {"summary": "[Frontend] In-app notification bell with unread count badge", "labels": ["frontend"]},
                    {"summary": "[QA] Push delivery test in PWA context; unread count increments; permission-denied fallback to email", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Calendar Integrations",
                "labels": [],
                "tasks": [
                    {"summary": "[Backend] ICS generation: RFC 5545 compliant calendar file for any booking", "labels": ["backend"]},
                    {"summary": "[Backend] Google Calendar OAuth2 flow: /calendar/google/authorize to /calendar/google/callback to create event", "labels": ["backend"]},
                    {"summary": "[Frontend] Add to Calendar component: Google one-click OAuth, Outlook download ICS, Apple Calendar download ICS", "labels": ["frontend"]},
                    {"summary": "[QA] ICS validates in Google Calendar, Outlook, Apple Calendar; Google OAuth creates event in user calendar", "labels": ["qa"]},
                ],
            },
        ],
    },

    # -----------------------------------------------------------------------
    # KAN-18  Infrastructure & DevOps
    # -----------------------------------------------------------------------
    {
        "key": "KAN-18",
        "stories": [
            {
                "summary": "Docker & Local Dev Environment",
                "labels": [],
                "tasks": [
                    {"summary": "[Architect] FastAPI Dockerfile: multi-stage (build + runtime), non-root user, EXPOSE 8000, HEALTHCHECK", "labels": ["architect"]},
                    {"summary": "[Architect] Next.js Dockerfile: multi-stage, output standalone in next.config.js, non-root user", "labels": ["architect"]},
                    {"summary": "[Architect] docker-compose.yml: postgres:16, redis:7, backend, frontend with volume mounts and env_file", "labels": ["architect"]},
                    {"summary": "[Architect] .env.example: all required vars documented (DATABASE_URL, AI_PROVIDER, AGORA_APP_ID, TAP_SECRET_KEY, SENDGRID_API_KEY, TWILIO_AUTH_TOKEN, FCM_CREDENTIALS, CLOUDFLARE_R2_KEY)", "labels": ["architect"]},
                    {"summary": "[QA] docker-compose up: all 4 services healthy; backend /health returns 200; frontend serves home page", "labels": ["qa"]},
                ],
            },
            {
                "summary": "GitHub Actions CI/CD Pipeline",
                "labels": [],
                "tasks": [
                    {"summary": "[Architect] Workflow file: lint (Ruff + ESLint) then pytest unit then pytest integration then Docker build", "labels": ["architect"]},
                    {"summary": "[Architect] Staging deploy job: deploy to Render staging + run Cypress E2E then notify on failure", "labels": ["architect"]},
                    {"summary": "[Architect] Production deploy job: manual approval gate (GitHub Environments) then deploy to Render + Vercel prod", "labels": ["architect"]},
                    {"summary": "[Architect] validate-env.sh: fail pipeline if any required env var is unset before deploy step", "labels": ["architect"]},
                    {"summary": "[Architect] check-phi-leaks.sh: scan log output and source for PHI patterns (email regex, phone regex, name fields), fail CI on match", "labels": ["architect"]},
                    {"summary": "[QA] Verify manual approval gate blocks auto-deploy to prod; Cypress E2E runs against staging after each staging deploy", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Production Deployment (Vercel + Render)",
                "labels": [],
                "tasks": [
                    {"summary": "[Architect] vercel.json: Next.js framework, env vars config, domain redirect (www to apex or vice versa)", "labels": ["architect"]},
                    {"summary": "[Architect] Render services: FastAPI web service (Docker), managed PostgreSQL 16, managed Redis 7", "labels": ["architect"]},
                    {"summary": "[Architect] Cloudflare R2: bucket creation, CORS config, signed URL generation for private assets (license docs)", "labels": ["architect"]},
                    {"summary": "[Architect] Environment variable management: staging vs prod separation in Render + Vercel dashboards", "labels": ["architect"]},
                    {"summary": "[QA] Staging smoke test: /health, /auth/register, /therapists, /content all respond correctly; R2 signed URL access works", "labels": ["qa"]},
                ],
            },
            {
                "summary": "Monitoring, Alerting & Scaling",
                "labels": [],
                "tasks": [
                    {"summary": "[Architect] Sentry: Next.js client + server, FastAPI — scrub PHI from error payloads before send", "labels": ["architect"]},
                    {"summary": "[Architect] PostHog: anonymized events (session_booked, companion_message_sent, crisis_detected) — no user PII in event props", "labels": ["architect"]},
                    {"summary": "[Architect] Better Uptime: monitors for frontend, backend /health, Agora webhook endpoint", "labels": ["architect"]},
                    {"summary": "[Architect] PagerDuty: P0 alerts (service down >2 min, crisis detection service failure)", "labels": ["architect"]},
                    {"summary": "[Architect] Render scaling config: scale-out trigger at >70% CPU for 2 min; pre-warm 30 min before peak hours (6PM-9PM GST)", "labels": ["architect"]},
                    {"summary": "[QA] k6 load test: 500 concurrent users simulating session booking flow; assert API P99 under 500ms; no errors above 1%", "labels": ["qa"]},
                ],
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Fetching Jira issue type IDs...")
    type_ids = get_issue_type_ids()

    story_type_id = type_ids.get("Story")
    task_type_id = type_ids.get("Task")

    if not story_type_id or not task_type_id:
        print(f"ERROR: Could not find Story or Task issue type IDs. Available: {list(type_ids.keys())}")
        sys.exit(1)

    print(f"Story type ID: {story_type_id}  |  Task type ID: {task_type_id}")
    print()

    total_stories = 0
    total_tasks = 0
    errors = 0

    for epic in EPICS:
        epic_key = epic["key"]
        print(f"\n{'='*70}")
        print(f"Epic: {epic_key}")
        print(f"{'='*70}")

        for story_data in epic["stories"]:
            print(f"\n  Story: {story_data['summary']}")
            story_key = create_issue(
                summary=story_data["summary"],
                issue_type_id=story_type_id,
                parent_key=epic_key,
                labels=story_data.get("labels", []),
            )
            time.sleep(DELAY_BETWEEN_CALLS)

            if not story_key:
                errors += 1
                print(f"  SKIPPING tasks for failed story.")
                continue

            total_stories += 1

            for task_data in story_data["tasks"]:
                task_key = create_issue(
                    summary=task_data["summary"],
                    issue_type_id=task_type_id,
                    parent_key=story_key,
                    labels=task_data.get("labels", []),
                )
                time.sleep(DELAY_BETWEEN_CALLS)
                if task_key:
                    total_tasks += 1
                else:
                    errors += 1

    print(f"\n{'='*70}")
    print(f"DONE")
    print(f"  Stories created : {total_stories}")
    print(f"  Tasks created   : {total_tasks}")
    print(f"  Errors          : {errors}")
    print(f"  Total tickets   : {total_stories + total_tasks}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
