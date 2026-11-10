# GitHub repository setup

The product and GitHub repository are named **PC Context Builder** and `PC-Context-Builder`. The repository is Private.

- Keep the repository private until the complete history, CI logs, and release assets have been audited for sensitive information.
- Do not commit any real `PC_Context_Pack_*.zip` or legacy `AI_PC_Knowledge_Pack_*.zip` export.
- Do not commit screenshots, local scan reports, user logs, credentials, tokens, or personal file lists.
- The repository uses the MIT License; retain `LICENSE` in redistributed copies.
- Use the Windows Actions workflow for repeatable syntax and built-in self-test checks. CI does not replace testing on the target PC.

Existing local clones should use the repository URL below:

```powershell
git remote set-url origin https://github.com/yanchengz685-bot/PC-Context-Builder.git
git remote -v
```

GitHub documents automatic redirects for most repository links and Git operations after a rename. Existing local clones should still be updated to the new remote URL.
