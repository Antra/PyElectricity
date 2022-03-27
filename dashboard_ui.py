import streamlit as st
import pandas as pd
from config import setup_logger
from dashboard_data import get_battery_state, get_solar_prediction, get_sunrise
import plotly.graph_objects as go
from datetime import datetime as dt
from datetime import timedelta
import matplotlib.pyplot as plt

# importing Streamlit seems to make logging happen to the console, but it's also logged to the file as usual
logger = setup_logger('Dashboard UI', level='INFO')
#logger.info('*** PyElectricity: Dashboard UI starting ***')

# Get data
base_date = dt.utcnow().date()


battery = get_battery_state()
battery_pct = battery['battery_state_norm'].values[0]
battery_pct_1hr_old = battery[battery['timestamp'] > battery['timestamp'].max(
) - timedelta(hours=+1)]['battery_state_norm'].values[-1]


solar = get_solar_prediction(base_date).rename(
    columns={'pv_estimate': 'Estimate',
             'pv_estimate10': 'Pessimistic',
             'pv_estimate90': 'Optimistic'}).set_index('timestamp')

sunrise, sunset = get_sunrise(base_date)


# Define the page
st.title('Solar and Weather data')

st.write(
    f"Today's sunrise was at {sunrise.time()}, and the sun will set at {sunset.time()}")

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
#plt.legend(loc="upper right")
plt.legend(bbox_to_anchor=(1, 1))
plt.ylim(0, 5.5)
st.pyplot(fig, use_container_width=True)


#logger.info('*** PyElectricity: Dashboard UI terminating ***')
