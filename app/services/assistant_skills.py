"""Small, product-owned skill registry for the copilot.

Skills are selected per request and injected only for that run. This keeps
domain guidance modular without introducing a heavyweight agent framework or
letting the model invent its own permissions.
"""
from __future__ import annotations


SKILLS: dict[str, str] = {
    "workforce_analysis": """Workforce analysis skill:
- Separate active FTE, vendor headcount, open positions, and requests in flight.
- When discussing spend, distinguish current actual cost, plan budget, and
  available budget. Name the period used.
- Prefer aggregates; list named workers only when the user asks for them.""",
    "forecast_planning": """Forecast planning skill:
- Fetch the baseline before comparing scenarios.
- A what-if is non-destructive and must be described as a scenario, not a saved plan.
- Compare headcount and cost deltas by month, then identify the operational
  implication and any assumptions.
- Never describe deterministic formulas as an AI prediction.""",
    "hiring_operations": """Hiring operations skill:
- Inspect current request state before recommending or preparing an action.
- Draft creation and submission are separate actions.
- Never fill missing grade, compensation, vendor, dates, quantity, or
  justification with guesses. Ask for the missing field.
- Writes require a confirmation card; never say they are complete before confirmation.""",
    "planning_operations": """Planning operations skill:
- Fetch the current forecast or plan context before proposing a plan change.
- Plan budgets are integer cents in tools.
- A plan update must preserve explicit FTE, vendor, and budget values for the month.
- Writes require a confirmation card.""",
}


KEYWORDS = {
    "workforce_analysis": {
        "headcount", "roster", "worker", "employee", "salary", "cost center",
        "location", "spend", "budget", "variance",
    },
    "forecast_planning": {
        "forecast", "scenario", "what if", "what-if", "attrition", "freeze",
        "delay", "projection", "projected", "risk",
    },
    "hiring_operations": {
        "hire", "hiring", "request", "recruit", "position", "vendor",
        "contractor", "submit", "approval",
    },
    "planning_operations": {
        "plan", "target", "budget", "planned fte", "planned vendor",
    },
}


def skill_instructions(message: str) -> str:
    lowered = message.lower()
    selected = [
        name
        for name, keywords in KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    ][:3]
    if not selected:
        selected = ["workforce_analysis"]
    return "\n\n".join(SKILLS[name] for name in selected)
