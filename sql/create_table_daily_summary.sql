CREATE TABLE IF NOT EXISTS public.daily_summary
(
    date date primary key,
    min_battery numeric(7, 2),
    max_battery numeric(7, 2),
    min_battery_raw numeric(7, 2),
    max_battery_raw numeric(7, 2),
    first_1kw timestamptz,
    last_1kw timestamptz,
    first_2kw timestamptz,
    last_2kw timestamptz,
    first_prod timestamptz,
    last_prod timestamptz,
    peak_solar numeric(7, 2),
    daily_total numeric(6, 0),
    daily_solar_est numeric(6, 0),
);