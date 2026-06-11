# src/utils/money.py
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")

def D(x) -> Decimal:
    # safe conversion for float/str/int
    return Decimal(str(x))

def money(x) -> Decimal:
    # round to cents using standard HALF_UP currency rounding
    return D(x).quantize(CENT, rounding=ROUND_HALF_UP)

