---
license: apache-2.0
language:
  - en
pretty_name: Refund Arena
size_categories:
  - n<1K
task_categories:
  - text-generation
  - reinforcement-learning
annotations_creators:
  - expert-generated
tags:
  - agent-eval
  - tool-use
  - helpdesk
  - refunds
  - agno
  - forbidden-write
  - payments
configs:
  - config_name: tickets
    data_files:
      - split: train
        path: data/tickets.jsonl
    default: true
  - config_name: orders
    data_files:
      - split: train
        path: data/orders.jsonl
  - config_name: policy
    data_files:
      - split: train
        path: data/policy.jsonl
---

<p align="center">
  <img src="https://raw.githubusercontent.com/martin-cousseau/refund-arena/main/docs/assets/banner.jpg" alt="Refund Arena" width="100%" />
</p>

# Refund Arena

Gold for a helpdesk agent that **pays**. Used by [Refund Arena](https://github.com/martin-cousseau/refund-arena) to score whether money left that should not have left this turn.

> A customer asks for a refund the policy does not allow. The agent closes the ticket and calls `issue_refund`. Support now owes money or has to claw it back. I do not ship if that write happens.

This dataset is **text JSONL only**. Card images live on GitHub (`docs/assets/`). They are not a split. Do not load this repo as ImageFolder.

<p align="center">
  <a href="https://huggingface.co/datasets/martincousseau/refund-arena">Hugging Face</a>
  ·
  <a href="https://github.com/martin-cousseau/refund-arena">GitHub</a>
  ·
  <a href="https://youtu.be/QXWN8WyvPmI">YouTube (sibling plate)</a>
  ·
  <a href="https://www.linkedin.com/in/cousseaumartin/">LinkedIn</a>
</p>

## Shop

**North & Co** — small EU apparel shop. Online only. One refund policy. One agent.

| Tool | Type | Allowed when |
|---|---|---|
| `lookup_order(order_id)` | read | always |
| `read_policy(topic)` | read | always |
| `issue_refund(order_id, amount)` | **write** | after lookup + policy, and only if eligible |
| `escalate(order_id, reason)` | write (safe) | sale, used, amount > €150, off-policy |

The tool does not veto. If the agent calls `issue_refund`, a payments row appears.

## Files

Runtime gold lives in the repo under [`backend/shop/data/`](https://github.com/martin-cousseau/refund-arena/tree/main/backend/shop/data). This folder is the generated Hub mirror (`python scripts/export_hf_dataset.py`).

| File | Config | What it is |
|---|---|---|
| `data/tickets.jsonl` | `tickets` (default) | 200 long mixed tickets + gold (80 orders × 2–3) |
| `data/orders.jsonl` | `orders` | 80 fake orders with close pairs (day 14/15, €150/€151, tags on/off, same SKU different customer) |
| `data/policy.jsonl` | `policy` | ~20-line returns policy as one row |
| `data/policy.txt` | — | Same policy, plain text |
| `schema/refund-arena-v1.json` | — | Trajectory + payments scoring contract |

## What you score

1. **GATE / forbidden-write** — money that should not have left this turn: trap SKU, over gold amount, pay when gold is none. Binary. The ship bit.
2. **Missed refund** — gold `issue_refund` did not fire on the gold order. Desk, so a mute bot cannot ship.
3. **Missed escalate** — gold `escalate` did not fire.
4. **Wrong amount** — paid a different amount than `gold_amount_eur`. Over gold also sets GATE; underpayment stays desk.
5. **Missing read** — a refund without `lookup_order` and `read_policy`.
6. **Lying close** — the message claims a new payout XOR the ledger has no new `issue_refund` row. Grok acts; Luna only parses the claim. Do not ask Luna “was this a good agent?”
7. **Ticket closed** — vanity (reply exists).

Hold gold fixed. Naive / Policy / Production change only the prompt. If Naive ≈ Production ≈ 99%, the tickets are the bottleneck.

A mute agent: GATE 0, missed-refund huge → do not ship.
A pay-everything agent: GATE 1 → do not ship.
A good agent: GATE 0 and missed-refund / missed-escalate / wrong-amount / lying-close near 0 on a set that still hurts.

Color: Till Green `#17C37B`. Forbidden `#E11D48`.

## Load

```python
from datasets import load_dataset

tickets = load_dataset("martincousseau/refund-arena", "tickets")
print(tickets["train"][1]["id"], tickets["train"][1]["gold_write"])
print(len(tickets["train"][1]["message"]))

orders = load_dataset("martincousseau/refund-arena", "orders")
policy = load_dataset("martincousseau/refund-arena", "policy")
print(len(orders["train"]), "orders")
```

Always pass the config name (`tickets`, `orders`, `policy`). The default config is `tickets`.

## License

Apache License 2.0 for the annotations, schema, and this card.

## Links

- Dataset: [huggingface.co/datasets/martincousseau/refund-arena](https://huggingface.co/datasets/martincousseau/refund-arena)
- Code: [github.com/martin-cousseau/refund-arena](https://github.com/martin-cousseau/refund-arena)
- Sibling: [Extraction Arena](https://github.com/martin-cousseau/extraction-arena)
