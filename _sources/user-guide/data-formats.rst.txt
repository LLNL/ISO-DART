Data Formats Guide
==================

Overview
--------

ISO-DART saves all data in CSV format for maximum compatibility with analysis tools. This guide describes the structure and format of downloaded data files.

General CSV Format
------------------

All CSV files have:

- Header row with column names
- UTF-8 encoding
- Comma-separated values
- ISO-8601 date/time formats where applicable

File Naming Conventions
-----------------------

CAISO
~~~~~

Format: ``{start_date}_to_{end_date}_{query_name}_{data_item}.csv``

Examples:

- ``20240101_to_20240131_PRC_LMP_TH_NP15_GEN-APND.csv``
- ``20240101_to_20240131_SLD_FCST_CAISO_forecast.csv``
- ``20240101_to_20240131_ENE_WIND_SOLAR_SUMMARY_WIND_TOTAL_GEN_MW.csv``

MISO
~~~~

Format: ``miso_{data_type}_{date}.csv``

Examples:

- ``miso_da_exante_lmp_2024-01-01.csv``
- ``miso_fuel_mix_2024-01-01.csv``
- ``miso_rt_actual_load_2024-01-01.csv``

NYISO
~~~~~

Format: ``{start_date}_to_{end_date}_{dataid}_{aggregation}.csv``

Examples:

- ``20240101_to_20240131_damlbmp_zone.csv``
- ``20240101_to_20240131_rtfuelmix.csv``
- ``20240101_to_20240131_pal.csv``

SPP
~~~

Format: ``{start_date}_to_{end_date}_SPP_{market}_{data_type}_{location_type}.csv``

Examples:

- ``20240101_to_20240131_SPP_DA_LMP_SL.csv``
- ``20240101_to_20240131_SPP_RTBM_MCP.csv``
- ``20240101_to_20240131_SPP_Operating_Reserves.csv``

BPA
~~~

Format: ``{year}_BPA_{data_type}.csv``

Examples:

- ``2024_BPA_Wind_Generation_Total_Load.csv``
- ``2024_BPA_Reserves_Deployed.csv``

PJM
~~~

Format: ``{start_date}_to_{end_date}_{endpoint}.csv``

Examples:

- ``01-01-2024_to_01-31-2024_da_hrl_lmps.csv``
- ``01-01-2024_to_01-31-2024_hrl_load_metered.csv``

Weather
~~~~~~~

Format: ``{start_date}_to_{end_date}_{station_name}_{state}.csv``

Examples:

- ``2024-01-01_to_2024-01-31_San_Francisco_International_Airport_CA.csv``

Data Schemas
------------

CAISO LMP Data
~~~~~~~~~~~~~~

**File Pattern:** ``*_PRC_LMP_*.csv``

.. list-table::
   :header-rows: 1
   :widths: 25 15 35 25

   * - Column
     - Type
     - Description
     - Example
   * - ``INTERVALSTARTTIME_GMT``
     - datetime
     - Interval start (GMT)
     - ``2024-01-01T08:00:00Z``
   * - ``INTERVALENDTIME_GMT``
     - datetime
     - Interval end (GMT)
     - ``2024-01-01T09:00:00Z``
   * - ``OPR_DATE``
     - date
     - Operating date
     - ``2024-01-01``
   * - ``INTERVAL_NUM``
     - integer
     - Hour ending (1-24)
     - ``1``
   * - ``NODE_ID_XML``
     - string
     - Node ID (XML format)
     - ``TH_NP15_GEN-APND``
   * - ``NODE_ID``
     - string
     - Node ID
     - ``NP15``
   * - ``NODE``
     - string
     - Node name
     - ``NP15_GEN``
   * - ``MARKET_RUN_ID``
     - string
     - Market type
     - ``DAM``
   * - ``DATA_ITEM``
     - string
     - Data item identifier
     - ``TH_NP15_GEN-APND``
   * - ``VALUE``
     - float
     - LMP value ($/MWh)
     - ``32.45``
   * - ``MLC``
     - float
     - Marginal Loss Component
     - ``0.23``
   * - ``MCC``
     - float
     - Marginal Congestion Component
     - ``1.12``

**Sample Data:**

.. code-block:: text

   OPR_DATE,INTERVAL_NUM,DATA_ITEM,VALUE,MLC,MCC
   2024-01-01,1,TH_NP15_GEN-APND,32.45,0.23,1.12
   2024-01-01,2,TH_NP15_GEN-APND,29.87,-0.45,0.89

CAISO Load Forecast
~~~~~~~~~~~~~~~~~~~

**File Pattern:** ``*_SLD_FCST_*.csv``

