"""
Sleek SaaS Sales Data Generator v2
===================================
Key improvements over v1:
  1. Incorporation only appears in month 1 (one-time fee)
  2. Products reflect plan tier realistically
  3. Payroll MRR scales with employee count
  4. Acquisition channel varies by market × segment
  5. All v1 patterns preserved (HK churn, UK CAC, SG Q1 spike, 2024 upgrade trend)
"""

import pandas as pd
import numpy as np
import random
from datetime import date, timedelta
import os

random.seed(42)
np.random.seed(42)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
START_DATE  = date(2022, 1, 1)
END_DATE    = date(2024, 12, 31)
N_CUSTOMERS = 2000

MARKETS = ["SG", "HK", "AU", "UK"]
MARKET_WEIGHTS = {"SG": 0.45, "HK": 0.25, "AU": 0.20, "UK": 0.10}

SEGMENTS = ["Startup", "SME", "Corporate"]
SEGMENT_WEIGHTS = [0.55, 0.35, 0.10]

PLANS = ["Starter", "Growth", "Full Compliance"]

# ─────────────────────────────────────────────
# PRICING (realistic, based on Sleek market rates)
# Accounting + Compliance bundled as base MRR per plan
# Payroll added separately based on headcount
# ─────────────────────────────────────────────
PLAN_BASE_MRR = {
    # Base monthly fee (Accounting + Compliance bundled)
    "Starter":         {"SG": 75,  "HK": 70,  "AU": 85,  "UK": 65},
    "Growth":          {"SG": 200, "HK": 185, "AU": 220, "UK": 175},
    "Full Compliance": {"SG": 420, "HK": 390, "AU": 460, "UK": 380},
}

# Incorporation one-time fee (charged in month 1 only)
INCORPORATION_FEE = {
    "SG": {"local": 650,  "foreign": 2200},
    "HK": {"local": 800,  "foreign": 2500},
    "AU": {"local": 900,  "foreign": 2800},
    "UK": {"local": 700,  "foreign": 2000},
}

# Payroll: per employee per month (~$25/employee/month based on $300/year)
PAYROLL_PER_EMPLOYEE = {"SG": 25, "HK": 28, "AU": 30, "UK": 24}

# Avg headcount by segment (drives payroll MRR)
HEADCOUNT_BY_SEGMENT = {
    "Startup":   (2, 8),    # 2–8 employees
    "SME":       (8, 40),   # 8–40 employees
    "Corporate": (40, 150), # 40–150 employees
}

# ─────────────────────────────────────────────
# ACQUISITION CHANNEL WEIGHTS (market × segment)
# Organic: SEO/content, Paid: ads, Referral: customer-to-customer, Partner: accounting firms/banks
# ─────────────────────────────────────────────
CHANNEL_WEIGHTS = {
    # (market, segment): {channel: weight}
    ("SG", "Startup"):   {"Organic": 0.30, "Paid": 0.20, "Referral": 0.30, "Partner": 0.20},
    ("SG", "SME"):       {"Organic": 0.25, "Paid": 0.15, "Referral": 0.20, "Partner": 0.40},
    ("SG", "Corporate"): {"Organic": 0.15, "Paid": 0.10, "Referral": 0.15, "Partner": 0.60},
    ("HK", "Startup"):   {"Organic": 0.30, "Paid": 0.25, "Referral": 0.25, "Partner": 0.20},
    ("HK", "SME"):       {"Organic": 0.25, "Paid": 0.20, "Referral": 0.20, "Partner": 0.35},
    ("HK", "Corporate"): {"Organic": 0.15, "Paid": 0.15, "Referral": 0.15, "Partner": 0.55},
    ("AU", "Startup"):   {"Organic": 0.35, "Paid": 0.30, "Referral": 0.20, "Partner": 0.15},
    ("AU", "SME"):       {"Organic": 0.30, "Paid": 0.25, "Referral": 0.20, "Partner": 0.25},
    ("AU", "Corporate"): {"Organic": 0.20, "Paid": 0.20, "Referral": 0.15, "Partner": 0.45},
    ("UK", "Startup"):   {"Organic": 0.25, "Paid": 0.45, "Referral": 0.20, "Partner": 0.10},
    ("UK", "SME"):       {"Organic": 0.20, "Paid": 0.40, "Referral": 0.15, "Partner": 0.25},
    ("UK", "Corporate"): {"Organic": 0.15, "Paid": 0.30, "Referral": 0.15, "Partner": 0.40},
}

