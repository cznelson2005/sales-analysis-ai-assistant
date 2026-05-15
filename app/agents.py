import json
import pandas as pd
from orchestrator import orchastrator, schema
import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-2.5-flash-lite")

def agent_overview(context: dict) -> dict:

  schema = json.dumps(json.loads(context['schema'])['tables'])

  #########
  #MRR data
  #########
  mrr_data = pd.DataFrame(context['mrr_data'])
  total_mrr = mrr_data['monthly_revenue'].sum()
  top_mrr_market = mrr_data.groupby('market')['monthly_revenue'].sum().idxmax()
  top_mrr_segment = mrr_data.groupby('segment')['monthly_revenue'].sum().idxmax()
  top_mrr_plan = mrr_data.groupby('plan')['monthly_revenue'].sum().idxmax()
  top_mrr_product = mrr_data.groupby('product')['monthly_revenue'].sum().idxmax()

  ##MRR breakdown
  mkt_pct = (mrr_data.groupby('market')['monthly_revenue'].sum() / total_mrr * 100).round(1).to_dict()
  segment_pct = (mrr_data.groupby('segment')['monthly_revenue'].sum() / total_mrr * 100).round(1).to_dict()
  plan_pct = (mrr_data.groupby('plan')['monthly_revenue'].sum() / total_mrr * 100).round(1).to_dict()
  product_pct = (mrr_data.groupby('product')['monthly_revenue'].sum() / total_mrr * 100).round(1).to_dict()

  mrr_by_month = mrr_data.groupby('month')['monthly_revenue'].sum()
  first_month = mrr_by_month.iloc[0]
  last_month = mrr_by_month.iloc[-1]
  mrr_growth = ((last_month - first_month) / first_month * 100).round(1)

  #########
  #Churn data
  active_customer = df_revenue[
      (df_revenue['month'] >= context['params']['start_date'][:7]) &
       (df_revenue['month'] <= context['params']['end_date'][:7]) &
      (df_revenue['event_type'] != 'churn')
       ]['customer_id'].nunique()

  churn_data = pd.DataFrame(context['churn_data'])
  total_churn_customer = churn_data['customers_lost'].sum()

  #Churn breakdown
  top_churn_reasons = churn_data.groupby('churn_reason_category')['customers_lost'].sum().idxmax()
  top_churn_market = churn_data.groupby('market')['customers_lost'].sum().idxmax()
  top_churn_segment = churn_data.groupby('segment')['customers_lost'].sum().idxmax()
  top_churn_plan = churn_data.groupby('plan')['customers_lost'].sum().idxmax()

  #########
  #CAC Data
  #########
  cac_data = pd.DataFrame(context['cac_data'])
  avg_cac      = cac_data['avg_cac'].mean().round(2)
  avg_ltv      = cac_data['avg_ltv'].mean().round(2)
  avg_ltv_cac  = cac_data['ltv_cac_ratio'].mean().round(2)
  top_cac_channel = cac_data.groupby('acquisition_channel')['avg_cac'].mean().idxmax()


  prompt=f"""
  You are a data analyst at an accounting SaaS company.

  You are goal is to analyze the data and provide overview insights to the business.

  ### Data Dictionary
  {schema}

  ### Paramaters
  Markets: {context['params']['market']} | Period: {context['params']['start_date']} to {context['params']['end_date']}

  ###MRR Data
  {mrr_data.to_string(index=False)}

  ###Churn Data
  {churn_data.to_string(index=False)}

  ## Pre-calculated Numbers (use these exactly)
  - Total MRR: ${total_mrr:,.0f}
  - MRR Growth: {mrr_growth}%
  - Top Market: {top_mrr_market}
  - Top Segment: {top_mrr_segment}
  - Top Plan: {top_mrr_plan}
  - Top Product: {top_mrr_product}
  - Market MRR share: {mkt_pct}
  - Segment MRR share: {segment_pct}
  - Plan MRR share: {plan_pct}
  - Product MRR share: {product_pct}
  - Total Churned Customers: {total_churn_customer}
  - Total Active Customers: {active_customer}
  - Top Churn Reason: {top_churn_reasons}
  - Top Churn Market: {top_churn_market}
  - Top Churn Segment: {top_churn_segment}
  - Top Churn Plan: {top_churn_plan}
  - Avg CAC: ${avg_cac:,.0f}
  - Avg LTV: ${avg_ltv:,.0f}
  - LTV:CAC Ratio: {avg_ltv_cac}x
  - Most Expensive Channel: {top_cac_channel}

  ## Instructions
  Analyze the data above and write a structured overview with exactly these 4 sections,
  separated by a divider line.

  - You MUST reference specific numbers from the data in every sentence
  - Do NOT make general statements without backing them up with exact figures
  - Refer to the pre-calculated numbers for insight generation
  - Format numbers clearly: $1,234 for revenue, 12.3% for percentages
  - Note: Payroll MRR scales with headcount, focus on Accounting and Compliance for product mix insight

  ────────────────────────────────────────────────────
  Overall Performance:
  [2 sentences on overall MRR trend and growth]

  ────────────────────────────────────────────────────
  Key Highlights:
  [3 sentences on notable trends across market, segment, or plan]

  ────────────────────────────────────────────────────
  Revenue Mix:
  [2 sentences on which market/segment/plan is driving most revenue]

  ────────────────────────────────────────────────────
  Customer Churn:
  [2 sentences on which market/segment/plan is driving most churn]

  ────────────────────────────────────────────────────
  Customer Acquisition Cost:
  [2 sentences on which channel is driving most CAC]

  ────────────────────────────────────────────────────
  Watch Out:
  [1 sentence on the most concerning trend in the data]
  """

  return model.generate_content(
      prompt,
      generation_config=genai.GenerationConfig(temperature=0.3)
      ).text

