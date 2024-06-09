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


def _get_device_data(dev_id=None):
    """helper method to get the device data from the database, filtered by dev_id"""
    engine = get_engine()

    if dev_id is not None:
        query = f"""SELECT * FROM consumption where device_location != '' and dev_id={dev_id}"""
    else:
        query = f"""SELECT * FROM consumption where device_location != ''"""

    return pd.read_sql(query, engine, parse_dates=['timestamp'], dtype={'dev_id': int}, index_col='timestamp').sort_index(ascending=True)


def get_data(dev_id):
    """get the data and return it as a dataframe"""
    df = _get_device_data(dev_id=dev_id)

    # resample to seconds and fill with previous value -- assumping just single device_location
    location = df['device_location'].unique()[0]
    df.drop(columns=['dev_id', 'device_id',
                     'device_location', 'comment'], inplace=True)
    df = df.resample('S').mean().bfill()
    df['location'] = location

    cols = ['amps', 'watts', 'volts', 'location']

    return df[cols]


def enrich_df(df):
    # add the watt diff from previous row
    df['watt_diff'] = df['watts'].diff(periods=-1)

    # where are we at 0 watts and the following row has a non-zero watt? that should be our start of cycles (and maybe resume cycles?)
    df['cycle_start'] = (df['watts'] == 0.0) & (df['watt_diff'] < 0)

    # when we're at non-zero watts and the following row goes to zero that should be the end of our cycle - if the next 2 mins are also 0 .. otherwise I presume we just opened it quickly and restarted it
    df['cycle_ended_check'] = df['watts'].rolling(
        300).sum().shift(-300).fillna(0)
    df['cycle_ended'] = (df['watts'] > 0) & (
        df['watts'] - df['watt_diff'] == 0) & (df['cycle_ended_check'] == 0)

    return df


def get_cycles(df, print_pairs=False):
    starts = df[df['cycle_start']].index
    ends = df[df['cycle_ended']].index

    paired_starts = []
    paired_ends = []

    try:
        for start in starts:
            # Find the closest end after the start
            end = ends[ends > start].min()
            duration = (end-start).seconds
            # Check if there's a valid end and duration is more than 90 mins
            if end is not pd.NaT and end not in paired_ends and duration > 5400:
                paired_starts.append(start)
                paired_ends.append(end)

        assert (len(paired_starts) == len(paired_ends))

    except AssertionError as e:
        print(
            f"Assertion error, paired_start and end lengths don't match: {e}")
        logger.error(
            "*** PyElectricity: Assertion error, paired_start and end lengths don't match: {} ***".format(e))

    if print_pairs:
        # Print the paired indices
        for start, end in zip(paired_starts, paired_ends):
            print("Start:", start, "End:", end)

    # return a df with just the period data
    # each column is a cycle and the index is the duration in seconds
    temp_dict = {}
    for start, end in zip(paired_starts, paired_ends):
        new_series = pd.Series(df['watts'].loc[start:end].values)
        col_name = start.strftime('%Y-%m-%d %H:%M')
        temp_dict[col_name] = new_series

    return pd.DataFrame(temp_dict).fillna(0)


def detailed_line_plot(df, location, display=False):
    start = pd.to_datetime(df.columns[0]).strftime('%y-%m-%d')
    end = pd.to_datetime(df.columns[-1]).strftime('%y-%m-%d')

    fig = px.line(df, x=(df.index)/60, y=df.columns, labels={"x": "Time (minutes)", "value": "Power consumption (Watts)", "variable": "Data records"},
                  title=f"Power consumption for {location} from {start} to {end}")

    if display:
        fig.show()

    return fig


def summary_line_plot(df, location, n_clusters=3, display=False):
    start = pd.to_datetime(df.columns[0]).strftime('%y-%m-%d')
    end = pd.to_datetime(df.columns[-1]).strftime('%y-%m-%d')

    # let's use KMeans to cluster the data and find the various kinds of cycles
    scaler = MinMaxScaler()
    df_scaled = scaler.fit_transform(df.transpose())
    # may need to come back here with Elbow method to find the true n
    kmeans = KMeans(n_clusters=n_clusters).fit(df_scaled)
    # the clusters are here, seems to fit pretty well for pattern detection for the dishwasher at least
    # kmeans.labels_

    df_transposed = df.transpose()
    df_transposed['cluster'] = kmeans.labels_
    cluster_averages = df_transposed.groupby('cluster').mean()

    # transpose back for easier plotting
    cluster_averages_transposed = cluster_averages.transpose()

    fig = px.line(cluster_averages_transposed, x=(cluster_averages_transposed.index/60), y=cluster_averages_transposed.columns,
                  labels={"x": "Time (minutes)",
                          "value": "Power consumption (Watts)",
                          "variable": "Cluster"},
                  title=f"Average power consumption for {location} from {start} to {end}"
                  )

    # add the total consumption to the legend
    newnames = {
        str(col): f"{col} (usage: {round(cluster_averages_transposed[col].sum()/1000)} kW)" for col in cluster_averages_transposed.columns}

    fig.for_each_trace(lambda t: t.update(name=newnames[t.name],
                                          legendgroup=newnames[t.name],
                                          hovertemplate=t.hovertemplate.replace(
        t.name, newnames[t.name]))
    )

    if display:
        fig.show()

    return fig


def _old_plotter_with_graph_objects():
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


def _how_many_clusters():
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


# find the periods with activity
# isolate individual runs... allow a custom timebound but default to 3.5 hrs?
# create new df with individual runs from time 0 (showing the run time) - but keep the old timestamps around for ensuring we don't recalculate the same timeperiods again and again?
# plot/save the data
if __name__ == '__main__':
    logger.info('*** PyElectricity: Computation starting ***')

    devices = [0, 1, 2]

    for dev_id in devices:
        df = get_data(dev_id=dev_id)
        location = df['location'].unique()[0]
        df = enrich_df(df)
        df = get_cycles(df)
        detailed_line_plot(df, location=location, display=True)
        summary_line_plot(df, location=location, display=True)

    logger.info('*** PyElectricity: Computation terminating ***')


# -- update the device_location for the devices
# update consumption
# set device_location = 'dishwasher'
# where dev_id = 0;
# --where device_id = 'bfe9b69f55e0b386f4xskd';
# update consumption
# set device_location = 'laundry machine'
# where dev_id = 1;
# --where device_id = 'bf88d12bd0ee2e2fe86azg';
# update consumption
# set device_location = 'drier'
# where dev_id = 2;
# --where device_id = 'bfc6b71faed5d7662f3enx';
# update consumption
# set device_location = 'quooker'
# where dev_id = 3;
# --where device_id = 'bfbcf3f9da753b993b0iog';
# update consumption
# set device_location = ''
# where dev_id = 4;
# --where device_id = 'bf599cac3e497a0dcaa0md;
# update consumption
# set device_location = ''
# where dev_id = 5
# --where device_id = 'bf10a4565febd19132yrzs';


# select dev_id, device_location, count(*) from consumption
# group by 1, 2
# order by 1 asc, 2 desc
