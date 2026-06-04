"""
Finance MCP Server
------------------
Custom MCP server exposing financial analysis tools to the Azure AI Foundry agent.
Run standalone with: python finance_server.py
Or via uvx after packaging.
"""

import json
import math
from datetime import datetime, timedelta
from typing import Any
import httpx

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("finance-research")


# ─── Market Data ──────────────────────────────────────────────────────────────

@mcp.tool()
async def get_stock_quote(ticker: str) -> dict:
    """
    Get a real-time (or latest) stock quote for a given ticker symbol.
    Uses Yahoo Finance unofficial API (no key required for demo).
    
    Args:
        ticker: Stock ticker symbol, e.g. 'AAPL', 'MSFT', 'TSLA'
    Returns:
        dict with price, change, volume, market cap, pe_ratio
    """
    ticker = ticker.upper().strip()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"interval": "1d", "range": "5d"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            data = r.json()

        result = data["chart"]["result"][0]
        meta = result["meta"]

        return {
            "ticker": ticker,
            "company": meta.get("longName", ticker),
            "price": round(meta.get("regularMarketPrice", 0), 2),
            "previous_close": round(meta.get("chartPreviousClose", 0), 2),
            "change": round(
                meta.get("regularMarketPrice", 0) - meta.get("chartPreviousClose", 0), 2
            ),
            "change_pct": round(
                (
                    (meta.get("regularMarketPrice", 0) - meta.get("chartPreviousClose", 0))
                    / meta.get("chartPreviousClose", 1)
                )
                * 100,
                2,
            ),
            "volume": meta.get("regularMarketVolume", "N/A"),
            "currency": meta.get("currency", "USD"),
            "exchange": meta.get("exchangeName", "N/A"),
            "market_state": meta.get("marketState", "N/A"),
            "52w_high": round(meta.get("fiftyTwoWeekHigh", 0), 2),
            "52w_low": round(meta.get("fiftyTwoWeekLow", 0), 2),
        }
    except Exception as e:
        return {"error": f"Could not fetch quote for {ticker}: {str(e)}"}


@mcp.tool()
async def compare_stocks(tickers: list[str]) -> dict:
    """
    Compare multiple stocks side-by-side.
    
    Args:
        tickers: List of ticker symbols, e.g. ['AAPL', 'MSFT', 'GOOGL']
    Returns:
        Comparative data for all tickers
    """
    results = {}
    for ticker in tickers[:5]:  # Cap at 5 to avoid rate limits
        quote = await get_stock_quote(ticker)
        results[ticker] = quote
    return results


# ─── Portfolio Analysis ────────────────────────────────────────────────────────

@mcp.tool()
def analyze_portfolio(holdings: list[dict]) -> dict:
    """
    Analyze a stock portfolio for allocation, diversity, and basic metrics.
    
    Args:
        holdings: List of dicts with keys: ticker, shares, avg_cost
                  Example: [{"ticker": "AAPL", "shares": 10, "avg_cost": 150.00}]
    Returns:
        Portfolio summary with allocation %, total value, gain/loss
    """
    if not holdings:
        return {"error": "No holdings provided"}

    total_cost = sum(h["shares"] * h["avg_cost"] for h in holdings)
    
    analysis = {
        "total_cost_basis": round(total_cost, 2),
        "holdings_count": len(holdings),
        "holdings": [],
        "sector_note": "For sector breakdown, consider adding sector tags to each holding.",
    }

    for h in holdings:
        ticker = h.get("ticker", "?").upper()
        shares = h.get("shares", 0)
        avg_cost = h.get("avg_cost", 0)
        cost_basis = shares * avg_cost
        weight = (cost_basis / total_cost * 100) if total_cost > 0 else 0

        analysis["holdings"].append({
            "ticker": ticker,
            "shares": shares,
            "avg_cost": avg_cost,
            "cost_basis": round(cost_basis, 2),
            "portfolio_weight_pct": round(weight, 2),
        })

    # Concentration check
    weights = [h["portfolio_weight_pct"] for h in analysis["holdings"]]
    max_weight = max(weights) if weights else 0
    analysis["concentration_warning"] = max_weight > 30

    return analysis


# ─── Financial Calculators ─────────────────────────────────────────────────────