def agent_anomaly_detector(context: dict,
                            churn_threshold=50,
                            mrr_neg_months=2,
                            ltv_cac_threshold=3,
                            revenue_mix_threshold=0.7,
                            cac_threshold=2) -> dict:

  mrr_data = pd.DataFrame(context['mrr_data'])
  churn_data = pd.DataFrame(context['churn_data'])

  #MRR monthly trend
  mrr_by_month = (
      mrr_data.groupby('month')['monthly_revenue'].sum()
      .reset_index()
      .sort_values('month')
  )

  mrr_by_month['mrr_growth'] = mrr_by_month['monthly_revenue'].pct_change() * 100

  #Churn
  churn_by_month = (
      churn_data.groupby('month')['customers_lost'].sum()
      .reset_index().rename(columns={'customers_lost': "total_churn"})
      .sort_values('month')
  )

  churn_by_month['3m_average'] = churn_by_month['total_churn'].rolling(3, min_periods=1).mean().shift(1)
  churn_by_month['churn_vs_baseline'] = (
      (churn_by_month['total_churn'] - churn_by_month['3m_average'])
      / churn_by_month['3m_average'] * 100
  ).round(1)


  #Churn by market
  churn_by_market = (
      churn_data.groupby(['month', 'market'])['customers_lost'].sum()
      .reset_index()
  )

  # Revenue mix
  total_mrr = mrr_data['monthly_revenue'].sum()
  market_pct = (mrr_data.groupby('market')['monthly_revenue'].sum() / total_mrr).to_dict()
  segment_pct = (mrr_data.groupby('segment')['monthly_revenue'].sum() / total_mrr).to_dict()
  plan_pct = (mrr_data.groupby('plan')['monthly_revenue'].sum() / total_mrr).to_dict()
  product_pct = (mrr_data.groupby('product')['monthly_revenue'].sum() / total_mrr).to_dict()

  prompt=f"""
  You are a data analyst at an accounting SaaS company.

  You are goal is to analyze the data and report any anomalies you observed based on the trends.

  Market: {context['params']['market']} | Period: {context['params']['start_date']} to {context['params']['end_date']}

  #MRR Trend (monthly, all markets)
  {mrr_by_month.to_string(index=False)}

  #Churn Trend(monthly, all markets)
  {churn_by_month.to_string(index=False)}

  #Churn by Market (monthly)
  {churn_by_market.to_string(index=False)}

  #Revenue Mix
  Market share: {market_pct}
  Segment share: {segment_pct}
  Plan share: {plan_pct}
  Product share: {product_pct}

  #Anomaly rules
  - MRR: flag out anomaly if the MRR trend has been negative for {mrr_neg_months} consecutive months
  - Churn: flag out anomaly if churn_vs_baseline is > +{churn_threshold}%. Use exact value from [churn_by_month] table only
  - LTV:CAC < {ltv_cac_threshold}x → flag. LTV:CAC > {ltv_cac_threshold}x is healthy, do NOT flag
  - Revenue Mix: flag ONLY if one market/segment/plan > {revenue_mix_threshold * 100}%. Exclude Payroll from product check
  - CAC: not applicable without customer-level data

  ## Drill Down Rules:
  - For churn spikes: cross-reference churn by market table, set drill_down_market to market with highest customers_lost that month
  - For market concentration: set drill_down_market to that market
  - If not market-specific: set drill_down_market to null

  ## Critical Instructions:
  - Only apply rules listed above, do not invent new rules
  - Do NOT flag if threshold is not strictly exceeded
  - Do NOT include anomaly if your observation says threshold is not met
  - severity must be "High" or "Medium" only

  Return ONLY a JSON object, no explanation, no markdown fences:
  {{
    "has_anomaly": true or false,
    "anomalies": [
      {{
        "metric": "MRR | Churn | LTV:CAC | Revenue Mix",
        "month": "YYYY-MM or null",
        "observation": "one sentence with exact numbers from data",
        "severity": "High | Medium",
        "possible_cause": "one sentence hypothesis",
        "drill_down_market": "SG | HK | AU | UK | null"
      }}
    ],
    "summary": "one sentence summary"
  }}
  """
  raw    = model.generate_content(prompt, generation_config=genai.GenerationConfig(temperature=0.0)).text
  clean  = raw.replace("```json", "").replace("```", "").strip()
  result = json.loads(clean)

  # ── Python filter ─────────────────────────────────────────────────────────
  churn_lookup = churn_by_month.set_index('month')['churn_vs_baseline'].to_dict()
  neg_growth   = mrr_by_month['mrr_growth'] < 0
  consecutive_neg = neg_growth & neg_growth.shift(1, fill_value=False)

  filtered = []
  for a in result['anomalies']:
      if a['metric'] == 'Churn':
          if abs(churn_lookup.get(a['month'], 0)) <= churn_threshold:
              continue
      elif a['metric'] == 'Revenue Mix':
          all_pcts = {**market_pct, **segment_pct, **plan_pct}
          if not any(v > revenue_mix_threshold for v in all_pcts.values()):
              continue
      elif a['metric'] == 'MRR':
          if not consecutive_neg.any():
              continue
      filtered.append(a)

  result['anomalies'] = filtered
  result['has_anomaly'] = len(filtered) > 0

  # ── Print ──────────────────────────────────────────────────────────────────
  print("=" * 55)
  print("🔍 ANOMALY DETECTOR")
  print("=" * 55)
  print(f"\n{result['summary']}\n")

  if result['has_anomaly']:
      print(f"⚠️  {len(result['anomalies'])} anomaly/anomalies detected:\n")
      for a in result['anomalies']:
          month_str  = f"[{a['month']}] " if a['month'] else ""
          market_str = f"  → Drill down: {a['drill_down_market']}" if a.get('drill_down_market') else ""
          print(f"  {a['metric']} {month_str}[{a['severity']}]")
          print(f"  → {a['observation']}")
          print(f"  → Possible cause: {a['possible_cause']}")
          if market_str:
              print(market_str)
          print()
  else:
      print("✅ No anomalies detected — all metrics within normal range")

  print("=" * 55)
  return result

