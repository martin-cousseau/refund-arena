# Resolvd case book

This folder is the eval book for Resolvd. The live desk still loads `backend/shop/data/tickets.json`, the North & Co plate (200 emails, 14-day window, €150 cap). Nothing here replaces that file.

`fixture.json` is the stub shop. Order `id` is what a refund is charged to. Order `name` (`#1101`) is what an inbound `orderId` of `1101` or `#1101` resolves to. `cara@shop.test` has no orders. Emails match exactly, after trim. `REFUND_AUTO_LIMIT` is 50 USD. `gold_amount_eur` stores that dollar figure so the existing scorer can compare amounts. The manifest records the unit.

`cases.json` is built by `scripts/build_resolvd_cases.py` and checked by `scripts/validate_resolvd_book.py`. Policy rows take their gold from `shop/resolvd_oracle.py` (heuristic triage, then decide, then order resolve). Gap rows are the catches: injection, already-refunded orders, conflicting dollar amounts, and a second turn that is itself a legal auto-refund. Those ids are `manifest.json` `divergences`.

`demo_ids` is the 15-ticket tape: clears on the limit, email match, a missing order id, fury, a complaint, a status lookup, and a disconnected store; catches on injection, a second refund, a follow-up cave, and two conflicting amounts.

Customer text does not mention the eval, and it does not name North & Co tools. Regenerating after a limit change is `python scripts/build_resolvd_cases.py` from the repo root, then the validator.
