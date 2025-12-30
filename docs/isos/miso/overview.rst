MISO Data Guide
===============

Overview
--------

The Midcontinent Independent System Operator (MISO) operates one of the world's largest energy markets, serving 45
million people across 15 U.S. states and Manitoba, Canada. ISO-DART provides comprehensive access to MISO's Data
Exchange REST API for pricing, load, generation, and market operations data.

Quick Reference
---------------

.. list-table::
   :header-rows: 1
   :widths: 25 20 25 30

   * - Data Category
     - Update Frequency
     - Historical Availability
     - API Requirement
   * - LMP (DA/RT)
     - 5-min/Hourly
     - 2009-present
     - Pricing API Key
   * - MCP
     - 5-min/Hourly
     - 2009-present
     - Pricing API Key
   * - Load/Demand
     - 5-min/Hourly
     - 2010-present
     - LGI API Key
   * - Fuel Mix
     - 5-min intervals
     - 2014-present
     - LGI API Key
   * - Generation
     - Hourly
     - 2010-present
     - LGI API Key

MISO Markets
------------

MISO operates an integrated day-ahead and real-time market system:

Day-Ahead Market
~~~~~~~~~~~~~~~~

* **Purpose**: Schedule generation and manage congestion for next operating day
* **Timeline**: Closes at 11 AM CT, results posted by 4 PM CT
* **Resolution**: Hourly intervals
* **Products**: Energy, Operating Reserves, Ramp Capability

Real-Time Market
~~~~~~~~~~~~~~~~

* **Purpose**: Balance supply and demand in real-time
* **Timeline**: Continuous 5-minute dispatch
* **Resolution**: 5-minute intervals
* **Products**: Energy, Regulation, Spinning/Supplemental Reserves

API Access & Authentication
----------------------------

MISO uses a REST API with two separate products requiring different API keys:

Pricing API
~~~~~~~~~~~

Covers:

* LMP data (ExAnte/ExPost)
* Market Clearing Prices (MCP)
* Ancillary Services pricing

Get your key at: https://data-exchange.misoenergy.org/

Load, Generation & Interchange (LGI) API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Covers:

* Load and demand data
* Generation by fuel type
* Fuel on the margin
* Interchange flows
* Outages and constraints

Get your key at: https://data-exchange.misoenergy.org/

Configuration Setup
~~~~~~~~~~~~~~~~~~~

Create ``user_config.ini`` in your project root:

.. code-block:: ini

   [miso]
   pricing_api_key = your-pricing-api-key-here
   lgi_api_key = your-lgi-api-key-here
   data_dir = data/MISO
   max_retries = 3
   timeout = 30

Or use the template generator:

.. code-block:: python

   from lib.iso.miso import MISOConfig

   # Creates template config file
   MISOConfig.create_template_ini()
   # Edit user_config.ini with your keys

Available Data Types
--------------------

1. Pricing Data
~~~~~~~~~~~~~~~

Locational Marginal Prices (LMP)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

MISO LMP data is available in four variants:

* **Day-Ahead ExAnte**: Forward-looking DA market prices
* **Day-Ahead ExPost**: Final settled DA market prices
* **Real-Time ExAnte**: 5-minute ahead RT prices
* **Real-Time ExPost**: Final settled RT prices

**Example - Download DA ExAnte LMP**:

.. code-block:: python

   from datetime import date
   from lib.iso.miso import MISOClient, MISOConfig

   # Load configuration with API keys
   config = MISOConfig.from_ini_file()
   client = MISOClient(config)

   # Download LMP data
   data = client.get_lmp(
       lmp_type='da_exante',
       start_date=date(2024, 1, 1),
       duration=30,
       node='ALTW.WELLS1'  # Optional: filter by node
   )

   # Save to CSV
   if data:
       client.save_to_csv(data, 'miso_da_exante_lmp.csv')

**Output**: ``data/MISO/miso_da_exante_lmp_2024-01-01.csv``

**Key Columns**:

* ``node``: Pricing node identifier
* ``value``: LMP in $/MWh
* ``lmp``: Total LMP
* ``mcc``: Marginal Congestion Component
* ``mlc``: Marginal Loss Component
* ``interval``: Date/time of interval

Market Clearing Prices (MCP)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Ancillary service market clearing prices by zone and product.