def agent_deep_dive(anomaly_result: dict, start_date: str, end_date: str) -> dict:

    flagged_markets = set(
        a['drill_down_market'] 
        for a in anomaly_result['anomalies'] 
        if a.get('drill_down_market') and a['drill_down_market'] not in [None, 'null', '']
    )

    print('flagged markets: ', flagged_markets)

    if not flagged_markets:
        print("No market-specific anomalies to drill down.")
        return {}

    print('Flagged_markets: ', flagged_markets)

    deep_dive_results = {}

    for market in flagged_markets:

        print('Market: ', market)

        # Re-run orchestrator for specific market
        mkt_ctx = orchastrator(market=[market], start_date=start_date, end_date=end_date)

        # Get anomalies for this market
        mkt_anomalies = [
            a for a in anomaly_result['anomalies']
            if a.get('drill_down_market') == market
        ]

        # Pre-calculate from raw data
        mrr_df   = pd.DataFrame(mkt_ctx['mrr_data'])
        churn_df = pd.DataFrame(mkt_ctx['churn_data'])
        cac_df   = pd.DataFrame(mkt_ctx['cac_data'])

        # MRR breakdown
        total_mrr    = mrr_df['monthly_revenue'].sum()
        segment_pct  = (mrr_df.groupby('segment')['monthly_revenue'].sum() / total_mrr * 100).round(1).to_dict()
        plan_pct     = (mrr_df.groupby('plan')['monthly_revenue'].sum() / total_mrr * 100).round(1).to_dict()

        # Churn breakdown
        churn_by_segment = churn_df.groupby('segment')['customers_lost'].sum().to_dict()
        churn_by_plan    = churn_df.groupby('plan')['customers_lost'].sum().to_dict()
        churn_by_reason  = churn_df.groupby('churn_reason_category')['customers_lost'].sum().to_dict()

        # CAC / LTV
        avg_cac     = cac_df['avg_cac'].mean().round(2)
        avg_ltv_cac = cac_df['ltv_cac_ratio'].mean().round(2)
        top_cac_channel = cac_df.groupby('acquisition_channel')['avg_cac'].mean().idxmax()

        prompt = f"""
        You are a senior sales analyst at Sleek, an accounting SaaS company.
        You are deep diving into the {market} market to identify root causes of detected anomalies.

        ## Detected Anomalies in {market}
        {json.dumps(mkt_anomalies, indent=2)}

        ## {market} Pre-calculated Metrics
        - Total MRR: ${total_mrr:,.0f}
        - MRR by Segment (%): {segment_pct}
        - MRR by Plan (%): {plan_pct}
        - Churn by Segment: {churn_by_segment}
        - Churn by Plan: {churn_by_plan}
        - Churn by Reason: {churn_by_reason}
        - Avg CAC: ${avg_cac:,.0f}
        - LTV:CAC Ratio: {avg_ltv_cac}x
        - Most Expensive Channel: {top_cac_channel}

        ## {market} MRR Trend
        {mrr_df.groupby('month')['monthly_revenue'].sum().reset_index().to_string(index=False)}

        ## {market} Churn Trend
        {churn_df.groupby('month')['customers_lost'].sum().reset_index().to_string(index=False)}

        ## Instructions
        - Focus on identifying WHICH segment / plan / channel is driving the anomaly
        - Cross-reference MRR and churn breakdowns to find the most likely driver
        - Be specific with numbers from the pre-calculated metrics

        Return ONLY a JSON object, no explanation, no markdown fences:
        {{
          "market": "{market}",
          "anomaly_summary": "one sentence describing the anomaly in this market with exact numbers",
          "drivers": [
            {{
              "dimension": "Segment | Plan | Channel | Product",
              "driver": "specific value e.g. Startup, Paid, Starter",
              "observation": "one sentence with exact numbers",
              "contribution": "High | Medium"
            }}
          ],
          "root_cause": "2 sentences synthesizing the most likely root cause with numbers",
          "recommended_action": "one sentence on what to investigate or action to take"
        }}
        """

        raw    = model.generate_content(prompt, generation_config=genai.GenerationConfig(temperature=0.1)).text
        clean  = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)
        deep_dive_results[market] = result

        # Print
        print("=" * 55)
        print(f"🔬 DEEP DIVE — {market}")
        print("=" * 55)
        print(f"\n{result['anomaly_summary']}\n")
        print("── Drivers ──────────────────────────────────────────")
        for d in result['drivers']:
            print(f"  [{d['dimension']}] {d['driver']} ({d['contribution']})")
            print(f"  → {d['observation']}\n")
        print("── Root Cause ───────────────────────────────────────")
        print(f"  {result['root_cause']}\n")
        print("── Recommended Action ───────────────────────────────")
        print(f"  {result['recommended_action']}")
        print("=" * 55)

    return deep_dive_results

