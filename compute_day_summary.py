import numpy as np
import pandas as pd
from datetime import timedelta
from datetime import datetime as dt
from config import setup_logger, get_engine
from sqlalchemy import text

logger = setup_logger('Computation', level='INFO')
logger.info('*** PyElectricity: Computation starting ***')

yesterday = dt.utcnow() - timedelta(hours=24)
now = dt.utcnow()

# get the newest date we have data for
engine = get_engine()
query = f"""SELECT max(date) FROM daily_summary"""
with engine.connect() as conn:
    # wrap query in text() when executing, https://stackoverflow.com/questions/69490450/objectnotexecutableerror-when-executing-any-sql-query-using-asyncengine
    newest_date = conn.execute(text(query)).fetchone()[0]


query = f"""-- diary query with battery and first/last 1kW+2kW
            with day_min_max1kw as (select cast(timestamp as date) as diary_date, min(timestamp) as first_time, max(timestamp) as last_time
            from public.inverter_data
            where p_solar >= 1000
            group by 1),
            day_min_max2kw as (select cast(timestamp as date) as diary_date, min(timestamp) as first_time, max(timestamp) as last_time
            from public.inverter_data
            where p_solar >= 2000
            group by 1),
            day_first_last as (select cast(timestamp as date) as diary_date, min(timestamp) as first_time, max(timestamp) as last_time
            from public.inverter_data
            where p_solar >= 50
            group by 1
            ),
            battery as (select cast(timestamp as date) as diary_date, min(battery_state) as min_battery_raw, max(battery_state) as max_battery_raw, min(battery_state_norm) as min_battery, max(battery_state_norm) as max_battery
            from public.inverter_data
            group by 1
            )
            select
                cast(inv.timestamp as date) as diary_date,
                batt.min_battery_raw,
                batt.max_battery_raw,
                batt.min_battery,
                batt.max_battery,
                day1kw.first_time as first_1kw,
                day1kw.last_time as last_1kw,
                day2kw.first_time as first_2kw,
                day2kw.last_time as last_2kw,
                first_last.first_time as first_prod,
                first_last.last_time as last_prod,
                max(p_solar) as peak_solar,
                max(e_day) as daily_total
            from public.inverter_data inv
            left join day_min_max1kw day1kw on cast(inv.timestamp as date) = day1kw.diary_date
            left join day_min_max2kw day2kw on cast(inv.timestamp as date) = day2kw.diary_date
            left join day_first_last first_last on cast(inv.timestamp as date) = first_last.diary_date
            left join battery batt on cast(inv.timestamp as date) = batt.diary_date
            where inv.timestamp < '{now.date()}'
            and inv.timestamp > '{newest_date + timedelta(days=1)}'
            group by 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
            order by 1 asc
"""

summary = pd.read_sql(query, engine)
summary['diary_date'] = summary['diary_date'].astype(str)

int_cols = ['daily_total']

for col in int_cols:
    summary[col] = summary[col].fillna(0).astype(int)


summary.rename(columns={'diary_date': 'date'}, inplace=True)

# add the estimated solar production
# this pretty close to what Solarweb reports; some difference, but precise enough to be within ~0.5kWh, always below on the dates I've tested
query = f"""SELECT timestamp, p_solar from public.inverter_data where timestamp < '{str((pd.to_datetime(summary.date.max()) + timedelta(days=1)).date())}' and timestamp >= '{summary.date.min()}'"""
details = pd.read_sql(query, engine).set_index(
    'timestamp').resample('S').bfill()
est_dict = {str(k): v for k, v in details.groupby(details.index.date)[
    'p_solar'].agg(lambda x: x.sum()/3600000).to_dict().items()}
summary['daily_solar_est'] = summary['date'].map(est_dict).fillna(0)

# sort the symmary and commit it
summary.sort_values(by='date', ascending=True, ignore_index=True, inplace=True)
summary.to_sql('daily_summary', engine, if_exists='append', index=False)

logger.info('*** PyElectricity: Computation terminating ***')
