"""
Shopo Robo - Retail Financial & EBITDA Calculator
Calculates Gross Profit, Operating Expenses, EBITDA, and Net Profit
specifically structured for retail shopkeepers and Tier-3 MSME business owners.
"""

def calculate_financials(
    monthly_sales: float = 156000.0,
    cogs: float = 118000.0,
    shop_rent: float = 8000.0,
    electricity_bills: float = 2500.0,
    staff_wages: float = 6000.0,
    transport_freight: float = 1500.0,
    spoilage_wastage: float = 800.0,
    interest_loans: float = 1200.0,
    depreciation: float = 800.0,
    taxes: float = 1500.0
) -> dict:
    gross_profit = max(0.0, monthly_sales - cogs)
    gross_margin_pct = (gross_profit / monthly_sales * 100) if monthly_sales > 0 else 0.0

    total_opex = shop_rent + electricity_bills + staff_wages + transport_freight + spoilage_wastage
    ebitda = gross_profit - total_opex
    ebitda_margin_pct = (ebitda / monthly_sales * 100) if monthly_sales > 0 else 0.0

    total_below_ebitda = interest_loans + depreciation + taxes
    net_profit = ebitda - total_below_ebitda
    net_margin_pct = (net_profit / monthly_sales * 100) if monthly_sales > 0 else 0.0

    voice_summary = (
        f"Sir, this month's gross sales stand at ₹{monthly_sales:,.0f}. "
        f"After purchase cost of ₹{cogs:,.0f}, your gross profit is ₹{gross_profit:,.0f}. "
        f"Operating expenses total ₹{total_opex:,.0f}, giving an EBITDA of ₹{ebitda:,.0f}. "
        f"Your final net take-home profit is ₹{net_profit:,.0f}, with a net margin of {net_margin_pct:.1f}%."
    )

    return {
        "monthly_sales": monthly_sales,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "gross_margin_pct": round(gross_margin_pct, 1),
        "total_opex": total_opex,
        "ebitda": ebitda,
        "ebitda_margin_pct": round(ebitda_margin_pct, 1),
        "net_profit": net_profit,
        "net_margin_pct": round(net_margin_pct, 1),
        "breakdown": {
            "rent": shop_rent,
            "electricity": electricity_bills,
            "staff": staff_wages,
            "transport": transport_freight,
            "spoilage": spoilage_wastage,
            "interest": interest_loans,
            "depreciation": depreciation,
            "taxes": taxes
        },
        "voice_summary": voice_summary
    }
