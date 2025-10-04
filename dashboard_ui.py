import streamlit as st
import pandas as pd
from config import setup_logger
from dashboard_data import get_battery_state, get_solar_prediction, get_sunrise, get_prices
import plotly.graph_objects as go
from datetime import datetime as dt
from datetime import timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pytz

# importing Streamlit seems to make logging happen to the console, but it's also logged to the file as usual
logger = setup_logger('Dashboard UI', level='INFO')
# logger.info('*** PyElectricity: Dashboard UI starting ***')

# Get data
timezone = 'Europe/Copenhagen'

base_date = dt.utcnow().date()

battery = get_battery_state()
battery_pct = battery['battery_state_norm'].values[0]
battery_pct_1hr_old = battery[battery['timestamp'] > battery['timestamp'].max(
) - timedelta(hours=+1)]['battery_state_norm'].values[-1]


solar = get_solar_prediction(base_date).rename(
    columns={'pv_estimate': 'Estimate',
             'pv_estimate10': 'Pessimistic',
             'pv_estimate90': 'Optimistic'}).set_index('timestamp')

sunrise, sunset, summary = get_sunrise(base_date)
# streamlit doesn't handletimezones well; so hardcoding it
sunrise = sunrise.astimezone(tz=pytz.timezone(timezone))
sunset = sunset.astimezone(tz=pytz.timezone(timezone))


prices = get_prices(base_date, limit=1000, tz=timezone)
# hardcoding the timezone for now; not supported well in Streamlit currently
# dropping the tzinfo afterwards; so it's displayed correctly in the Matplotlib plot
prices = prices[prices['timestamp'] > pd.Timestamp(
    'today').tz_localize(tz=timezone) - timedelta(hours=+1)]
prices['timestamp'] = pd.to_datetime(
    prices['timestamp'].dt.tz_convert(tz=timezone)).dt.tz_localize(None)

# and add a helper for our vertical line
prices['hour'] = prices['timestamp'].dt.hour
midnight_index = None
if prices[(prices['hour'] == 0) & (prices.index != 0)].shape[0] > 0:
    midnight_index = prices[(prices['hour'] == 0) &
                            (prices.index != 0)].index[0]
price_currency = prices['currency'].values[0]


# Define the page
st.title('Solar and Weather data')

st.write(
    f"Today's sunrise was at {sunrise.time()}, and the sun will set at {sunset.time()}.  \nAccording to the weather forecast: {summary}.")

# Battery Gauge - Plotly
fig = go.Figure(go.Indicator(
    domain={'x': [0, 1], 'y': [0, 1]},
    value=battery_pct,
    mode="gauge+number+delta",
    title={'text': "Battery percentage"},
    delta={'reference': battery_pct_1hr_old},
    gauge={'axis': {'range': [None, 100]},
           'steps': [
        {'range': [0, 85], 'color': "lightgray"},
        {'range': [85, 100], 'color': "gray"}],
        'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 85}}))
fig.add_annotation(text='battery level compared to 1hr ago<br>at 85% with maximum sun, battery is full in 20 mins',
                   align='left',
                   showarrow=False,
                   xref='paper',
                   yref='paper',
                   x=0.25,
                   y=-0.09,
                   bordercolor='black',
                   borderwidth=1)
st.plotly_chart(fig, use_container_width=True)


# Solar predictions - Matplotlib
fig, ax = plt.subplots()
ax.plot(solar.index, solar['Estimate'],
        color='blue', linewidth=2.0, label='Estimate')
ax.plot(solar.index, solar['Optimistic'],
        color='green', linewidth=2.0, label='Optimistic')
ax.plot(solar.index, solar['Pessimistic'],
        color='red', linewidth=2.0, label='Pessimistic')
ax.axvline(x=dt.utcnow(), color='grey', linestyle='--', label='right now')
ax.set_title('Solar production predictions for the next few days')
ax.set_xlabel('Today and next two days')
ax.set_ylabel('Estimated solar production (kW)')
# plt.legend(loc="upper right")
plt.legend(bbox_to_anchor=(1, 1))
plt.ylim(0, 5.5)
st.pyplot(fig)


# Power price
fig, ax = plt.subplots()
prices['price'] = prices['price'] + prices['offset']
ax.plot(prices['timestamp'], prices['price'], color='blue',
        linewidth=2.0, label='raw electricity price')

ax.set_title('Electricity price incl. net tariff')


if prices["timestamp"].min().date() == prices["timestamp"].max().date():
    x_label = f'{prices["timestamp"].min().date()}'
else:
    x_label = f'{prices["timestamp"].min().date()} to {prices["timestamp"].max().date()}'
ax.set_xlabel(x_label)
ax.set_ylabel(f'Price ({price_currency})')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.xticks(rotation=-45, fontsize=5)
if midnight_index:
    ax.axvline(x=prices[prices.index == midnight_index]['timestamp'], color='grey',
               linestyle='--', label='midnight')

ax.axhline(y=0.65, color='pink', linestyle='--', label='cheap')
plt.legend(bbox_to_anchor=(1, 1))
st.pyplot(fig)

# logger.info('*** PyElectricity: Dashboard UI terminating ***')
