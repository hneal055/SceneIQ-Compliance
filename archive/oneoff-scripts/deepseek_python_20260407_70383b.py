def get_multiplier(rule, base_budget):
    for condition in rule:
        min_budget = condition.get("min", float("-inf"))
        max_budget = condition.get("max", float("inf"))
        multiplier = condition.get("multiplier", 0.0)
        if min_budget <= base_budget <= max_budget:
            return multiplier
    return 0.0

# Example
rule = [
    {"min": 0, "max": 1000000, "multiplier": 0.20},
    {"min": 1000001, "max": None, "multiplier": 0.30}
]
print(get_multiplier(rule, 1500000))  # 0.30