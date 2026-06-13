# Codex Prompt：代码审查清单

```text
Review the current changes against AGENTS.md and the docs.

Focus on:
- Inventory changes must go through InventoryService.
- No direct stock mutation without transaction.
- No unauthorized scraping or hidden network behavior.
- No committed secrets or private data.
- AI output must remain draft until confirmation.
- Data model must keep Wine, Vintage, Bottle separate.
- Tests must cover important state transitions.
- README must include run and test commands.

Return issues by severity: P0, P1, P2, P3.
```
