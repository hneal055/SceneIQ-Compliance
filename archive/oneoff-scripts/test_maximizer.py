from maximizer import SceneIQMaximizer, MaximizedResult


def print_result(result: MaximizedResult, label: str = ""):
    print("\n" + "=" * 65)
    print(f"PILOTFORGE MAXIMIZER{' — ' + label if label else ''}")
    print("=" * 65)

    if result.resolved_state:
        print(f"Resolved state:       {result.resolved_state}")
    print(f"Jurisdictions:        {result.jurisdictions_evaluated}")
    if result.qualified_spend:
        print(f"Qualified spend:      ${result.qualified_spend:>14,.2f}")
    print(f"Total incentive:      ${result.total_incentive_usd:>14,.2f}")
    if result.effective_rate is not None:
        print(f"Effective rate:       {result.effective_rate * 100:.1f}%")

    if result.applied_rules:
        print(f"\n{'Rule':<40} {'Type':<14} {'Value':>14}")
        print("-" * 70)
        for r in result.applied_rules:
            if r.value_unit == "percent" and result.qualified_spend:
                val_str = f"${r.computed_value:>12,.2f}  ({r.raw_value:.1f}%)"
            elif r.value_unit == "USD":
                val_str = f"${r.computed_value:>12,.2f}"
            else:
                val_str = f"{r.raw_value:.1f}%  (no spend)"
            print(f"  {r.rule_key[:38]:<38} {r.rule_type:<14} {val_str}")

    non_zero = {k: v for k, v in result.breakdown.items() if v != 0}
    if non_zero:
        print(f"\n{'Breakdown':}")
        for category, value in non_zero.items():
            print(f"  {category:<20} ${value:>12,.2f}")

    if result.warnings:
        print(f"\nWarnings:")
        for w in result.warnings:
            print(f"  [!] {w}")

    if result.recommendations != ["Incentive stack is clean — no conflicts detected"]:
        print(f"\nRecommendations:")
        for r in result.recommendations:
            print(f"  --> {r}")


def test_maximizer():
    engine = SceneIQMaximizer()

    # ── Scenario 1: Erie County (Buffalo) — lat/lng, $5M spend ────────────────
    result1 = engine.maximize(
        lat=42.8864,
        lng=-78.8784,
        project_type="film",
        qualified_spend=5_000_000,
    )
    print_result(result1, "Erie County (Buffalo) — $5M qualified spend")

    # ── Scenario 2: NYC stacking — explicit codes, $10M spend ─────────────────
    result2 = engine.maximize(
        jurisdiction_codes=["NY", "NY-NYC"],
        project_type="film",
        qualified_spend=10_000_000,
    )
    print_result(result2, "NYC stacking (NY + NY-NYC) — $10M qualified spend")

    # ── Scenario 3: no qualified_spend — should warn cleanly ──────────────────
    result3 = engine.maximize(
        lat=42.8864,
        lng=-78.8784,
        project_type="film",
    )
    print_result(result3, "Erie County — no qualified_spend (raw rates)")


if __name__ == "__main__":
    test_maximizer()
