## Summary

<!-- One sentence: what does this PR do and why? -->
<!-- Reference the Jira ticket: Closes KAN-XX -->

## Type of Change

- [ ] `feat` — new feature
- [ ] `fix` — bug fix
- [ ] `refactor` — code change with no feature/fix
- [ ] `test` — adding or updating tests
- [ ] `chore` — dependency updates, config, tooling
- [ ] `docs` — documentation only
- [ ] `ci` — CI/CD changes

## Testing

- [ ] Unit tests added / updated and passing (`just test`)
- [ ] Integration tests passing
- [ ] If crisis-related (KAN-26, KAN-58, KAN-59): red-team suite passes (`just red-team`)
- [ ] Manual smoke test performed locally

## PHI / Security

- [ ] No PHI fields are logged or returned in unencrypted form
- [ ] PHI leak check passes (`bash scripts/check-phi-leaks.sh`)
- [ ] No secrets or API keys committed
- [ ] OWASP Top 10 considered for any new endpoints

## Checklist

- [ ] PR title follows Conventional Commits format (`type(scope): subject`)
- [ ] Branch name references the Jira ticket (`feature/KAN-XX-...`)
- [ ] CI is green (lint + tests + build)
- [ ] Self-reviewed — no debug prints, commented-out code, or TODOs left in
- [ ] Breaking changes documented in commit body (if any)

## Screenshots / Recordings

<!-- For UI changes: before/after screenshots or a short screen recording -->

## Notes for Reviewer

<!-- Anything the reviewer should pay special attention to? -->