# ─────────────────────────────────────────────
# CAC by channel and market (UK Paid most expensive)
# ─────────────────────────────────────────────
BASE_CAC = {
    "SG": {"Organic": 80,  "Paid": 320, "Referral": 60,  "Partner": 150},
    "HK": {"Organic": 90,  "Paid": 350, "Referral": 70,  "Partner": 160},
    "AU": {"Organic": 100, "Paid": 380, "Referral": 75,  "Partner": 170},
    "UK": {"Organic": 120, "Paid": 520, "Referral": 90,  "Partner": 200},
}

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def random_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))

def add_months(d, n):
    month = d.month + n
    year  = d.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    return date(year, month, 1)

def weighted_choice(weights_dict):
    keys = list(weights_dict.keys())
    wts  = [weights_dict[k] for k in keys]
    return random.choices(keys, weights=wts, k=1)[0]

def signup_date_for_market(market):
    if market == "SG":
        year = random.choices([2022, 2023, 2024], weights=[0.45, 0.35, 0.20])[0]
        month = random.randint(1, 3) if random.random() < 0.30 else random.randint(1, 12)
        return min(date(year, month, random.randint(1, 28)), END_DATE)
    elif market == "UK":
        return random_date(date(2022, 6, 1), END_DATE)
    else:
        return random_date(START_DATE, END_DATE)

def initial_plan(segment):
    if segment == "Corporate":
        return random.choices(PLANS, weights=[0.10, 0.35, 0.55])[0]
    elif segment == "SME":
        return random.choices(PLANS, weights=[0.30, 0.50, 0.20])[0]
    else:
        return random.choices(PLANS, weights=[0.55, 0.35, 0.10])[0]

def maybe_upgrade(plan, month, segment):
    idx = PLANS.index(plan)
    if idx == len(PLANS) - 1:
        return plan
    prob = 0.008
    if month.year == 2024:
        prob *= 2.0
    if segment == "SME":
        prob *= 1.3
    return PLANS[idx + 1] if random.random() < prob else plan

def monthly_churn_prob(market, month, segment):
    base = {"SG": 0.018, "HK": 0.022, "AU": 0.020, "UK": 0.015}[market]
    if market == "HK" and month.year == 2023 and month.month in [7, 8, 9]:
        base *= 2.8
    if segment == "Corporate":
        base *= 0.5
    elif segment == "Startup":
        base *= 1.2
    return min(base, 0.15)

def compute_cac(market, channel, signup_date):
    cac = BASE_CAC[market][channel]
    if channel == "Paid" and signup_date.year == 2023 and signup_date.month >= 7:
        cac *= 1.45
    return round(cac * random.uniform(0.80, 1.20), 2)

def is_foreign_founder(market, segment):
    # Corporates more likely to be foreign; UK customers mostly foreign
    if market == "UK":
        return random.random() < 0.70
    if segment == "Corporate":
        return random.random() < 0.40
    return random.random() < 0.25