@mcp.tool()
def calculate_compound_interest(
    principal: float,
    annual_rate_pct: float,
    years: int,
    compounds_per_year: int = 12,
    monthly_contribution: float = 0.0,
) -> dict:
    """
    Calculate compound interest growth with optional monthly contributions.
    
    Args:
        principal: Initial investment amount in dollars
        annual_rate_pct: Annual interest rate as percentage (e.g. 7 for 7%)
        years: Number of years
        compounds_per_year: How often interest compounds (12=monthly, 4=quarterly, 1=annual)
        monthly_contribution: Optional recurring monthly contribution
    Returns:
        Future value, total contributions, total interest earned, year-by-year breakdown
    """
    r = annual_rate_pct / 100 / compounds_per_year
    n = compounds_per_year * years

    # Future value of lump sum
    fv_principal = principal * (1 + r) ** n

    # Future value of monthly contributions (annuity)
    if monthly_contribution > 0 and r > 0:
        # Adjust contribution to match compounding frequency
        contrib_per_period = monthly_contribution * (12 / compounds_per_year)
        fv_contributions = contrib_per_period * (((1 + r) ** n - 1) / r)
    else:
        fv_contributions = 0
        contrib_per_period = 0

    total_future_value = fv_principal + fv_contributions
    total_contributions = principal + (monthly_contribution * 12 * years)
    total_interest = total_future_value - total_contributions

    # Year-by-year snapshot
    yearly = []
    for yr in range(1, min(years + 1, 31)):  # cap display at 30 years
        n_yr = compounds_per_year * yr
        fv_yr = principal * (1 + r) ** n_yr
        if monthly_contribution > 0 and r > 0:
            fv_yr += contrib_per_period * (((1 + r) ** n_yr - 1) / r)
        yearly.append({"year": yr, "value": round(fv_yr, 2)})

    return {
        "initial_principal": principal,
        "monthly_contribution": monthly_contribution,
        "annual_rate_pct": annual_rate_pct,
        "years": years,
        "future_value": round(total_future_value, 2),
        "total_contributions": round(total_contributions, 2),
        "total_interest_earned": round(total_interest, 2),
        "return_multiplier": round(total_future_value / max(total_contributions, 1), 2),
        "yearly_breakdown": yearly,
    }


@mcp.tool()
def calculate_loan_payment(
    loan_amount: float,
    annual_rate_pct: float,
    loan_term_years: int,
    extra_monthly_payment: float = 0.0,
) -> dict:
    """
    Calculate monthly loan payments, total interest, and amortization summary.
    Supports mortgage, auto loan, personal loan, student loan.
    
    Args:
        loan_amount: Total loan amount in dollars
        annual_rate_pct: Annual interest rate as percentage
        loan_term_years: Loan term in years
        extra_monthly_payment: Optional extra payment per month to pay off faster
    Returns:
        Monthly payment, total interest, payoff timeline, savings from extra payments
    """
    if annual_rate_pct == 0:
        monthly = loan_amount / (loan_term_years * 12)
        return {
            "monthly_payment": round(monthly, 2),
            "total_paid": round(monthly * loan_term_years * 12, 2),
            "total_interest": 0.0,
        }

    r = annual_rate_pct / 100 / 12
    n = loan_term_years * 12
    monthly = loan_amount * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

    total_paid = monthly * n
    total_interest = total_paid - loan_amount

    result = {
        "loan_amount": loan_amount,
        "annual_rate_pct": annual_rate_pct,
        "loan_term_years": loan_term_years,
        "monthly_payment": round(monthly, 2),
        "total_paid": round(total_paid, 2),
        "total_interest": round(total_interest, 2),
        "effective_cost_pct": round((total_interest / loan_amount) * 100, 2),
    }

    # Extra payment scenario
    if extra_monthly_payment > 0:
        balance = loan_amount
        months = 0
        total_paid_extra = 0
        while balance > 0 and months < n * 2:
            interest = balance * r
            payment = min(monthly + extra_monthly_payment, balance + interest)
            balance = balance + interest - payment
            total_paid_extra += payment
            months += 1

        interest_saved = total_paid - total_paid_extra
        result["extra_payment_scenario"] = {
            "extra_monthly": extra_monthly_payment,
            "new_payoff_months": months,
            "new_payoff_years": round(months / 12, 1),
            "months_saved": n - months,
            "interest_saved": round(interest_saved, 2),
            "total_paid_with_extra": round(total_paid_extra, 2),
        }

    return result


