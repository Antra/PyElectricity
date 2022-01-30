CREATE TABLE IF NOT EXISTS public.price_data
(
    timestamp timestamptz primary key,
    price numeric(7, 2),
    rolling_sum numeric(7, 2),
    currency varchar(3)
);