Python API Guide
================

Overview
--------

This guide covers using ISO-DART programmatically from Python scripts and applications.

Installation
------------

.. code-block:: python

   # Option 1: Use as a library (recommended)
   import sys
   sys.path.append('/path/to/ISO-DART')

   from lib.iso.caiso import CAISOClient, Market
   from lib.iso.miso import MISOClient, MISOConfig
   # ... etc

   # Option 2: Install as package (future)
   # pip install isodart

Basic Usage Pattern
-------------------

All ISO clients follow a similar pattern:

.. code-block:: python

   from datetime import date

   # 1. Import the client
   from lib.iso.caiso import CAISOClient, Market

   # 2. Create client instance
   client = CAISOClient()

   # 3. Download data
   success = client.get_lmp(
       market=Market.DAM,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

   # 4. Clean up
   client.cleanup()

CAISO Client
------------

Basic LMP Download
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from datetime import date
   from lib.iso.caiso import CAISOClient, Market

   # Initialize client
   client = CAISOClient()

   # Download Day-Ahead LMP
   client.get_lmp(
       market=Market.DAM,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

   # Download Real-Time LMP
   client.get_lmp(
       market=Market.RTM,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 7)
   )

   client.cleanup()

Available Markets
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lib.iso.caiso import Market

   Market.DAM      # Day-Ahead Market
   Market.HASP     # Hour-Ahead Scheduling Process
   Market.RTM      # Real-Time Market
   Market.RTPD     # Real-Time Pre-Dispatch
   Market.RUC      # Residual Unit Commitment
   Market.TWO_DA   # Two Day-Ahead
   Market.SEVEN_DA # Seven Day-Ahead

Load Forecasts
~~~~~~~~~~~~~~

.. code-block:: python

   # Day-Ahead forecast
   client.get_load_forecast(
       market=Market.DAM,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

   # 7-Day forecast
   client.get_load_forecast(
       market=Market.SEVEN_DA,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

Renewable Generation
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Wind and solar summary
   client.get_wind_solar_summary(
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

Ancillary Services
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # AS prices
   client.get_ancillary_services_prices(
       market=Market.DAM,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

   # AS requirements
   client.get_ancillary_services_requirements(
       market=Market.DAM,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31),
       anc_type='ALL',  # or 'RU', 'RD', 'SR', 'NR'
       anc_region='ALL'
   )

Custom Configuration
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from pathlib import Path
   from lib.iso.caiso import CAISOClient, CAISOConfig

   # Custom config
   config = CAISOConfig(
       data_dir=Path('my_data/CAISO'),
       max_retries=5,
       timeout=60,
       retry_delay=10
   )

   client = CAISOClient(config=config)

MISO Client
-----------

Setup with API Keys
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lib.iso.miso import MISOClient, MISOConfig

   # Load from config file
   config = MISOConfig.from_ini_file()
   client = MISOClient(config)

   # Or specify directly
   config = MISOConfig(
       pricing_api_key='your-pricing-key',
       lgi_api_key='your-lgi-key'
   )
   client = MISOClient(config)

LMP Data
~~~~~~~~

.. code-block:: python

   from datetime import date

   # Day-Ahead ExAnte LMP
   data = client.get_lmp(
       lmp_type='da_exante',
       start_date=date(2024, 1, 1),
       duration=30,
       node='ALTW.WELLS1'  # Optional: specific node
   )

   # Save to CSV
   if data:
       client.save_to_csv(data, 'miso_lmp.csv')

Available LMP Types
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   'da_exante'   # Day-Ahead ExAnte
   'da_expost'   # Day-Ahead ExPost
   'rt_exante'   # Real-Time ExAnte
   'rt_expost'   # Real-Time ExPost

Load and Generation
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Actual load
   load_data = client.get_demand(
       demand_type='rt_actual',
       start_date=date(2024, 1, 1),
       duration=30,
       time_resolution='daily'
   )

   # Fuel mix
   fuel_data = client.get_fuel_mix(
       start_date=date(2024, 1, 1),
       duration=30
   )

   # Generation by fuel type
   gen_data = client.get_generation(
       gen_type='rt_fuel_type',
       start_date=date(2024, 1, 1),
       duration=30
   )

Working with MISO Data
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Download and process
   data = client.get_lmp('da_exante', date(2024, 1, 1), 7)

   if data:
       # Data is a dict: {date: [records]}
       print(f"Downloaded data for {len(data)} dates")

       # Save to CSV
       client.save_to_csv(data, 'output.csv')

       # Or process directly
       import pandas as pd
       all_records = []
       for date_key, records in data.items():
           for record in records:
               record['query_date'] = date_key
               all_records.append(record)

       df = pd.DataFrame(all_records)
       print(df.head())

NYISO Client
------------

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from lib.iso.nyiso import NYISOClient, NYISOMarket

   client = NYISOClient()

   # LBMP data
   client.get_lbmp(
       market=NYISOMarket.DAM,
       level='zonal',  # or 'generator'
       start_date=date(2024, 1, 1),
       duration=30
   )

   # Load data
   client.get_load_data(
       load_type='actual',
       start_date=date(2024, 1, 1),
       duration=30
   )

   # Fuel mix
   client.get_fuel_mix(
       start_date=date(2024, 1, 1),
       duration=30
   )

   client.cleanup()

SPP Client
----------

LMP Data
~~~~~~~~

.. code-block:: python

   from lib.iso.spp import SPPClient, SPPMarket

   client = SPPClient()

   # LMP by settlement location
   client.get_lmp(
       market=SPPMarket.DAM,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31),
       by_location=True  # False for by bus
   )

   # Market clearing prices
   client.get_mcp(
       market=SPPMarket.RTBM,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

   client.cleanup()

Load and Resource Forecasts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Short-term load forecast
   client.get_load_forecast(
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31),
       forecast_type='stlf'
   )

   # Medium-term resource (wind + solar) forecast
   client.get_resource_forecast(
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31),
       forecast_type='mtrf'
   )

BPA Client
----------

Historical Data
~~~~~~~~~~~~~~~

.. code-block:: python

   from lib.iso.bpa import BPAClient

   client = BPAClient()

   # Wind generation and total load
   client.get_wind_gen_total_load(
       year=2024,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

   # Operating reserves
   client.get_reserves_deployed(
       year=2024,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

   # Outages
   client.get_outages(
       year=2024,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 31)
   )

   client.cleanup()

PJM Client
----------

Setup
~~~~~

.. code-block:: python

   from lib.iso.pjm import PJMClient, PJMConfig

   # Load from config
   config = PJMConfig.from_ini_file()
   client = PJMClient(config)

   # Or specify directly
   config = PJMConfig(api_key='your-api-key')
   client = PJMClient(config)

LMP Data
~~~~~~~~

.. code-block:: python

   # Day-ahead hourly LMP
   client.get_lmp(
       lmp_type='da_hourly',
       start_date=date(2024, 1, 1),
       duration=7,
       pnode_id=51288  # Optional: specific node
   )

   # Real-time 5-minute LMP
   client.get_lmp(
       lmp_type='rt_5min',
       start_date=date(2024, 1, 1),
       duration=1  # Use shorter duration for 5-min data
   )

   client.cleanup()

ISO-NE Client
-------------

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from lib.iso.isone import ISONEClient

   client = ISONEClient()

   # Day-ahead hourly LMP
   paths = client.get_hourly_lmp(
       start_date=date(2024, 1, 1),
       end_date_exclusive=date(2024, 2, 1),
       market='da',
       report='final'
   )

   # 5-minute regulation prices
   paths = client.get_5min_regulation_prices(
       start_date=date(2024, 1, 1),
       end_date_exclusive=date(2024, 2, 1)
   )

Weather Client
--------------

Download Weather Data
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from lib.weather.client import WeatherClient

   client = WeatherClient()

   # Download weather data (interactive station selection)
   client.download_weather_data(
       state='CA',
       start_date=date(2024, 1, 1),
       duration=30,
       interactive=True
   )

   # Download solar data
   client.download_solar_data(year=2024)

Advanced Patterns
-----------------

Multi-ISO Download
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from datetime import date
   from lib.iso.caiso import CAISOClient, Market as CAISOMarket
   from lib.iso.miso import MISOClient, MISOConfig
   from lib.iso.nyiso import NYISOClient, NYISOMarket

   start = date(2024, 1, 1)
   end = date(2024, 1, 31)

   # CAISO
   caiso = CAISOClient()
   caiso.get_lmp(CAISOMarket.DAM, start, end)
   caiso.cleanup()

   # MISO
   miso_config = MISOConfig.from_ini_file()
   miso = MISOClient(miso_config)
   miso.get_lmp('da_exante', start, 30)

   # NYISO
   nyiso = NYISOClient()
   nyiso.get_lbmp(NYISOMarket.DAM, 'zonal', start, 30)
   nyiso.cleanup()

   print("Downloaded data from all three ISOs")

Error Handling
~~~~~~~~~~~~~~

.. code-block:: python

   from datetime import date
   from lib.iso.caiso import CAISOClient, Market
   import logging

   # Setup logging
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)

   client = CAISOClient()

   try:
       success = client.get_lmp(
           market=Market.DAM,
           start_date=date(2024, 1, 1),
           end_date=date(2024, 1, 31)
       )

       if success:
           logger.info("Download successful")
       else:
           logger.error("Download failed")

   except Exception as e:
       logger.error(f"Error: {e}", exc_info=True)

   finally:
       client.cleanup()

Async/Parallel Downloads
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from concurrent.futures import ThreadPoolExecutor
   from datetime import date
   from lib.iso.caiso import CAISOClient, Market

   def download_market(market, start, end):
       """Download data for a specific market."""
       client = CAISOClient()
       try:
           result = client.get_lmp(market, start, end)
           return market, result
       finally:
           client.cleanup()

   # Download multiple markets in parallel
   markets = [Market.DAM, Market.HASP, Market.RTM]
   start = date(2024, 1, 1)
   end = date(2024, 1, 31)

   with ThreadPoolExecutor(max_workers=3) as executor:
       futures = [
           executor.submit(download_market, m, start, end)
           for m in markets
       ]
       results = [f.result() for f in futures]

   for market, success in results:
       print(f"{market.value}: {'✓' if success else '✗'}")

Data Processing Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pandas as pd
   from datetime import date
   from pathlib import Path
   from lib.iso.caiso import CAISOClient, Market

   def download_and_process(start_date, end_date):
       """Download data and perform basic processing."""

       # Download
       client = CAISOClient()
       success = client.get_lmp(Market.DAM, start_date, end_date)
       client.cleanup()

       if not success:
           return None

       # Load the most recent file
       data_dir = Path('data/CAISO')
       files = sorted(data_dir.glob('*PRC_LMP*.csv'))
       if not files:
           return None

       # Process
       df = pd.read_csv(files[-1])

       # Add datetime column
       df['datetime'] = pd.to_datetime(df['OPR_DATE'])

       # Calculate statistics
       stats = {
           'mean_price': df['VALUE'].mean(),
           'max_price': df['VALUE'].max(),
           'min_price': df['VALUE'].min(),
           'date_range': f"{df['OPR_DATE'].min()} to {df['OPR_DATE'].max()}"
       }

       return df, stats

   # Use it
   df, stats = download_and_process(date(2024, 1, 1), date(2024, 1, 7))
   if df is not None:
       print(f"Mean price: ${stats['mean_price']:.2f}/MWh")

Custom Retry Logic
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import time
   from datetime import date
   from lib.iso.caiso import CAISOClient, Market

   def download_with_retry(client, market, start, end, max_retries=5):
       """Download with custom retry logic."""

       for attempt in range(max_retries):
           try:
               success = client.get_lmp(market, start, end)
               if success:
                   return True

               print(f"Attempt {attempt + 1} failed, retrying...")
               time.sleep(30 * (attempt + 1))  # Exponential backoff

           except Exception as e:
               print(f"Error on attempt {attempt + 1}: {e}")
               if attempt < max_retries - 1:
                   time.sleep(30 * (attempt + 1))

       return False

   # Use it
   client = CAISOClient()
   success = download_with_retry(
       client, Market.DAM,
       date(2024, 1, 1), date(2024, 1, 31)
   )
   client.cleanup()

Best Practices
--------------

1. Always Clean Up
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Use try-finally
   client = CAISOClient()
   try:
       client.get_lmp(Market.DAM, start, end)
   finally:
       client.cleanup()

   # Or use context manager pattern (if implemented)
   # with CAISOClient() as client:
   #     client.get_lmp(Market.DAM, start, end)

2. Check Return Values
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   success = client.get_lmp(Market.DAM, start, end)
   if not success:
       print("Download failed - check logs")
       # Handle failure

3. Use Appropriate Date Ranges
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from datetime import date, timedelta

   # Don't download future dates
   today = date.today()
   safe_date = today - timedelta(days=2)

   # Don't use excessively large ranges at once
   # Break into chunks for better reliability

4. Configure Logging
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import logging

   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
       handlers=[
           logging.FileHandler('isodart.log'),
           logging.StreamHandler()
       ]
   )

Type Hints
----------

ISO-DART v2.0 includes type hints for better IDE support:

.. code-block:: python

   from datetime import date
   from lib.iso.caiso import CAISOClient, Market

   # IDE will provide autocomplete and type checking
   client: CAISOClient = CAISOClient()
   market: Market = Market.DAM
   start: date = date(2024, 1, 1)

   success: bool = client.get_lmp(market, start, start)

Next Steps
----------

- See :doc:`command-line` for CLI usage
- See :doc:`configuration` for advanced config
- See :doc:`../tutorials/examples/index` for complete examples