@mcp.tool()
def calculate_retirement_readiness(
    current_age: int,
    retirement_age: int,
    current_savings: float,
    monthly_contribution: float,
    expected_annual_return_pct: float = 7.0,
    desired_monthly_income: float = 5000.0,
    social_security_monthly: float = 0.0,
) -> dict:
    """
    Estimate retirement readiness — projected savings vs. needed nest egg.
    Uses the 4% safe withdrawal rule as default.
    
    Args:
        current_age: Your current age
        retirement_age: Target retirement age
        current_savings: Current retirement savings
        monthly_contribution: Monthly contribution to retirement accounts
        expected_annual_return_pct: Expected average annual return (default 7%)
        desired_monthly_income: Desired monthly income in retirement
        social_security_monthly: Expected Social Security monthly benefit
    Returns:
        Projected savings, needed nest egg, gap analysis, recommendations
    """
    years_to_retire = retirement_age - current_age
    if years_to_retire <= 0:
        return {"error": "Retirement age must be greater than current age"}

    # Project savings at retirement
    projection = calculate_compound_interest(
        principal=current_savings,
        annual_rate_pct=expected_annual_return_pct,
        years=years_to_retire,
        compounds_per_year=12,
        monthly_contribution=monthly_contribution,
    )
    projected_savings = projection["future_value"]

    # Needed nest egg (4% rule)
    monthly_income_needed = desired_monthly_income - social_security_monthly
    annual_income_needed = monthly_income_needed * 12
    nest_egg_needed = annual_income_needed / 0.04  # 4% safe withdrawal

    gap = projected_savings - nest_egg_needed
    on_track = gap >= 0

    # How much more per month to close gap
    extra_needed = 0
    if not on_track and years_to_retire > 0:
        r = expected_annual_return_pct / 100 / 12
        n = years_to_retire * 12
        pv_gap = abs(gap)
        if r > 0:
            extra_needed = pv_gap * r / ((1 + r) ** n - 1)

    return {
        "current_age": current_age,
        "retirement_age": retirement_age,
        "years_to_retirement": years_to_retire,
        "current_savings": current_savings,
        "monthly_contribution": monthly_contribution,
        "projected_savings_at_retirement": round(projected_savings, 2),
        "nest_egg_needed_4pct_rule": round(nest_egg_needed, 2),
        "gap": round(gap, 2),
        "on_track": on_track,
        "status": "✅ On Track" if on_track else "⚠️ Shortfall Projected",
        "extra_monthly_needed_to_close_gap": round(extra_needed, 2) if not on_track else 0,
        "social_security_monthly": social_security_monthly,
        "desired_monthly_income": desired_monthly_income,
        "assumptions": {
            "withdrawal_rate": "4% (standard safe withdrawal rate)",
            "return_rate_pct": expected_annual_return_pct,
            "inflation_note": "These projections are in nominal dollars. Adjust return rate down ~3% to approximate real returns.",
        },
    }


# ─── Budget Analysis ───────────────────────────────────────────────────────────

@mcp.tool()
def analyze_budget(
    monthly_income: float,
    expenses: dict[str, float],
) -> dict:
    """
    Analyze a monthly budget using the 50/30/20 framework and provide recommendations.
    
    Args:
        monthly_income: Gross monthly income (before tax)
        expenses: Dict of category -> monthly amount
                  e.g. {"rent": 1500, "groceries": 400, "netflix": 15, "car_payment": 350}
    Returns:
        Budget breakdown, 50/30/20 analysis, savings rate, actionable tips
    """
    # Rough after-tax estimate (simplified)
    after_tax = monthly_income * 0.75  # rough 25% effective tax rate

    total_expenses = sum(expenses.values())
    savings = after_tax - total_expenses
    savings_rate = (savings / after_tax * 100) if after_tax > 0 else 0

    # 50/30/20 targets
    needs_target = after_tax * 0.50
    wants_target = after_tax * 0.30
    savings_target = after_tax * 0.20

    # Categorize expenses (heuristic)
    needs_keywords = ["rent", "mortgage", "utilities", "insurance", "groceries", "food", 
                      "gas", "electric", "water", "internet", "phone", "car_payment",
                      "medical", "health", "loan", "minimum"]
    wants_keywords = ["dining", "restaurant", "entertainment", "netflix", "spotify",
                      "gym", "subscription", "shopping", "travel", "vacation", "hobby"]

    needs_total = 0
    wants_total = 0
    uncategorized = {}

    for category, amount in expenses.items():
        cat_lower = category.lower().replace(" ", "_")
        if any(k in cat_lower for k in needs_keywords):
            needs_total += amount
        elif any(k in cat_lower for k in wants_keywords):
            wants_total += amount
        else:
            uncategorized[category] = amount
            needs_total += amount * 0.5  # split uncategorized 50/50
            wants_total += amount * 0.5

    return {
        "monthly_income_gross": monthly_income,
        "estimated_after_tax": round(after_tax, 2),
        "total_expenses": round(total_expenses, 2),
        "monthly_savings": round(savings, 2),
        "savings_rate_pct": round(savings_rate, 2),
        "savings_status": (
            "Excellent (20%+)" if savings_rate >= 20
            else "Good (10–20%)" if savings_rate >= 10
            else "Needs Improvement (<10%)"
        ),
        "50_30_20_analysis": {
            "needs": {
                "actual": round(needs_total, 2),
                "target": round(needs_target, 2),
                "over_budget": needs_total > needs_target,
            },
            "wants": {
                "actual": round(wants_total, 2),
                "target": round(wants_target, 2),
                "over_budget": wants_total > wants_target,
            },
            "savings": {
                "actual": round(savings, 2),
                "target": round(savings_target, 2),
                "meeting_target": savings >= savings_target,
            },
        },
        "expense_breakdown": expenses,
        "uncategorized_expenses": uncategorized,
        "recommendations": _generate_budget_tips(savings_rate, needs_total, needs_target, wants_total, wants_target),
    }


