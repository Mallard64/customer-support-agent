"""A 4-step customer support agent: classify -> decide (policy) -> draft reply -> tone check.

  export OPENAI_API_KEY=...
  python agent.py "My earbuds from order A1001 are still in the box. Can I get my money back?"

Each step's system prompt lives in prompts/<step>.txt (one instruction per line); each step's model and
sampling settings live in config.yml. The order and policy lookups are fake and read data/*.json.
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

HERE = Path(__file__).parent
STEPS = ["classify", "decide", "draft", "tone"]
TODAY = "2026-10-06"  # fixed so the tools give the same answer every time
ORDERS = json.loads((HERE / "data" / "orders.json").read_text())
POLICIES = json.loads((HERE / "data" / "policies.json").read_text())


def prompt(step):
    return (HERE / "prompts" / f"{step}.txt").read_text().strip()


def config():
    return yaml.safe_load((HERE / "config.yml").read_text())["steps"]


def days_between(a, b):
    return (datetime.fromisoformat(b) - datetime.fromisoformat(a)).days


def lookup_order(order_id):
    """Order record with day counts worked out, so the model never does date arithmetic."""
    o = ORDERS.get((order_id or "").strip().upper())
    if o is None:
        return None
    rec = {"order_id": order_id.strip().upper(), **o}
    if "delivered" in o:
        rec["days_since_delivery"] = days_between(o["delivered"], TODAY)
    if "estimated_delivery" in o:
        rec["days_past_estimated_delivery"] = max(0, days_between(o["estimated_delivery"], TODAY))
    return rec


def lookup_policy(category):
    return POLICIES.get(category, POLICIES["other"])


def parse_json(raw):
    m = re.search(r"\{.*\}", raw or "", re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None


def user_message(step, ctx):
    t = ctx["ticket"]
    if step == "classify":
        return f"Ticket:\n{t}"
    if step == "decide":
        order = json.dumps(ctx["order"]) if ctx["order"] else "none found"
        return (f"Ticket:\n{t}\n\nCategory: {ctx['category']}\n\nPolicy {ctx['policy']['policy_id']}:\n"
                f"{ctx['policy']['text']}\n\nOrder record: {order}")
    if step == "draft":
        order = json.dumps(ctx["order"]) if ctx["order"] else "none"
        return f"Ticket:\n{t}\n\nDecision: {json.dumps(ctx['decision'])}\n\nOrder record: {order}"
    return f"Ticket:\n{t}\n\nDecision: {json.dumps(ctx['decision'])}\n\nDraft reply:\n{ctx['draft']}"


def call(model, settings, system, user):
    from openai import OpenAI
    params = {k: v for k, v in settings.items() if k != "model"}
    r = OpenAI().chat.completions.create(model=model, messages=[{"role": "system", "content": system},
                                                                {"role": "user", "content": user}], **params)
    return r.choices[0].message.content or ""


def run(ticket, llm=call):
    """Run all four steps; returns the final reply and what each step decided."""
    cfg, ctx = config(), {"ticket": ticket}
    for step in STEPS:
        raw = llm(cfg[step]["model"], cfg[step], prompt(step), user_message(step, ctx))
        if step == "classify":
            out = parse_json(raw) or {}
            ctx.update(category=out.get("category"), order_id=out.get("order_id"))
            ctx["order"], ctx["policy"] = lookup_order(ctx["order_id"]), lookup_policy(ctx["category"])
        elif step == "decide":
            ctx["decision"] = parse_json(raw) or {"action": None}
        elif step == "draft":
            ctx["draft"] = raw.strip()
        else:
            out = parse_json(raw) or {}
            revised = out.get("verdict") == "REVISED" and out.get("final_reply")
            ctx["final_reply"] = out["final_reply"].strip() if revised else ctx["draft"]
    return {k: ctx.get(k) for k in ("category", "order_id", "decision", "final_reply")}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('usage: python agent.py "ticket text"')
    print(json.dumps(run(sys.argv[1]), indent=2))