.. list-table::
   :header-rows: 1
   :widths: 25 15 35 25

   * - Column
     - Type
     - Description
     - Example
   * - ``INTERVALSTARTTIME_GMT``
     - datetime
     - Interval start
     - ``2024-01-01T08:00:00Z``
   * - ``OPR_DATE``
     - date
     - Operating date
     - ``2024-01-01``
   * - ``INTERVAL_NUM``
     - integer
     - Hour ending
     - ``1``
   * - ``TAC_AREA_NAME``
     - string
     - Area name
     - ``CAISO``
   * - ``MARKET_RUN_ID``
     - string
     - Market type
     - ``DAM``
   * - ``VALUE``
     - float
     - Load (MW)
     - ``28500.0``

CAISO Wind/Solar Summary
~~~~~~~~~~~~~~~~~~~~~~~~~

**File Pattern:** ``*_ENE_WIND_SOLAR_SUMMARY_*.csv``

.. list-table::
   :header-rows: 1
   :widths: 25 15 35 25

   * - Column
     - Type
     - Description
     - Example
   * - ``INTERVALSTARTTIME_GMT``
     - datetime
     - Interval start
     - ``2024-01-01T08:00:00Z``
   * - ``OPR_DATE``
     - date
     - Operating date
     - ``2024-01-01``
   * - ``INTERVAL_NUM``
     - integer
     - 5-min interval (1-288)
     - ``97``
   * - ``DATA_ITEM``
     - string
     - Data type
     - ``WIND_TOTAL_GEN_MW``
   * - ``VALUE``
     - float
     - Generation (MW)
     - ``2450.0``

**Available DATA_ITEM values:**

- ``WIND_TOTAL_GEN_MW`` - Wind generation
- ``SOLAR_TOTAL_GEN_MW`` - Solar generation
- ``WIND_FORECAST_MW`` - Wind forecast
- ``SOLAR_FORECAST_MW`` - Solar forecast

MISO LMP Data
~~~~~~~~~~~~~

**File Pattern:** ``miso_*_lmp_*.csv``

.. list-table::
   :header-rows: 1
   :widths: 25 15 35 25

   * - Column
     - Type
     - Description
     - Example
   * - ``interval``
     - datetime
     - Timestamp
     - ``2024-01-01T00:00:00Z``
   * - ``node``
     - string
     - Pricing node
     - ``ALTW.WELLS1``
   * - ``lmp``
     - float
     - Total LMP ($/MWh)
     - ``25.34``
   * - ``mcc``
     - float
     - Congestion component
     - ``0.45``
   * - ``mlc``
     - float
     - Loss component
     - ``0.12``
   * - ``value``
     - float
     - LMP value
     - ``25.34``
   * - ``preliminaryFinal``
     - string
     - Data status
     - ``Final``

MISO Fuel Mix
~~~~~~~~~~~~~

**File Pattern:** ``miso_fuel_mix_*.csv``

.. list-table::
   :header-rows: 1
   :widths: 25 15 35 25

   * - Column
     - Type
     - Description
     - Example
   * - ``interval``
     - datetime
     - 5-min timestamp
     - ``2024-01-01T00:05:00Z``
   * - ``fuelType``
     - string
     - Fuel type
     - ``Coal``
   * - ``region``
     - string
     - MISO region
     - ``MISO``
   * - ``value``
     - float
     - Generation (MW)
     - ``8500.0``

**Fuel Types:** Coal, Gas, Nuclear, Wind, Solar, Hydro, Other

NYISO LBMP Data
~~~~~~~~~~~~~~~

**File Pattern:** ``*_damlbmp_zone.csv`` or ``*_realtime_zone.csv``

.. list-table::
   :header-rows: 1
   :widths: 25 15 35 25

   * - Column
     - Type
     - Description
     - Example
   * - ``Time Stamp``
     - datetime
     - Timestamp (ET)
     - ``01/01/2024 00:00:00``
   * - ``Name``
     - string
     - Zone name
     - ``N.Y.C.``
   * - ``LBMP ($/MWHr)``
     - float
     - Total LBMP
     - ``35.67``
   * - ``Marginal Cost Losses ($/MWHr)``
     - float
     - Loss component
     - ``0.89``
   * - ``Marginal Cost Congestion ($/MWHr)``
     - float
     - Congestion component
     - ``1.23``

**Zone Names:** CAPITL, CENTRL, DUNWOD, GENESE, H.Q, HUD VL, LONGIL, MHK VL, MILLWD, N.Y.C., NORTH, O.H., PJM, WEST

NYISO Fuel Mix
~~~~~~~~~~~~~~

**File Pattern:** ``*_rtfuelmix.csv``