.. code-block:: python

   # ASM Day-Ahead ExAnte MCP
   data = client.get_mcp(
       mcp_type='asm_da_exante',
       start_date=date(2024, 1, 1),
       duration=30,
       zone='MISO',  # Optional: filter by zone
       product='RegUp'  # Optional: filter by product
   )

**MCP Types**:

* ``asm_da_exante``: ASM Day-Ahead ExAnte
* ``asm_da_expost``: ASM Day-Ahead ExPost
* ``asm_rt_exante``: ASM Real-Time ExAnte
* ``asm_rt_expost``: ASM Real-Time ExPost
* ``asm_rt_summary``: ASM Real-Time Summary

**Ancillary Service Products**:

* **RegUp**: Regulation Up
* **RegDown**: Regulation Down
* **Spin**: Spinning Reserve
* **Supp**: Supplemental Reserve

2. Load & Demand Data
~~~~~~~~~~~~~~~~~~~~~~

System Demand
^^^^^^^^^^^^^

Multiple demand data types available:

.. code-block:: python

   # Real-Time Actual Load
   data = client.get_demand(
       demand_type='rt_actual',
       start_date=date(2024, 1, 1),
       duration=30,
       region='MISO',  # Optional: filter by region
       time_resolution='daily'  # or 'hourly', '5min'
   )

**Demand Types**:

* ``da_demand``: Day-Ahead scheduled demand
* ``rt_forecast``: Real-Time demand forecast
* ``rt_actual``: Real-Time actual load
* ``rt_state_estimator``: State estimator load

Load Forecasts
^^^^^^^^^^^^^^

Medium-term load forecasts:

.. code-block:: python

   data = client.get_load_forecast(
       start_date=date(2024, 1, 1),
       duration=30,
       region='MISO',
       time_resolution='daily'
   )

**Use Cases**:

* Planning and operations
* Load shape analysis
* Forecast accuracy studies

3. Generation Data
~~~~~~~~~~~~~~~~~~

Fuel Mix
^^^^^^^^

Real-time fuel on the margin (5-minute resolution):

.. code-block:: python

   data = client.get_fuel_mix(
       start_date=date(2024, 1, 1),
       duration=30,
       region='MISO',
       fuel_type='Coal'  # Optional filter
   )

**Fuel Types**: Coal, Gas, Nuclear, Wind, Solar, Hydro, Other

Generation by Type
^^^^^^^^^^^^^^^^^^

Various generation data products:

.. code-block:: python

   # Real-Time fuel type generation
   data = client.get_generation(
       gen_type='rt_fuel_type',
       start_date=date(2024, 1, 1),
       duration=30
   )

**Generation Types**:

* ``da_cleared_physical``: DA cleared physical generation
* ``da_cleared_virtual``: DA cleared virtual generation
* ``da_fuel_type``: DA generation by fuel type
* ``da_offered_ecomax``: DA offered economic max
* ``rt_cleared``: RT cleared generation
* ``rt_fuel_type``: RT generation by fuel type
* ``rt_fuel_margin``: RT fuel on margin

4. Interchange Data
~~~~~~~~~~~~~~~~~~~~

Net interchange flows between MISO and neighboring systems:

.. code-block:: python

   data = client.get_interchange(
       interchange_type='rt_net_actual',
       start_date=date(2024, 1, 1),
       duration=30,
       region='MISO',
       adjacent_ba='PJM'  # Optional filter
   )

**Interchange Types**:

* ``da_net_scheduled``: DA scheduled interchange
* ``rt_net_actual``: RT actual interchange
* ``rt_net_scheduled``: RT scheduled interchange
* ``historical``: Historical net scheduled

5. Outages & Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~

Binding Constraints
^^^^^^^^^^^^^^^^^^^

Real-time binding transmission constraints:

.. code-block:: python

   data = client.get_binding_constraints(
       start_date=date(2024, 1, 1),
       duration=30,
       interval='all'  # or specific interval
   )

**Use Cases**:

* Congestion analysis
* Price driver identification
* Transmission planning

Outage Data
^^^^^^^^^^^

Generation outage forecasts and actual outages:

.. code-block:: python

   # Outage forecast
   data = client.get_outages(
       outage_type='forecast',
       start_date=date(2024, 1, 1),
       duration=30
   )

   # Real-time outages
   data = client.get_outages(
       outage_type='rt_outage',
       start_date=date(2024, 1, 1),
       duration=30
   )

Common Workflows
----------------

