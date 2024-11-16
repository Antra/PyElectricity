CREATE TABLE IF NOT EXISTS public.weather_hourly
(
    date timestamptz primary key,
    temp numeric(6, 2),
    feels_like numeric(6, 2),
    pressure numeric(6, 0),
    humidity numeric(3, 0),
    dew_point numeric(6, 2),
    uvi numeric(6, 2),
    clouds numeric(3, 0),
    visibility numeric(6, 0),
    wind_speed numeric(6, 2),
    wind_deg numeric(3, 0),
    wind_gust numeric(6, 2),
    pop numeric(6, 2),
    id numeric(3, 0),
    main varchar(20),
    description varchar(50),
    icon varchar(5),
    rain numeric(6, 2),
    snow numeric(6, 2),
    during_day boolean
);


CREATE TABLE IF NOT EXISTS public.weather_sunrise
(
    date date primary key,
    sunrise timestamptz,
    sunset timestamptz,
    summary varchar(125)
);