# ─────────────────────────────────────────────
# PRODUCT → MRR LOGIC (the key improvement)
# Each monthly row has a primary product + MRR breakdown
# ─────────────────────────────────────────────
def get_monthly_mrr_rows(cid, month, market, segment, plan, event_type,
                          headcount, is_month_one, is_foreign):
    """
    Returns list of revenue line items for this customer-month.
    Month 1: Incorporation fee (one-time) + first month recurring
    Month 2+: Recurring only (Accounting, Compliance, ±Payroll)
    """
    rows = []
    base = PLAN_BASE_MRR[plan][market]

    # Split base MRR into Accounting (~60%) and Compliance (~40%)
    accounting_mrr  = round(base * 0.60 * random.uniform(0.97, 1.03), 2)
    compliance_mrr  = round(base * 0.40 * random.uniform(0.97, 1.03), 2)

    # Payroll: only Growth and Full Compliance, scaled by headcount
    payroll_mrr = 0
    if plan in ["Growth", "Full Compliance"]:
        rate = PAYROLL_PER_EMPLOYEE[market]
        payroll_mrr = round(headcount * rate * random.uniform(0.95, 1.05), 2)

    # Month 1: Incorporation one-time fee
    if is_month_one:
        fee_key = "foreign" if is_foreign else "local"
        inc_fee = INCORPORATION_FEE[market][fee_key]
        inc_fee = round(inc_fee * random.uniform(0.95, 1.05), 2)
        rows.append({
            "customer_id": cid,
            "month":       month.strftime("%Y-%m"),
            "market":      market,
            "segment":     segment,
            "plan":        plan,
            "product":     "Incorporation",
            "mrr":         inc_fee,
            "event_type":  "new",
        })

    # Accounting (every month)
    rows.append({
        "customer_id": cid,
        "month":       month.strftime("%Y-%m"),
        "market":      market,
        "segment":     segment,
        "plan":        plan,
        "product":     "Accounting",
        "mrr":         accounting_mrr,
        "event_type":  "new" if is_month_one else event_type,
    })

    # Compliance (every month)
    rows.append({
        "customer_id": cid,
        "month":       month.strftime("%Y-%m"),
        "market":      market,
        "segment":     segment,
        "plan":        plan,
        "product":     "Compliance",
        "mrr":         compliance_mrr,
        "event_type":  "new" if is_month_one else event_type,
    })

    # Payroll (Growth and Full Compliance only)
    if payroll_mrr > 0:
        rows.append({
            "customer_id": cid,
            "month":       month.strftime("%Y-%m"),
            "market":      market,
            "segment":     segment,
            "plan":        plan,
            "product":     "Payroll",
            "mrr":         payroll_mrr,
            "event_type":  "new" if is_month_one else event_type,
        })

    return rows

# ─────────────────────────────────────────────
# GENERATE CUSTOMERS
# ─────────────────────────────────────────────
print("Generating customers...")
customers = []

for i in range(N_CUSTOMERS):
    cid     = f"SLEEK-{i+1:04d}"
    market  = weighted_choice(MARKET_WEIGHTS)
    segment = random.choices(SEGMENTS, weights=SEGMENT_WEIGHTS)[0]
    channel = weighted_choice(CHANNEL_WEIGHTS[(market, segment)])
    signup  = signup_date_for_market(market)
    plan    = initial_plan(segment)
    cac     = compute_cac(market, channel, signup)
    foreign = is_foreign_founder(market, segment)
    hc_min, hc_max = HEADCOUNT_BY_SEGMENT[segment]
    headcount = random.randint(hc_min, hc_max)

    customers.append({
        "customer_id":         cid,
        "signup_date":         signup,
        "market":              market,
        "segment":             segment,
        "plan":                plan,
        "acquisition_channel": channel,
        "is_foreign_founder":  foreign,
        "headcount":           headcount,
        "cac":                 cac,
        "churned":             False,
        "churn_date":          None,
        "ltv":                 0.0,
    })

# ─────────────────────────────────────────────
# GENERATE MONTHLY REVENUE
# ─────────────────────────────────────────────
print("Generating monthly revenue events...")
revenue_rows = []
customer_ltv   = {c["customer_id"]: 0.0 for c in customers}
customer_churn = {c["customer_id"]: (False, None) for c in customers}

