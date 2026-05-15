import duckdb
import pandas as pd
import json

# Load data
df_revenue  = pd.read_csv('data/monthly_revenue_v2.csv')
df_customer = pd.read_csv('data/customers_v2.csv')
df_churn    = pd.read_csv('data/monthly_churn.csv')

with open('data/schema.json') as f:
    schema = json.load(f)

# Register DuckDB tables
con = duckdb.connect()
con.register('monthly_revenue', df_revenue)
con.register('monthly_churn', df_churn)
con.register('customers', df_customer)

def run_query(sql):
    return con.execute(sql).df()

def orchastrator(market= ['All'], start_date=start_date, end_date=end_date) -> dict:

  #market filter
  if market == ['All']:

    market_list = tuple(df_revenue['market'].unique())

  else:
    market_list = tuple(market)

  mrr_trend=f"""

  select
    month
    ,market
    ,segment
    ,plan
    ,product
    ,event_type
    ,sum(mrr) as monthly_revenue
  from monthly_revenue
  where
    product != 'Incorporation'
    and month between substring('{start_date}',1,7) and substring('{end_date}',1,7)
    and market in {market_list}
  group by month, market, segment, plan, product, event_type

  """

  churn_query = f"""

  select
    churn_month as month
    ,market
    ,segment
    ,plan
    ,churn_reason_category
    ,sum(mrr_lost) as monthly_mrr_lost
    ,count(customer_id) as customers_lost
  from monthly_churn
  where
    churn_month between substring('{start_date}',1,7) and substring('{end_date}',1,7)
    and market in {market_list}
  group by churn_month, market, segment, plan, churn_reason_category

  """

  cac_ltv_query = f"""
  SELECT
      acquisition_channel,
      market,
      segment,
      AVG(cac) as avg_cac,
      AVG(ltv) as avg_ltv,
      AVG(ltv / cac) as ltv_cac_ratio,
      COUNT(customer_id) as customers
  FROM customers
  WHERE market IN {market_list}
  AND signup_date BETWEEN '{start_date}' AND '{end_date}'
  GROUP BY acquisition_channel, market, segment
  ORDER BY avg_cac DESC
  """

  df_mrr_trend = run_query(mrr_trend)
  df_churn_trend = run_query(churn_query)
  df_cac_trend = run_query(cac_ltv_query)

  return {
      'params': {'market': market_list, 'start_date': start_date, 'end_date': end_date},
      'schema': schema,
      'mrr_data': df_mrr_trend.to_dict(orient='records'),
      'churn_data': df_churn_trend.to_dict(orient='records'),
      'cac_data': df_cac_trend.to_dict(orient='records')
  }