CAISO Data Guide
================

Overview
--------

The California Independent System Operator (CAISO) manages the bulk of California's power grid and operates one of the most transparent electricity markets in the world. ISO-DART provides comprehensive access to CAISO's OASIS API, covering pricing, load, generation, and market operations data.

Quick Reference
---------------

.. list-table::
   :header-rows: 1
   :widths: 25 20 25 30

   * - Data Category
     - Update Frequency
     - Historical Availability
     - Typical File Size
   * - LMP (DAM)
     - Daily
     - 2009-present
     - 50-100 MB/month
   * - LMP (RTM)
     - 5-min intervals
     - 2009-present
     - 200-400 MB/month
   * - Load Forecast
     - Hourly
     - 2010-present
     - 5-10 MB/month
   * - Wind & Solar
     - 5-min intervals
     - 2015-present
     - 20-30 MB/month
   * - Fuel Prices
     - Daily
     - 2014-present
     - <1 MB/month

CAISO Markets
-------------

CAISO operates several interconnected markets:

Day-Ahead Market (DAM)
~~~~~~~~~~~~~~~~~~~~~~

* **Purpose**: Schedule generation and transmission for next day
* **Timeline**: Closes at 10 AM, results posted by 1 PM
* **Resolution**: Hourly intervals
* **Use Cases**: Price forecasting, scheduling, bilateral contracts

Hour-Ahead Scheduling Process (HASP)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Purpose**: Finalize schedules for upcoming hour
* **Timeline**: Runs 75 minutes before each operating hour
* **Resolution**: Hourly intervals
* **Use Cases**: Short-term adjustments, intraday trading

Real-Time Market (RTM)
~~~~~~~~~~~~~~~~~~~~~~

* **Purpose**: Balance supply and demand in real-time
* **Timeline**: Continuous operation
* **Resolution**: 5-minute intervals
* **Use Cases**: Real-time balancing, regulation services

Real-Time Pre-Dispatch (RTPD)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Purpose**: Provide 5-minute binding dispatch instructions
* **Timeline**: Runs every 5 minutes
* **Resolution**: 5-minute intervals
* **Use Cases**: Real-time operations, frequency regulation

Residual Unit Commitment (RUC)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Purpose**: Ensure sufficient capacity for next day
* **Timeline**: Runs after DAM clears
* **Resolution**: Hourly intervals
* **Use Cases**: Capacity analysis, reliability assessment

Available Data Types
--------------------

1. Pricing Data
~~~~~~~~~~~~~~~

Locational Marginal Prices (LMP)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

LMP represents the cost of delivering electricity to a specific location, decomposed into:

* **Energy Component (LMP)**: Base energy cost
* **Congestion Component (MCC)**: Transmission constraint costs
* **Loss Component (MLC)**: Electrical loss costs

**Available Markets**: DAM, HASP, RTM, RTPD

**Example - Download DAM LMP**:

.. code-block:: python

   from datetime import date
   from lib.iso.caiso import CAISOClient, Market

   client = CAISOClient()
   client.get_lmp(
       market=Market.DAM,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )
   client.cleanup()

**Output File**: ``20240101_to_20240131_PRC_LMP_{location}.csv``

**Key Columns**:

* ``OPR_DATE``: Operating date (YYYY-MM-DD)
* ``INTERVAL_NUM``: Hour ending (1-24) or 5-min interval (1-288)
* ``DATA_ITEM``: Pricing node identifier (e.g., TH_NP15_GEN-APND)
* ``VALUE``: Price in $/MWh
* ``MLC``: Marginal Loss Component
* ``MCC``: Marginal Congestion Component

**Common Pricing Nodes**:

* ``TH_NP15_GEN-APND``: NP15 Generation Trading Hub
* ``TH_SP15_GEN-APND``: SP15 Generation Trading Hub
* ``TH_ZP26_GEN-APND``: ZP26 Generation Trading Hub
* ``DLAP_LA_BASIN``: LA Basin Load Aggregation Point