def _generate_budget_tips(savings_rate, needs, needs_target, wants, wants_target):
    tips = []
    if savings_rate < 10:
        tips.append("🚨 Your savings rate is critically low. Aim to save at least 10% of take-home pay.")
    if savings_rate < 20:
        tips.append("💡 Try to build toward a 20% savings rate using the 50/30/20 rule.")
    if needs > needs_target:
        tips.append(f"🏠 Your essential expenses exceed 50% of income. Consider housing or transportation costs as primary levers.")
    if wants > wants_target:
        tips.append("☕ Your discretionary spending exceeds 30%. Review subscriptions and dining expenses.")
    if savings_rate >= 20:
        tips.append("✅ Great savings rate! Consider maxing out tax-advantaged accounts (401k, IRA, HSA).")
    return tips


# ─── Market Research ───────────────────────────────────────────────────────────

@mcp.tool()
def calculate_dcf_valuation(
    current_free_cash_flow: float,
    growth_rate_pct: float,
    terminal_growth_rate_pct: float = 3.0,
    discount_rate_pct: float = 10.0,
    projection_years: int = 10,
    shares_outstanding_millions: float = 1000.0,
) -> dict:
    """
    Simple Discounted Cash Flow (DCF) valuation model.
    
    Args:
        current_free_cash_flow: Current annual free cash flow in millions
        growth_rate_pct: Expected annual FCF growth rate during projection period
        terminal_growth_rate_pct: Long-term sustainable growth rate (default 3%)
        discount_rate_pct: Required rate of return / WACC (default 10%)
        projection_years: Number of years to project (default 10)
        shares_outstanding_millions: Shares outstanding for per-share value
    Returns:
        Intrinsic value estimate, per-share value, projected cash flows
    """
    r = discount_rate_pct / 100
    g = growth_rate_pct / 100
    g_terminal = terminal_growth_rate_pct / 100

    # Project FCF
    projected_fcf = []
    pv_fcf = []
    fcf = current_free_cash_flow

    for yr in range(1, projection_years + 1):
        fcf = fcf * (1 + g)
        pv = fcf / (1 + r) ** yr
        projected_fcf.append({"year": yr, "fcf": round(fcf, 2), "pv": round(pv, 2)})
        pv_fcf.append(pv)

    # Terminal value
    terminal_fcf = fcf * (1 + g_terminal)
    terminal_value = terminal_fcf / (r - g_terminal)
    pv_terminal = terminal_value / (1 + r) ** projection_years

    total_pv = sum(pv_fcf) + pv_terminal
    intrinsic_value_per_share = (total_pv / shares_outstanding_millions) if shares_outstanding_millions > 0 else 0

    return {
        "current_fcf_millions": current_free_cash_flow,
        "growth_rate_pct": growth_rate_pct,
        "discount_rate_pct": discount_rate_pct,
        "terminal_growth_rate_pct": terminal_growth_rate_pct,
        "total_enterprise_value_millions": round(total_pv, 2),
        "pv_of_projected_fcf_millions": round(sum(pv_fcf), 2),
        "pv_of_terminal_value_millions": round(pv_terminal, 2),
        "terminal_value_pct_of_total": round(pv_terminal / total_pv * 100, 1),
        "intrinsic_value_per_share": round(intrinsic_value_per_share, 2),
        "shares_outstanding_millions": shares_outstanding_millions,
        "projected_cash_flows": projected_fcf,
        "disclaimer": "DCF is highly sensitive to assumptions. Use as one of many valuation inputs.",
    }


if __name__ == "__main__":
    mcp.run()
