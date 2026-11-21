# Public repository maintenance policy

Repository: https://github.com/amor-purus/PC-Context-Builder

## Privacy before publication

This repository is intentionally public. Never commit real computer inventory,
`PC_Context_Pack_*.zip`, CSV exports, logs, raw diagnostic traces, local
profiles, screenshots containing identifying metadata or credentials.

Use synthetic data only in tests, examples and GitHub Actions. Inspect the
Git history as well as the current tree when evaluating disclosure risks.

## Atomic release procedure

1. Prepare the *complete* change set in a candidate branch or unreferenced
   Git object, without changing `main`.
2. Require all Windows CI jobs including frozen-EXE self-test to succeed.
3. Move `main` in one commit to the validated tree. No intermediate or
   partially completed feature set may appear on `main`.
4. The release workflow tests that exact main SHA again, creates a DRAFT
   GitHub Release, attaches all verified assets, checks their count and
   SHA-256, and only then publishes the release.
5. If any check fails, do not make the release public. Correct the candidate
   and run the whole verification gate again. Existing releases remain usable.

The application uses MIT License. A Public repository is not a waiver
of the license attribution requirements.

## Local clone

```powershell
git remote set-url origin https://github.com/amor-purus/PC-Context-Builder.git
git remote -v
```