for c in customers:
    cid       = c["customer_id"]
    market    = c["market"]
    segment   = c["segment"]
    plan      = c["plan"]
    signup    = c["signup_date"]
    headcount = c["headcount"]
    foreign   = c["is_foreign_founder"]

    first_month   = date(signup.year, signup.month, 1)
    last_possible = date(END_DATE.year, END_DATE.month, 1)
    current_month = first_month
    is_month_one  = True
    churned       = False
    churn_month   = None
    total_mrr     = 0.0

    while current_month <= last_possible:
        event_type = "new" if is_month_one else "active"

        # Maybe upgrade plan
        new_plan = maybe_upgrade(plan, current_month, segment)
        if new_plan != plan and not is_month_one:
            event_type = "expansion"
            plan = new_plan
            # Headcount also grows on expansion
            headcount = min(headcount + random.randint(1, 5), HEADCOUNT_BY_SEGMENT[segment][1])

        # Get revenue rows for this month
        month_rows = get_monthly_mrr_rows(
            cid, current_month, market, segment, plan,
            event_type, headcount, is_month_one, foreign
        )
        revenue_rows.extend(month_rows)
        total_mrr += sum(r["mrr"] for r in month_rows)
        is_month_one = False

        # Check churn
        churn_p = monthly_churn_prob(market, current_month, segment)
        if random.random() < churn_p:
            churned = True
            churn_month = current_month
            next_month = add_months(current_month, 1)
            if next_month <= last_possible:
                # Add churn event (MRR = 0) for each product
                for product in ["Accounting", "Compliance"] + (["Payroll"] if plan in ["Growth", "Full Compliance"] else []):
                    revenue_rows.append({
                        "customer_id": cid,
                        "month":       next_month.strftime("%Y-%m"),
                        "market":      market,
                        "segment":     segment,
                        "plan":        plan,
                        "product":     product,
                        "mrr":         0.0,
                        "event_type":  "churn",
                    })
            break

        current_month = add_months(current_month, 1)

    customer_ltv[cid]   = round(total_mrr, 2)
    customer_churn[cid] = (churned, churn_month)

# ─────────────────────────────────────────────
# UPDATE CUSTOMER TABLE
# ─────────────────────────────────────────────
for c in customers:
    cid = c["customer_id"]
    churned, churn_month = customer_churn[cid]
    c["churned"]    = churned
    c["churn_date"] = churn_month.strftime("%Y-%m") if churn_month else None
    c["ltv"]        = customer_ltv[cid]

# ─────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────
output_dir = "/mnt/user-data/outputs"
os.makedirs(output_dir, exist_ok=True)

df_customers = pd.DataFrame(customers)
df_customers["signup_date"] = pd.to_datetime(df_customers["signup_date"])
df_customers.to_csv(f"{output_dir}/customers_v2.csv", index=False)
print(f"✅ customers_v2.csv: {len(df_customers)} rows")

df_revenue = pd.DataFrame(revenue_rows)
df_revenue.to_csv(f"{output_dir}/monthly_revenue_v2.csv", index=False)
print(f"✅ monthly_revenue_v2.csv: {len(df_revenue)} rows")

# ─────────────────────────────────────────────
# SANITY CHECK
# ─────────────────────────────────────────────
print("\n── Sanity Checks ─────────────────────────────────")

print("\nCustomers by market:")
print(df_customers["market"].value_counts().to_string())

print("\nChurn rate by market:")
print(df_customers.groupby("market")["churned"].mean().round(3).to_string())

print("\nAcquisition channel by market (%):")
ch = df_customers.groupby(["market","acquisition_channel"]).size().unstack(fill_value=0)
print((ch.div(ch.sum(axis=1), axis=0) * 100).round(1).to_string())

print("\nProduct breakdown in revenue (non-churn rows):")
active = df_revenue[df_revenue["mrr"] > 0]
print(active.groupby("product")["mrr"].agg(["count","sum"]).round(0).to_string())

print("\nIncorporation rows — should only appear in event_type=new:")
inc = df_revenue[df_revenue["product"] == "Incorporation"]
print(inc["event_type"].value_counts().to_string())

print("\nPlan distribution 2022 vs 2024 (upgrade trend):")
for yr in ["2022", "2024"]:
    sub = df_revenue[(df_revenue["month"].str.startswith(yr)) &
                     (df_revenue["product"] == "Accounting") &
                     (df_revenue["event_type"] != "churn")]
    print(f"  {yr}: {sub['plan'].value_counts(normalize=True).round(3).to_dict()}")

print("\nAvg CAC by channel:")
print(df_customers.groupby("acquisition_channel")["cac"].mean().round(0).to_string())

print("\nDone! 🎉")