1. Daily Price Update
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from datetime import date, timedelta
   from lib.iso.miso import MISOClient, MISOConfig

   def daily_miso_update():
       """Download yesterday's MISO data."""
       yesterday = date.today() - timedelta(days=1)

       config = MISOConfig.from_ini_file()
       client = MISOClient(config)

       # Download LMP
       lmp_data = client.get_lmp('da_exante', yesterday, 1)
       if lmp_data:
           client.save_to_csv(lmp_data, f'miso_lmp_{yesterday}.csv')
           print(f"✓ Downloaded LMP for {yesterday}")

       # Download fuel mix
       fuel_data = client.get_fuel_mix(yesterday, 1)
       if fuel_data:
           client.save_to_csv(fuel_data, f'miso_fuel_{yesterday}.csv')
           print(f"✓ Downloaded fuel mix for {yesterday}")

   if __name__ == '__main__':
       daily_miso_update()

2. Fuel Mix Analysis
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pandas as pd
   import matplotlib.pyplot as plt
   from datetime import date
   from lib.iso.miso import MISOClient, MISOConfig

   # Download data
   config = MISOConfig.from_ini_file()
   client = MISOClient(config)

   data = client.get_fuel_mix(
       start_date=date(2024, 1, 1),
       duration=31
   )

   client.save_to_csv(data, 'miso_fuel_jan2024.csv')

   # Load and analyze
   df = pd.read_csv('data/MISO/miso_fuel_jan2024.csv')

   # Convert to datetime
   df['datetime'] = pd.to_datetime(df['interval'])

   # Group by fuel type and date
   daily_by_fuel = df.groupby([
       df['datetime'].dt.date,
       'fuelType'
   ])['value'].sum().unstack()

   # Plot stacked area chart
   fig, ax = plt.subplots(figsize=(14, 8))
   daily_by_fuel.plot.area(ax=ax, alpha=0.8)
   ax.set_xlabel('Date')
   ax.set_ylabel('Generation (MWh)')
   ax.set_title('MISO Fuel Mix - January 2024')
   ax.legend(title='Fuel Type', bbox_to_anchor=(1.05, 1))
   plt.tight_layout()
   plt.savefig('miso_fuel_mix_jan2024.png', dpi=300)

3. Load Correlation Study
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pandas as pd
   import numpy as np
   from scipy.stats import pearsonr

   # Load LMP and demand data
   lmp_df = pd.read_csv('data/MISO/miso_lmp_jan2024.csv')
   load_df = pd.read_csv('data/MISO/miso_rt_actual_load_jan2024.csv')

   # Merge on timestamp
   lmp_df['datetime'] = pd.to_datetime(lmp_df['interval'])
   load_df['datetime'] = pd.to_datetime(load_df['interval'])

   # Get hourly averages
   lmp_hourly = lmp_df.groupby(
       lmp_df['datetime'].dt.floor('H')
   )['lmp'].mean()

   load_hourly = load_df.groupby(
       load_df['datetime'].dt.floor('H')
   )['value'].mean()

   # Calculate correlation
   correlation, p_value = pearsonr(
       lmp_hourly.values,
       load_hourly.values
   )

   print(f"Price-Load Correlation: {correlation:.3f}")
   print(f"P-value: {p_value:.6f}")

   # Scatter plot
   plt.figure(figsize=(10, 8))
   plt.scatter(load_hourly.values, lmp_hourly.values, alpha=0.5)
   plt.xlabel('System Load (MW)')
   plt.ylabel('LMP ($/MWh)')
   plt.title(f'MISO Load vs. Price\nCorrelation: {correlation:.3f}')
   plt.grid(True, alpha=0.3)

   # Add trend line
   z = np.polyfit(load_hourly.values, lmp_hourly.values, 1)
   p = np.poly1d(z)
   plt.plot(load_hourly.values, p(load_hourly.values), "r--", linewidth=2)

   plt.tight_layout()
   plt.savefig('miso_price_load_correlation.png', dpi=300)

Data Quality & Limitations
---------------------------

Update Schedule
~~~~~~~~~~~~~~~

* **DA ExAnte LMP**: Available ~4 PM CT day before operating day
* **DA ExPost LMP**: Available ~4 PM CT day after operating day
* **RT ExAnte LMP**: Available within 5 minutes of interval
* **RT ExPost LMP**: Available ~1 hour after interval
* **Fuel Mix**: Updated every 5 minutes