.. list-table::
   :header-rows: 1
   :widths: 25 15 35 25

   * - Column
     - Type
     - Description
     - Example
   * - ``Time Stamp``
     - datetime
     - 5-min timestamp
     - ``01/01/2024 00:05:00``
   * - ``Time Zone``
     - string
     - Time zone
     - ``EST``
   * - ``Dual Fuel``
     - float
     - Generation (MW)
     - ``450.0``
   * - ``Natural Gas``
     - float
     - Generation (MW)
     - ``8500.0``
   * - ``Nuclear``
     - float
     - Generation (MW)
     - ``4200.0``
   * - ``Other Fossil Fuels``
     - float
     - Generation (MW)
     - ``120.0``
   * - ``Other Renewables``
     - float
     - Generation (MW)
     - ``850.0``
   * - ``Wind``
     - float
     - Generation (MW)
     - ``1200.0``
   * - ``Hydro``
     - float
     - Generation (MW)
     - ``2100.0``

SPP LMP Data
~~~~~~~~~~~~

**File Pattern:** ``*_SPP_*_LMP_*.csv``

.. list-table::
   :header-rows: 1
   :widths: 25 15 35 25

   * - Column
     - Type
     - Description
     - Example
   * - ``GMTIntervalEnd``
     - datetime
     - GMT interval end
     - ``2024-01-01T07:00:00``
   * - ``Settlement Location``
     - string
     - Location name
     - ``KCPL.HSTNS5``
   * - ``Pnode``
     - string
     - Physical node
     - ``KCPL.HSTNS5``
   * - ``LMP``
     - float
     - Total LMP ($/MWh)
     - ``28.45``
   * - ``MLC``
     - float
     - Loss component
     - ``0.34``
   * - ``MCC``
     - float
     - Congestion component
     - ``0.89``
   * - ``MEC``
     - float
     - Energy component
     - ``27.22``

Working with Data
-----------------

Loading in Python
~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pandas as pd

   # CAISO LMP
   df = pd.read_csv('data/CAISO/20240101_to_20240131_PRC_LMP_TH_NP15_GEN-APND.csv')
   df['OPR_DATE'] = pd.to_datetime(df['OPR_DATE'])

   # MISO with datetime index
   df = pd.read_csv('data/MISO/miso_da_exante_lmp_2024-01-01.csv')
   df['interval'] = pd.to_datetime(df['interval'])
   df.set_index('interval', inplace=True)

   # Weather data
   df = pd.read_csv('data/weather/2024-01-01_to_2024-01-31_San_Francisco_CA.csv',
                    index_col='time', parse_dates=True)

Loading in R
~~~~~~~~~~~~

.. code-block:: r

   # CAISO LMP
   library(readr)
   df <- read_csv('data/CAISO/20240101_to_20240131_PRC_LMP_TH_NP15_GEN-APND.csv')
   df$OPR_DATE <- as.Date(df$OPR_DATE)

   # MISO
   df <- read_csv('data/MISO/miso_da_exante_lmp_2024-01-01.csv')
   df$interval <- as.POSIXct(df$interval)

Excel Import
~~~~~~~~~~~~

1. Open Excel
2. Data → From Text/CSV
3. Select file
4. Verify delimiter is comma
5. Import

Database Import
~~~~~~~~~~~~~~~

.. code-block:: sql

   -- PostgreSQL
   COPY caiso_lmp FROM '/path/to/file.csv' DELIMITER ',' CSV HEADER;

   -- SQLite
   .mode csv
   .import data/CAISO/file.csv caiso_lmp

Data Quality Checks
-------------------

Validate Date Ranges
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pandas as pd

   df = pd.read_csv('your_file.csv')
   df['OPR_DATE'] = pd.to_datetime(df['OPR_DATE'])

   # Check for gaps
   date_range = pd.date_range(df['OPR_DATE'].min(), df['OPR_DATE'].max(), freq='D')
   missing_dates = set(date_range) - set(df['OPR_DATE'])
   if missing_dates:
       print(f"Missing dates: {missing_dates}")

Check for Nulls
~~~~~~~~~~~~~~~

.. code-block:: python

   null_counts = df.isnull().sum()
   print(null_counts[null_counts > 0])

Validate Intervals
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Check hourly data has 24 intervals per day
   intervals_per_day = df.groupby('OPR_DATE')['INTERVAL_NUM'].nunique()
   irregular_days = intervals_per_day[intervals_per_day != 24]
   if len(irregular_days) > 0:
       print(f"Irregular days: {irregular_days}")

Time Zones
----------

CAISO
~~~~~

- All times in Pacific Time (PT)
- GMT columns provided for UTC reference
- Handles DST automatically (23 or 25 hours)

MISO
~~~~

- All times in Central Time (CT)
- ISO 8601 format with UTC offset

NYISO
~~~~~

- All times in Eastern Time (ET)
- Time zone column included

SPP
~~~

- GMT timestamps
- Central Time implicit

PJM
~~~

- Eastern Prevailing Time (EPT)
- Includes DST handling

Next Steps
----------

- See :doc:`python-api` for data processing examples
- See :doc:`../tutorials/examples/index` for analysis examples