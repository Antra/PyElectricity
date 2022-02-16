CREATE TABLE IF NOT EXISTS public.solar_forecast
(
    timestamp timestamptz primary key,
    pv_estimate numeric(6, 4),
    pv_estimate10 numeric(6, 4),
    pv_estimate90 numeric(6, 4)
);