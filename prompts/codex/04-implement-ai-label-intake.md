# Codex Prompt：实现酒标识别草稿流程

```text
Read AGENTS.md, docs/05-ux-flows.md, and docs/09-compliance-data-policy.md.

Implement only the draft workflow for label-image intake.

Requirements:
- Upload image to local media directory.
- Create an IntakeDraft record with extracted fields as nullable draft data.
- The draft must include source, confidence, raw_text/raw_json if available.
- The draft must not create Bottle, Wine, Vintage, or InventoryTransaction until user confirmation.
- Add confirm/reject endpoints.
- On confirm, use existing inventory service to create records.

Do not connect to a real AI provider yet unless explicitly asked.
Use a mock extractor interface so provider can be plugged in later.
```
