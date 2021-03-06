# PyElectricity
Small basic recorder tool for gathering up electricity stats and storing them in a recording DB.

My setup consists of:
- `Fronius Symo Hybrid 5.0-3-S` (5kW inverter)
- `20x MaysunSolar 310Wp panels` (approx. 6kW peak effect)
- `Smart Meter 63A` (electricity meter)
- `Datalogger module` (logger/uploader to Fronius)
- `LG Resu H` (9800Wh battery)
- `PostgreSQL 13` (database running via Docker)
- `Raspberry Pi 3b+` (executing the scripts, runs Raspbian Linux)
