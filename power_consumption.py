import tinytuya
from datetime import datetime as dt
from pytz import timezone
from config import setup_logger, get_engine, tuya_device_config, tuya_device_count, TIME_FORMAT, freq
from sqlalchemy import text
from time import sleep

logger = setup_logger('Consumption', level='INFO')
logger.info('*** PyElectricity: Consumption starting ***')


def _setup(dev_config):
    devices = []

    for dev_id in range(1, tuya_device_count+1):
        try:
            device_list = [
                dev_config[f'device{dev_id}_id'], dev_config[f'device{dev_id}_key']]
            if all(device_list) and not any(config == 'place_key_here' for config in device_list):
                devices.append(tinytuya.OutletDevice(
                    dev_id=device_list[0],
                    address='Auto',
                    local_key=device_list[1],
                    version=3.3
                ))
        except:
            logger.info(
                f'** Consumption: Device#{dev_id} ({dev_config[f"device{dev_id}_id"]}) not found, skipping')

    return devices


def _store(timestamp, dev_id, device_id, amps, watts, volts, device_location=None, comment=None):
    try:
        engine = get_engine()
        # delete existing values
        delete_query = f"""DELETE FROM consumption WHERE timestamp = '{timestamp.strftime(TIME_FORMAT)}'"""
        query = f"""
                INSERT INTO consumption (timestamp,
                                        dev_id,
                                        device_id,
                                        amps,
                                        watts,
                                        volts,
                                        device_location,
                                        comment)
                            VALUES (
                                '{timestamp.strftime(TIME_FORMAT)}',
                                {dev_id},
                                '{device_id}',
                                {amps},
                                {watts},
                                {volts},
                                '{device_location or ""}',
                                '{comment or ""}'
                                ); """

        with engine.begin() as conn:
            # wrap query in text() when executing, https://stackoverflow.com/questions/69490450/objectnotexecutableerror-when-executing-any-sql-query-using-asyncengine
            conn.execute(text(delete_query))
            conn.execute(text(query))
            conn.commit()

        logger.debug(
            f'** Consumption: Data written to DB: {timestamp.strftime(TIME_FORMAT)} for device#{dev_id}, {device_id}')

    except Exception as err:
        logger.error(
            f'** Consumption: Error writing consumption data to DB! Error message: {err}')


def _update(device, id=None):
    update = device.updatedps()
    stats = device.status().get('dps', {})

    if not update:
        update = stats

    amps = (update.get('dps', {}).get('18', None) or stats.get('18', 0)) / 1000
    watts = (update.get('dps', {}).get('19', None) or stats.get('19', 0)) / 10
    volts = (update.get('dps', {}).get('20', None) or stats.get('20', 0)) / 10

    timestamp = dt.fromtimestamp(update.get(
        't', dt.now().timestamp()), timezone('UTC')).astimezone()

    if not watts or watts == 0:
        watts = amps * volts

    _store(timestamp=timestamp, dev_id=id, device_id=device.id,
           amps=amps, watts=watts, volts=volts)


if __name__ == '__main__':
    logger.info('*** Consumption: Looking for smart devices to record from ***')
    DEVICES = _setup(tuya_device_config)
    logger.info(
        '*** Consumption: Found %d device(s) in total - starting the recording loop ***', len(DEVICES))
    # TODO: can we run in permanent loop here? It didn't work for solar_panels.py on the RPi, but is it better from Docker? -- if nothing else, how do we ensure that we re-discover the devices if they are added/removed?
    while True:
        for id, dev in enumerate(DEVICES):
            # actual handling
            _update(device=dev, id=id)

        sleep(freq)
