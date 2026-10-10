"""Offline tests: the fake tools and the pipeline wiring (no API key needed)."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import agent  # noqa: E402


class Tools(unittest.TestCase):
    def test_order_lookup_counts_days_and_ignores_case(self):
        o = agent.lookup_order("a1001")
        self.assertEqual((o["order_id"], o["days_since_delivery"]), ("A1001", 16))

    def test_unknown_order_and_category(self):
        self.assertIsNone(agent.lookup_order("A9999"))
        self.assertEqual(agent.lookup_policy("nonsense")["policy_id"], "GENERAL-07")

    def test_every_step_has_a_prompt_and_a_model(self):
        cfg = agent.config()
        for step in agent.STEPS:
            self.assertTrue(agent.prompt(step))
            self.assertIn("model", cfg[step])


class Pipeline(unittest.TestCase):
    def test_runs_all_four_steps_in_order(self):
        seen = []
        replies = {"classify": '{"category": "refund", "order_id": "A1001"}',
                   "decide": '{"action": "refund", "policy_id": "REFUND-01", "amount": 79.0, "reason": "unused"}',
                   "draft": "Your refund of $79.00 for order A1001 is on its way.",
                   "tone": '{"verdict": "PASS", "issues": [], "final_reply": null}'}

        def fake(model, settings, system, user):
            step = agent.STEPS[len(seen)]
            seen.append(step)
            return replies[step]

        out = agent.run("Earbuds from A1001, still in the box. Refund please.", llm=fake)
        self.assertEqual(seen, agent.STEPS)
        self.assertEqual((out["category"], out["decision"]["action"]), ("refund", "refund"))
        self.assertEqual(out["final_reply"], replies["draft"])


if __name__ == "__main__":
    unittest.main()
