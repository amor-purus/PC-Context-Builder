# GitHub repository setup

The product is **PC Context Builder**, and the GitHub repository is currently named `PC-Context-Builder`.

- Keep the repository private until the complete history, CI logs, and release assets have been audited for sensitive information.
- Do not commit any real `PC_Context_Pack_*.zip` or legacy `AI_PC_Knowledge_Pack_*.zip` export.
- Do not commit screenshots, local scan reports, user logs, credentials, tokens, or personal file lists.
- The project is released under the MIT License. Keep the `LICENSE` file in source archives and redistributions.
- Use the Windows Actions workflow for repeatable syntax and built-in self-test checks. CI does not replace testing on the target PC.

After the GitHub repository is renamed to `PC-Context-Builder`, update existing local clones with:

```powershell
git remote set-url origin https://github.com/yanchengz685-bot/PC-Context-Builder.git
git remote -v
```

GitHub documents automatic redirects for most repository links and Git operations after a rename. Existing local clones should still be updated to the new remote URL.