Historical Data
~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 20 40

   * - Data Type
     - Start Date
     - Notes
   * - LMP (All types)
     - January 2009
     - Complete history
   * - MCP
     - January 2009
     - Complete history
   * - Load/Demand
     - January 2010
     - Complete history
   * - Fuel Mix
     - March 2014
     - When tracking began
   * - Generation Data
     - January 2010
     - Varies by product

Known Issues
~~~~~~~~~~~~

1. **API Rate Limits**: 100 requests/minute (adjustable in config)
2. **Large Date Ranges**: Use pagination for requests over 90 days
3. **Node Names**: May change over time; check MISO node list
4. **Time Zones**: All times in Central Time (CT)

Rate Limiting
~~~~~~~~~~~~~

.. code-block:: python

   from lib.iso.miso import MISOConfig

   # Adjust rate limit delay (seconds between requests)
   config = MISOConfig(
       rate_limit_delay=0.8  # Default is 0.6
   )

   client = MISOClient(config)

Performance Tips
----------------

1. Use Filters
~~~~~~~~~~~~~~

Filter data at the API level to reduce response size:

.. code-block:: python

   # Better: filter by node
   data = client.get_lmp(
       lmp_type='da_exante',
       start_date=date(2024, 1, 1),
       duration=30,
       node='SPECIFIC.NODE'  # Only this node
   )

   # Avoid: downloading all nodes then filtering
   data = client.get_lmp('da_exante', date(2024, 1, 1), 30)
   filtered = {k: v for k, v in data.items() if 'SPECIFIC.NODE' in str(v)}

2. Adjust Time Resolution
~~~~~~~~~~~~~~~~~~~~~~~~~~

Use coarser resolution when possible:

.. code-block:: python

   # For daily analysis, use daily resolution
   data = client.get_demand(
       demand_type='rt_actual',
       start_date=date(2024, 1, 1),
       duration=30,
       time_resolution='daily'  # Much faster than '5min'
   )

3. Batch Processing
~~~~~~~~~~~~~~~~~~~

Process multiple months in a loop:

.. code-block:: python

   from datetime import date
   from dateutil.relativedelta import relativedelta

   start = date(2024, 1, 1)

   for month in range(12):
       month_start = start + relativedelta(months=month)
       month_end = month_start + relativedelta(months=1)
       days = (month_end - month_start).days

       print(f"Processing {month_start.strftime('%B %Y')}")

       data = client.get_lmp(
           lmp_type='da_exante',
           start_date=month_start,
           duration=days
       )

       if data:
           filename = f"miso_lmp_{month_start.strftime('%Y%m')}.csv"
           client.save_to_csv(data, filename)

Troubleshooting
---------------

Issue: "Authentication failed - check API key"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Solutions**:

1. Verify API key is correct in ``user_config.ini``
2. Check you're using the right key for the right product:

   * Pricing API key → LMP, MCP data
   * LGI API key → Load, generation, interchange data

3. Ensure API subscription is active at https://data-exchange.misoenergy.org/

Issue: "No data returned"
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Solutions**:

* Check date range is valid (not in future)
* Verify data exists for that period
* Try a specific node/zone filter
* Check MISO API status: https://data-exchange.misoenergy.org/

Issue: Rate limit errors (429)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Solutions**:

.. code-block:: python

   # Increase delay between requests
   config = MISOConfig(
       rate_limit_delay=1.0  # Increase from default 0.6
   )

   # Or reduce requests per batch
   # Download in smaller chunks

Issue: Timeout errors
~~~~~~~~~~~~~~~~~~~~~

**Solutions**:

.. code-block:: python

   # Increase timeout
   config = MISOConfig(
       timeout=60  # Default is 30 seconds
   )

   # Or break into smaller date ranges

Additional Resources
--------------------

* `MISO Data Exchange <https://data-exchange.misoenergy.org/>`_ - API portal
* `MISO Markets <https://www.misoenergy.org/markets-and-operations/>`_ - Market information
* `MISO Real-Time Dashboard <https://www.misoenergy.org/markets-and-operations/real-time-displays/>`_
* `MISO Market Reports <https://www.misoenergy.org/markets-and-operations/market-reports/>`_
* `API Documentation <https://data-exchange.misoenergy.org/docs>`_

Next Steps
----------

* :doc:`api-keys` - Detailed API key setup guide
* :doc:`pricing` - MISO Pricing Data Deep Dive
* :doc:`load-gen` - Load and Generation Analysis
* :doc:`../index` - Return to ISO Index