Ancillary Services Prices
^^^^^^^^^^^^^^^^^^^^^^^^^^

Clearing prices for regulation, spinning reserves, and other AS products.

.. code-block:: python

   client.get_ancillary_services_prices(
       market=Market.DAM,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

**Service Types**:

* **RU (Regulation Up)**: Frequency regulation - increase generation
* **RD (Regulation Down)**: Frequency regulation - decrease generation
* **SR (Spinning Reserve)**: 10-minute synchronized reserves
* **NR (Non-Spinning Reserve)**: 10-minute non-synchronized reserves

Fuel Prices
^^^^^^^^^^^

Natural gas and other fuel prices used in market clearing.

.. code-block:: python

   client.get_fuel_prices(
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31),
       region='ALL'  # or specific region
   )

**Fuel Regions**: SFBAY, SOCAL, NP15, SP15

GHG Allowance Prices
^^^^^^^^^^^^^^^^^^^^

Greenhouse gas allowance prices for resources participating in the California Cap-and-Trade program.

.. code-block:: python

   client.get_ghg_allowance_prices(
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

2. Load Data
~~~~~~~~~~~~

System Load Forecasts
^^^^^^^^^^^^^^^^^^^^^

CAISO publishes multiple load forecasts with different time horizons:

**Day-Ahead (DAM)**:

.. code-block:: python

   client.get_load_forecast(
       market=Market.DAM,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

**Two Day-Ahead (2DA)**:

.. code-block:: python

   client.get_load_forecast(
       market=Market.TWO_DA,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

**Seven Day-Ahead (7DA)**:

.. code-block:: python

   client.get_load_forecast(
       market=Market.SEVEN_DA,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

**Real-Time (RTM)**:

.. code-block:: python

   client.get_load_forecast(
       market=Market.RTM,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

**Advisory (RTPD)**:

.. code-block:: python

   client.get_advisory_demand_forecast(
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

**Use Cases**:

* **DA & 2DA**: Next-day planning, unit commitment
* **7DA**: Weekly operations planning
* **RTM**: Real-time balancing
* **Advisory**: 4-hour ahead adjustments

3. Generation & Resources
~~~~~~~~~~~~~~~~~~~~~~~~~~

Wind and Solar Summary
^^^^^^^^^^^^^^^^^^^^^^

Real-time wind and solar generation across CAISO's footprint.

.. code-block:: python

   client.get_wind_solar_summary(
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

**Key Metrics**:

* Current wind/solar generation (MW)
* Forecasted generation (MW)
* Available capacity (MW)
* Curtailment data
* By resource type and location

**Analysis Example**:

.. code-block:: python

   import pandas as pd
   import matplotlib.pyplot as plt

   # Load wind/solar data
   df = pd.read_csv('data/CAISO/20240101_to_20240131_ENE_WIND_SOLAR_SUMMARY_WIND_TOTAL_GEN_MW.csv')

   # Plot daily generation pattern
   df['OPR_DT'] = pd.to_datetime(df['OPR_DATE'])
   daily = df.groupby(df['OPR_DT'].dt.date)['VALUE'].sum()

   plt.figure(figsize=(14, 6))
   plt.bar(range(len(daily)), daily.values)
   plt.xlabel('Day of Month')
   plt.ylabel('Total Generation (MWh)')
   plt.title('January 2024 Wind Generation - CAISO')
   plt.savefig('wind_generation_jan2024.png')

System Load and Resource Schedules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Scheduled generation, load, and interchange for each market.

.. code-block:: python

   client.get_system_load(
       market=Market.DAM,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

**Available for**: DAM, RUC, HASP, RTM

4. Market Operations Data
~~~~~~~~~~~~~~~~~~~~~~~~~~

Market Power Mitigation (MPM)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Shows which resources were mitigated due to local market power.

.. code-block:: python

   client.get_market_power_mitigation(
       market=Market.DAM,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

**Markets**: DAM, HASP, RTPD

**Mitigation Types**:

* Local Market Power Mitigation
* Default Energy Bid (DEB) applied
* Resource commitment status

Flexible Ramping
^^^^^^^^^^^^^^^^

Flexible ramping products help CAISO manage uncertainty from renewables.

**Requirements**:

.. code-block:: python

   client.get_flex_ramp_requirements(
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31),
       baa_group='ALL'  # or specific BAA
   )

**Awards**:

.. code-block:: python

   client.get_flex_ramp_awards(
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

**Demand Curves**:

.. code-block:: python

   client.get_flex_ramp_demand_curve(
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

**Directions**: Up (FRU), Down (FRD)

Energy Imbalance Market (EIM)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

EIM transfers and limits across participating balancing authorities.

**Transfer Data**:

.. code-block:: python

   client.get_eim_transfer(
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

**Transfer Limits**:

.. code-block:: python

   client.get_eim_transfer_limits(
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

5. Ancillary Services
~~~~~~~~~~~~~~~~~~~~~~

Requirements
^^^^^^^^^^^^

System-wide AS requirements by product and region.

.. code-block:: python

   client.get_ancillary_services_requirements(
       market=Market.DAM,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31),
       anc_type='ALL',      # or 'RU', 'RD', 'SR', 'NR'
       anc_region='ALL'     # or specific region
   )

**Markets**: DAM, HASP, RTM

Awards/Results
^^^^^^^^^^^^^^

Cleared quantities by product and resource.

.. code-block:: python

   client.get_ancillary_services_results(
       market=Market.DAM,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

Operating Reserves
^^^^^^^^^^^^^^^^^^

Actual deployed operating reserves.

.. code-block:: python

   client.get_operating_reserves(
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

Common Workflows
----------------

1. Daily Price Monitoring
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from datetime import date, timedelta
   from lib.iso.caiso import CAISOClient, Market

   def daily_price_update():
       """Download yesterday's prices across all markets."""
       yesterday = date.today() - timedelta(days=1)

       client = CAISOClient()

       # Download DAM and RTM LMP
       client.get_lmp(Market.DAM, yesterday, yesterday)
       client.get_lmp(Market.RTM, yesterday, yesterday)

       # Download AS prices
       client.get_ancillary_services_prices(Market.DAM, yesterday, yesterday)

       client.cleanup()
       print(f"✓ Downloaded prices for {yesterday}")

   if __name__ == '__main__':
       daily_price_update()

Schedule with cron::

   0 8 * * * cd /path/to/ISO-DART && /path/to/venv/bin/python daily_price_update.py

2. Renewable Generation Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pandas as pd
   import matplotlib.pyplot as plt
   from datetime import date
   from lib.iso.caiso import CAISOClient

   # Download wind and solar data
   client = CAISOClient()
   client.get_wind_solar_summary(date(2024, 1, 1), date(2024, 1, 31))
   client.cleanup()

   # Load and analyze
   wind_file = 'data/CAISO/20240101_to_20240131_ENE_WIND_SOLAR_SUMMARY_WIND_TOTAL_GEN_MW.csv'
   solar_file = 'data/CAISO/20240101_to_20240131_ENE_WIND_SOLAR_SUMMARY_SOLAR_TOTAL_GEN_MW.csv'

   wind_df = pd.read_csv(wind_file)
   solar_df = pd.read_csv(solar_file)

   # Convert to datetime
   wind_df['datetime'] = pd.to_datetime(wind_df['OPR_DATE'])
   solar_df['datetime'] = pd.to_datetime(solar_df['OPR_DATE'])

   # Calculate daily totals
   wind_daily = wind_df.groupby(wind_df['datetime'].dt.date)['VALUE'].sum()
   solar_daily = solar_df.groupby(solar_df['datetime'].dt.date)['VALUE'].sum()

   # Plot
   fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

   ax1.plot(wind_daily.index, wind_daily.values, 'b-', linewidth=2)
   ax1.set_ylabel('Wind Generation (MWh)', fontsize=12)
   ax1.set_title('January 2024 Renewable Generation - CAISO', fontsize=14)
   ax1.grid(True, alpha=0.3)

   ax2.plot(solar_daily.index, solar_daily.values, 'orange', linewidth=2)
   ax2.set_ylabel('Solar Generation (MWh)', fontsize=12)
   ax2.set_xlabel('Date', fontsize=12)
   ax2.grid(True, alpha=0.3)

   plt.tight_layout()
   plt.savefig('caiso_renewables_jan2024.png', dpi=300)
   print("✓ Analysis complete")

Data Quality & Limitations
---------------------------

Update Schedule
~~~~~~~~~~~~~~~

* **DAM LMP**: Available by 1 PM PT for next operating day
* **RTM LMP**: Published within 1 hour of operating interval
* **Load Forecasts**: Updated multiple times daily
* **AS Prices**: Available shortly after market clearing

Historical Data Availability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 20 40

   * - Data Type
     - Start Date
     - Notes
   * - LMP (All markets)
     - April 2009
     - Complete history
   * - AS Prices
     - April 2009
     - Complete history
   * - Load Forecasts
     - January 2010
     - Earlier data may be sparse
   * - Wind/Solar
     - March 2015
     - When tracking began
   * - EIM Data
     - October 2014
     - When EIM launched
   * - Flex Ramping
     - November 2016
     - Product launch date

Known Issues
~~~~~~~~~~~~

1. **Holiday Data**: Some holidays may have partial or delayed data
2. **Market Reruns**: Occasionally markets are re-run; initial results may be revised
3. **Daylight Saving Time**: Spring forward (23 hours) and fall back (25 hours) days handled automatically
4. **Location Changes**: Some pricing nodes are renamed or retired; check CAISO's Master File

Data Validation
~~~~~~~~~~~~~~~

.. code-block:: python

   import pandas as pd

   def validate_caiso_data(file_path):
       """Basic validation checks for CAISO data."""
       df = pd.read_csv(file_path)

       # Check for required columns
       required_cols = ['OPR_DATE', 'INTERVAL_NUM', 'VALUE']
       missing = set(required_cols) - set(df.columns)
       if missing:
           print(f"❌ Missing columns: {missing}")
           return False

       # Check for nulls
       null_counts = df[required_cols].isnull().sum()
       if null_counts.any():
           print(f"⚠️  Null values found: {null_counts[null_counts > 0]}")

       # Check interval count
       intervals_per_day = df.groupby('OPR_DATE')['INTERVAL_NUM'].nunique()
       expected = 24  # or 288 for 5-min data
       irregular = intervals_per_day[intervals_per_day != expected]
       if len(irregular) > 0:
           print(f"⚠️  Irregular interval counts on: {irregular.index.tolist()}")

       # Check for negative prices (unusual but possible)
       if (df['VALUE'] < 0).any():
           neg_count = (df['VALUE'] < 0).sum()
           print(f"⚠️  {neg_count} negative prices found (may be valid)")

       print("✓ Validation complete")
       return True

   # Example usage
   validate_caiso_data('data/CAISO/20240101_to_20240131_PRC_LMP_TH_NP15_GEN-APND.csv')

Performance Tips
----------------

1. Optimize Date Ranges
~~~~~~~~~~~~~~~~~~~~~~~~

Large date ranges can be slow. Break into chunks:

.. code-block:: python

   from datetime import date, timedelta
   from lib.iso.caiso import CAISOClient, Market

   def download_large_range(start, end, chunk_days=30):
       """Download in monthly chunks."""
       client = CAISOClient()

       current = start
       while current < end:
           chunk_end = min(current + timedelta(days=chunk_days), end)
           print(f"Downloading {current} to {chunk_end}")
           client.get_lmp(Market.DAM, current, chunk_end)
           current = chunk_end + timedelta(days=1)

       client.cleanup()

   # Download full year in monthly chunks
   download_large_range(date(2024, 1, 1), date(2024, 12, 31))

2. Adjust Step Size
~~~~~~~~~~~~~~~~~~~~

Control requests per API call:

.. code-block:: python

   client = CAISOClient()

   # Smaller step size for more stable downloads
   client.get_lmp(
       market=Market.DAM,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 12, 31),
       step_size=1  # 1 day per request (default)
   )

3. Parallel Downloads
~~~~~~~~~~~~~~~~~~~~~

Download multiple markets simultaneously:

.. code-block:: python

   from concurrent.futures import ThreadPoolExecutor
   from datetime import date
   from lib.iso.caiso import CAISOClient, Market

   def download_market(market, start, end):
       client = CAISOClient()
       result = client.get_lmp(market, start, end)
       client.cleanup()
       return market, result

   markets = [Market.DAM, Market.HASP, Market.RTM]
   start = date(2024, 1, 1)
   end = date(2024, 1, 31)

   with ThreadPoolExecutor(max_workers=3) as executor:
       futures = [executor.submit(download_market, m, start, end) for m in markets]
       results = [f.result() for f in futures]

   for market, success in results:
       print(f"{market.value}: {'✓' if success else '✗'}")

Troubleshooting
---------------

Issue: "API Error 404: Data not found"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Possible Causes**:

* Date is too recent (data not yet published)
* Date is before data collection began
* Market was not operating on that date (holiday)

**Solutions**:

.. code-block:: python

   # Check date range is valid
   from datetime import date, timedelta

   # Use a date that's at least 2 days old
   safe_date = date.today() - timedelta(days=2)
   client.get_lmp(Market.DAM, safe_date, safe_date)

Issue: Slow Downloads
~~~~~~~~~~~~~~~~~~~~~

**Solutions**:

* Download during off-peak hours (early morning PT)
* Use smaller date ranges
* Reduce ``step_size``
* Check your internet connection
* Verify CAISO OASIS is operational: http://www.caiso.com/Pages/System-Status.aspx

Issue: Missing Intervals
~~~~~~~~~~~~~~~~~~~~~~~~~

Some days may have 23 or 25 hours due to Daylight Saving Time.

**Detection**:

.. code-block:: python

   df = pd.read_csv('your_file.csv')
   intervals_by_day = df.groupby('OPR_DATE')['INTERVAL_NUM'].nunique()
   print(intervals_by_day[intervals_by_day != 24])  # Find irregular days

**Handling**:

.. code-block:: python

   # Fill missing intervals with NaN
   df = df.set_index(['OPR_DATE', 'INTERVAL_NUM'])
   df = df.reindex(pd.MultiIndex.from_product([
       df.index.levels[0],
       range(1, 25)  # Always 1-24
   ], names=['OPR_DATE', 'INTERVAL_NUM']))
   df = df.reset_index()

Additional Resources
--------------------

* `CAISO OASIS <http://oasis.caiso.com/>`_ - Official data portal
* `CAISO OASIS API Documentation <http://www.caiso.com/Documents/OASIS-InterfaceSpecification.pdf>`_
* `CAISO Today's Outlook <http://www.caiso.com/TodaysOutlook/Pages/default.aspx>`_ - Real-time dashboard
* `CAISO Business Practice Manuals <http://www.caiso.com/rules/Pages/BusinessPracticeManuals/Default.aspx>`_
* `Market Monitoring Reports <http://www.caiso.com/market/Pages/ReportsBulletins/Default.aspx>`_

Next Steps
----------

* :doc:`pricing` - CAISO Pricing Data Deep Dive
* :doc:`load` - Load Data Tutorial
* :doc:`generation` - Generation Analysis Examples
* :doc:`../index` - Return to ISO Index