# GitHub repository setup

The product is **PC Context Builder**, and the GitHub repository is currently named `PC-Context-Builder`.

- Keep the repository private until the complete history, CI logs, and release assets have been audited for sensitive information.
- Do not commit any real `PC_Context_Pack_*.zip` or legacy `AI_PC_Knowledge_Pack_*.zip` export.
- Do not commit screenshots, local scan reports, user logs, credentials, tokens, or personal file lists.
- The project is released under the MIT License. Keep the `LICENSE` file in source archives and redistributions.
- Use the Windows Actions workflow for repeatable syntax and built-in self-test checks. CI does not replace testing on the target PC.

For local clones that still point to the former repository URL, update the remote with:

```powershell
git remote set-url origin https://github.com/yanchengz685-bot/PC-Context-Builder.git
git remote -v
```

The repository is already named `PC-Context-Builder`; the command above normalizes older local clones to the current URL.
