# Codex Prompt：实现库存 Ledger 服务

```text
Read AGENTS.md and docs/decisions/ADR-0002-ledger-inventory.md.

Implement InventoryService.

Requirements:
- create_bottle_with_purchase_in
- move_bottle
- drink_bottle
- gift_bottle
- sell_bottle
- mark_damaged
- stocktake_adjustment
- Each method must create an InventoryTransaction.
- Each method must update Bottle.current_status and Bottle.current_location_id consistently.
- Add tests for every state transition.
- Prevent invalid transitions, e.g. moving a bottle that is already drunk.

Do not implement UI.
```
