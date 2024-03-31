import pandas as pd
from datetime import timedelta
from config import setup_logger, get_engine
import plotly.graph_objects as go
import plotly.express as px

from sklearn.cluster import KMeans
from sklearn.preprocessing import MinMaxScaler
from yellowbrick.cluster import KElbowVisualizer
from yellowbrick.cluster import SilhouetteVisualizer

logger = setup_logger('Computation', level='INFO')
logger.info('*** PyElectricity: Computation starting ***')

# get the newest date we have data for


def get_device_data(dev_id=None):
    engine = get_engine()

    if dev_id is not None:
        query = f"""SELECT * FROM consumption where device_location != '' and dev_id={dev_id}"""
    else:
        query = f"""SELECT * FROM consumption where device_location != ''"""

    return pd.read_sql(query, engine, parse_dates=['timestamp'], dtype={'dev_id': int}, index_col='timestamp').sort_index(ascending=True)


df = get_device_data(dev_id=0)
# resample to seconds and fill with previous value -- assumping just single device_location (otherwise split by location first)
location = df['device_location'].unique()[0]
df.drop(columns=['dev_id', 'device_id',
        'device_location', 'comment'], inplace=True)
df = df.resample('S').mean().bfill()
df['device_location'] = location


# find the periods with activity
# isolate individual runs... allow a custom timebound but default to 3.5 hrs?
# create new df with individual runs from time 0 (showing the run time) - but keep the old timestamps around for ensuring we don't recalculate the same timeperiods again and again?
# plot/save the data
logger.info('*** PyElectricity: Computation terminating ***')


# identify start of dishwasher cycle
# add the watt diff from previous row
df['watt_diff'] = df['watts'].diff(periods=-1)

# where are we at 0 watts and the following row has a non-zero watt? that should be our start of cycles (and maybe resume cycles?)
df['cycle_start'] = (df['watts'] == 0.0) & (df['watt_diff'] < 0)

# when we're at non-zero watts and the following row goes to zero that should be the end of our cycle - if the next 2 mins are also 0 .. otherwise I presume we just opened it quickly and restarted it
df['cycle_ended_check'] = df['watts'].rolling(300).sum().shift(-300).fillna(0)
df['cycle_ended'] = (df['watts'] > 0) & (
    df['watts'] - df['watt_diff'] == 0) & (df['cycle_ended_check'] == 0)


# all the starts and all the ends
starts = df[df['cycle_start']].index
ends = df[df['cycle_ended']].index

paired_starts = []
paired_ends = []

try:
    for start in starts:
        end = ends[ends > start].min()  # Find the closest end after the start
        duration = (end-start).seconds
        # Check if there's a valid end and duration is more than 90 mins
        if end is not pd.NaT and end not in paired_ends and duration > 5400:
            paired_starts.append(start)
            paired_ends.append(end)

    assert (len(paired_starts) == len(paired_ends))

except AssertionError as e:
    print(f"Assertion error, paired_start and end lengths don't match: {e}")
    logger.error(
        "*** PyElectricity: Assertion error, paired_start and end lengths don't match: {} ***".format(e))

# Print the paired indices
# for start, end in zip(paired_starts, paired_ends):
#    print("Start:", start, "End:", end)

# quick plotter using plotly's px
temp_dict = {}
for start, end in zip(paired_starts, paired_ends):
    new_series = pd.Series(df['watts'].loc[start:end].values)
    col_name = start.strftime('%Y-%m-%d %H:%M')
    temp_dict[col_name] = new_series

df1 = pd.DataFrame(temp_dict).fillna(0)

# fig = px.line(df1, x=(df1.index)/60, y=df1.columns)
fig = px.line(df1, x=(df1.index)/60, y=df1.columns, labels={"x": "Time (minutes)", "value": "Power consumption (Watts)", "variable": "Data records"},
              title=f"Power consumption for {location} from {paired_starts[0].strftime('%Y-%m-%d')} to {paired_ends[-1].strftime('%Y-%m-%d')}")
fig.show()


# let's use KMeans to cluster the data and find the various kinds of cycles
scaler = MinMaxScaler()
df_scaled = scaler.fit_transform(df1.transpose())
# may need to come back here with Elbow method to find the true n
n_clusters = 3
kmeans = KMeans(n_clusters=n_clusters, random_state=0).fit(df_scaled)
# the clusters are here, seems to fit pretty well for pattern detection for the dishwasher at least
# kmeans.labels_

# let's create an average of the clusters and plot it too
df_transposed = df1.transpose()
df_transposed['cluster'] = kmeans.labels_
cluster_averages = df_transposed.groupby('cluster').mean()

# transpose back for easier plotting
cluster_averages_transposed = cluster_averages.transpose()

fig = px.line(cluster_averages_transposed, x=(cluster_averages_transposed.index/60), y=cluster_averages_transposed.columns,
              labels={"x": "Time (minutes)",
                      "value": "Power consumption (Watts)",
                      "variable": "Cluster"},
              title=f"Average power consumption for {location} from {paired_starts[0].strftime('%Y-%m-%d')} to {paired_ends[-1].strftime('%Y-%m-%d')}"
              )

# add the total consumption to the legend
newnames = {
    str(col): f"{col} (usage: {round(cluster_averages_transposed[col].sum()/1000)} kW)" for col in cluster_averages_transposed.columns}

fig.for_each_trace(lambda t: t.update(name=newnames[t.name],
                                      legendgroup=newnames[t.name],
                                      hovertemplate=t.hovertemplate.replace(
                                          t.name, newnames[t.name])
                                      )
                   )

fig.show()


# old stuff below

# elbow method, figuring out the n_clusters value
km = KMeans(random_state=42)
visualiser = KElbowVisualizer(km, k=(2, 10))
visualiser.fit(df_scaled)
visualiser.show()

# and with silhuette method
fig, ax = plt.subplots(3, 2, figsize=(15, 8))
for i in [2, 3, 4, 5]:
    km = KMeans(n_clusters=i, init='k-means++',
                n_init=10, max_iter=100, random_state=42)
    q, mod = divmod(i, 2)
    visualiser = SilhouetteVisualizer(
        km, colors='yellowbrick', ax=ax[q-1][mod])
    visualiser.fit(df_scaled)

visualiser.show()

# old manual plotting with graph_objects
fig = go.Figure()

# Add traces for each start-end pair
for i, (start, end) in enumerate(zip(paired_starts, paired_ends)):
    watt_data = df['watts'].loc[start:end]
    time_diff = (end - start).total_seconds()
    x_values = [round(((timestamp - start).total_seconds())/60, 2)
                for timestamp in df[start:end+timedelta(seconds=60)].index if start <= timestamp <= end]
    y_values = df['watts'].loc[start:end]
    fig.add_trace(go.Scatter(x=x_values, y=y_values,
                  mode='lines', name=f'Record #{i}'))

# Update layout
fig.update_layout(
    title="Power consumption",
    xaxis_title="Time (minutes)",
    yaxis_title="Power consumption (Watts)",
    showlegend=True
)

# Show plot
fig.show()
