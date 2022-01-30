CREATE TABLE IF NOT EXISTS public.inverter_data
(
    timestamp timestamptz primary key,
    p_battery numeric(7, 2),
    p_grid numeric(7, 2),
    p_local numeric(7, 2),
    p_solar numeric(7, 2),
    pct_selfsufficient numeric(4, 1),
    pct_autonomy numeric(4, 1),
    p_total numeric(7, 2),
    battery_state numeric(4, 1),
    battery_state_norm numeric(4, 1)
);