def agent_summary(context: dict, overview: str, anomaly_result: dict, deep_dive: dict) -> str:

    # Prepare deep dive text
    deep_dive_str = ""
    if deep_dive:
        for market, result in deep_dive.items():
            deep_dive_str += f"\n### {market}\n"
            deep_dive_str += f"Anomaly: {result.get('anomaly_summary', '')}\n"
            deep_dive_str += f"Root Cause: {result.get('root_cause', '')}\n"
            deep_dive_str += f"Recommended Action: {result.get('recommended_action', '')}\n"
    else:
        deep_dive_str = "No market-specific anomalies detected."

    prompt = f"""
    You are a senior sales analyst at an accounting SaaS company.
    Write a concise executive summary for the leadership team.

    ## Parameters
    Market: {context['params']['market']} | Period: {context['params']['start_date']} to {context['params']['end_date']}

    ## Overview Analysis
    {overview}

    ## Anomaly Detection Summary
    {anomaly['summary']}

    ## Anomalies Found
    {json.dumps(anomaly['anomalies'], indent=2) if anomaly['has_anomaly'] else "No anomalies detected."}

    ## Deep Dive Findings
    {deep_dive_str}

    ## Instructions
    - Write for a leadership audience — clear, concise, actionable
    - Must include specific numbers in every section
    - No bullet points, write in prose

    Write exactly these 3 sections separated by a divider:

    ────────────────────────────────────────────────────
    What Happened:
    [2-3 sentences — overall performance + key anomalies found]

    ────────────────────────────────────────────────────
    Why It Happened:
    [2-3 sentences — root causes from deep dive, specific market/segment/plan]

    ────────────────────────────────────────────────────
    What To Do:
    [3 prioritized actions, numbered 1-3, one sentence each]
    """

    result = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(temperature=0.4)
    ).text

    print("=" * 55)
    print("📝 EXECUTIVE SUMMARY")
    print("=" * 55)
    print(result)
    print("=" * 55)

    return result

