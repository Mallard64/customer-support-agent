# Customer support agent

A small 4-step support agent for an online store. It reads a customer ticket and writes the reply:

1. **classify**: what the ticket is about (refund, damaged, shipping, cancel, billing, account, other) and the order ID
2. **decide**: what the store will do, using the store policy and the order record
3. **draft**: the customer-facing reply
4. **tone**: a final check that the reply is polite and promises nothing extra

Each step has its own prompt in `prompts/<step>.txt` (one instruction per line) and its own model in `config.yml`.
The order and policy lookups are fake and read `data/orders.json` and `data/policies.json`, so runs are repeatable.

This repo is the example app used by [upshift](https://github.com/Mallard64/upshift): it runs on `gpt-4`, which
OpenAI shuts down on Oct 23, 2026, and upshift opens the pull request that moves it to a new model.

## Run it

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
python agent.py "My earbuds from order A1001 are still in the box. Can I get my money back?"
```

## Test it (no API key needed)

```bash
python -m unittest discover tests
```