def run_pipeline(market = ['All'], start_date = start_date, end_date = end_date):

    print("\n" + "=" * 55)
    print("🚀 PIPELINE STARTED")
    print(f"   Market: {market} | {start_date} to {end_date}")
    print("=" * 55 + "\n")

    #Step 1: Orchastrator
    print("⚙️  Step 1: Orchestrating data...\n")
    ctx = orchastrator(market=market, start_date=start_date, end_date=end_date)

    #Step 2: Overview
    print("⚙️  Step 2: Running Overview Agent...\n")
    overview = agent_overview(ctx)

    #Step 3: Anomaly detector
    print("⚙️  Step 3: Running Anomaly Detector...\n")
    anomaly = agent_anomaly_detector(ctx)

    #Step 4: Deep dive, only if anomaly is found
    deep_dive = {}

    if anomaly['has_anomaly']:
      print("⚙️  Step 4: Anomaly found, running Anomaly Detector...\n")
      deepdive = agent_deep_dive(anomaly, start_date=start_date, end_date=end_date)

    else:
      print("⚙️  Step 4: No anomalies — Skipping Deep Dive\n")

    #Step 5: Summary
    print("⚙️  Step 5: Running Summary Agent...\n")
    summary = agent_summary(context = ctx, overview = overview, deep_dive = deepdive, anomaly_result = anomaly)

    print("\n" + "=" * 55)
    print("✅ PIPELINE COMPLETE")
    print("=" * 55 + "\n")

    return {
        'context':   ctx,
        'overview':  overview,
        'anomaly':   anomaly,
        'deep_dive': deep_dive,
        'summary':   summary,
    }