Your First Data Download
========================

This tutorial walks you through downloading your first electricity market data with ISO-DART, from installation to analyzing your results.

**Time Required**: 15 minutes

**What You'll Learn**:

* How to download CAISO Day-Ahead LMP data
* How to verify your download succeeded
* How to load and explore the data with pandas
* How to create a simple price visualization

Prerequisites
-------------

Before starting, ensure you have:

* Python 3.10 or higher installed
* ISO-DART installed (:doc:`../../getting-started/installation`)
* A text editor or IDE
* Basic familiarity with Python (helpful but not required)

Step 1: Choose Your Data
-------------------------

For this tutorial, we'll download **CAISO Day-Ahead LMP** (Locational Marginal Prices) data because:

* CAISO requires no API keys
* Day-Ahead market data is stable and complete
* LMP is a fundamental electricity market metric
* The data is easy to understand and visualize

**What is LMP?**

Locational Marginal Price (LMP) is the cost to deliver one additional megawatt-hour (MWh) of electricity at a specific location. It reflects:

* Energy costs
* Transmission congestion
* Line losses

Higher LMP = electricity is more expensive at that location

Step 2: Download the Data
--------------------------

Choose one of three methods:

Method 1: Interactive Mode (Recommended for First Time)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Run interactive mode
   python isodart.py

Then follow the prompts:

.. code-block:: text

   What type of data? → (1) ISO Data
   Which ISO? → (1) CAISO
   What type of CAISO data? → (1) Pricing Data
   What type of pricing? → (1) LMP
   Which market? → (1) Day-Ahead Market
   Year: 2024
   Month: 1
   Day: 1
   Duration: 7

**Result**: Data for January 1-7, 2024 downloads to ``data/CAISO/``

Method 2: Command Line (Faster)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python isodart.py --iso caiso --data-type lmp --market dam \
     --start 2024-01-01 --duration 7

**Result**: Same data, but with a single command

Method 3: Python Script (Most Flexible)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``download_first.py``:

.. code-block:: python

   from datetime import date
   from lib.iso.caiso import CAISOClient, Market

   # Initialize client
   client = CAISOClient()

   # Download data
   success = client.get_lmp(
       market=Market.DAM,
       start_date=date(2024, 1, 1),
       end_date=date(2024, 1, 7)
   )

   # Check result
   if success:
       print("✓ Download successful!")
       print("Check data/CAISO/ for your files")
   else:
       print("✗ Download failed - check logs")

   # Clean up
   client.cleanup()

Run it:

.. code-block:: bash

   python download_first.py

Step 3: Verify Your Download
-----------------------------

Check that files were created:

.. code-block:: bash

   # List downloaded files
   ls -lh data/CAISO/

   # You should see files like:
   # 20240101_to_20240107_PRC_LMP_TH_NP15_GEN-APND.csv
   # 20240101_to_20240107_PRC_LMP_TH_SP15_GEN-APND.csv
   # 20240101_to_20240107_PRC_LMP_TH_ZP26_GEN-APND.csv

Each file represents prices at a different location (trading hub):

* **NP15**: Northern California (NP = North Path 15)
* **SP15**: Southern California (SP = South Path 15)
* **ZP26**: Kern County (ZP = Zone Path 26)

Quick verification:

.. code-block:: bash

   # Count rows in a file (should be 168 for 7 days × 24 hours)
   wc -l data/CAISO/20240101_to_20240107_PRC_LMP_TH_NP15_GEN-APND.csv

   # Output: 169 (168 data rows + 1 header)

   # Peek at the first few lines
   head -n 5 data/CAISO/20240101_to_20240107_PRC_LMP_TH_NP15_GEN-APND.csv

Step 4: Load the Data
----------------------

Create ``analyze_first.py``:

.. code-block:: python

   import pandas as pd

   # Load the data
   df = pd.read_csv('data/CAISO/20240101_to_20240107_PRC_LMP_TH_NP15_GEN-APND.csv')

   # Display basic information
   print("=== Dataset Info ===")
   print(f"Rows: {len(df)}")
   print(f"Columns: {len(df.columns)}")
   print(f"\nColumn names: {list(df.columns)}")

   # Show first few rows
   print("\n=== First 5 Rows ===")
   print(df.head())

   # Show data types
   print("\n=== Data Types ===")
   print(df.dtypes)

Run it:

.. code-block:: bash

   python analyze_first.py

**Expected Output**:

.. code-block:: text

   === Dataset Info ===
   Rows: 168
   Columns: 10

   Column names: ['INTERVALSTARTTIME_GMT', 'INTERVALENDTIME_GMT',
                  'OPR_DATE', 'INTERVAL_NUM', 'NODE_ID_XML', 'NODE_ID',
                  'NODE', 'MARKET_RUN_ID', 'DATA_ITEM', 'VALUE']

   === First 5 Rows ===
         OPR_DATE  INTERVAL_NUM                    DATA_ITEM   VALUE
   0   2024-01-01             1  TH_NP15_GEN-APND           32.45
   1   2024-01-01             2  TH_NP15_GEN-APND           29.87
   2   2024-01-01             3  TH_NP15_GEN-APND           27.33
   ...

Step 5: Explore the Data
-------------------------

Add to ``analyze_first.py``:

.. code-block:: python

   # Summary statistics
   print("\n=== Price Statistics ===")
   print(df['VALUE'].describe())

   # Find highest and lowest prices
   print("\n=== Price Extremes ===")
   print(f"Highest price: ${df['VALUE'].max():.2f}/MWh")
   print(f"   Occurred: {df.loc[df['VALUE'].idxmax(), 'OPR_DATE']}, "
         f"Hour {df.loc[df['VALUE'].idxmax(), 'INTERVAL_NUM']}")

   print(f"Lowest price: ${df['VALUE'].min():.2f}/MWh")
   print(f"   Occurred: {df.loc[df['VALUE'].idxmin(), 'OPR_DATE']}, "
         f"Hour {df.loc[df['VALUE'].idxmin(), 'INTERVAL_NUM']}")

   # Average price by day
   print("\n=== Daily Average Prices ===")
   daily_avg = df.groupby('OPR_DATE')['VALUE'].mean()
   for date, price in daily_avg.items():
       print(f"{date}: ${price:.2f}/MWh")

**Expected Output**:

.. code-block:: text

   === Price Statistics ===
   count    168.000000
   mean      38.245625
   std       12.438721
   min       18.45
   25%       29.32
   50%       35.67
   75%       45.23
   max       78.92

   === Price Extremes ===
   Highest price: $78.92/MWh
      Occurred: 2024-01-03, Hour 19
   Lowest price: $18.45/MWh
      Occurred: 2024-01-02, Hour 4

   === Daily Average Prices ===
   2024-01-01: $36.23/MWh
   2024-01-02: $32.45/MWh
   2024-01-03: $42.67/MWh
   ...

Step 6: Create Your First Visualization
----------------------------------------

Add to ``analyze_first.py``:

.. code-block:: python

   import matplotlib.pyplot as plt

   # Convert date and hour to datetime for plotting
   df['datetime'] = pd.to_datetime(df['OPR_DATE']) + \
                    pd.to_timedelta(df['INTERVAL_NUM'] - 1, unit='h')

   # Create the plot
   plt.figure(figsize=(14, 6))
   plt.plot(df['datetime'], df['VALUE'], linewidth=2, color='#2E86AB')

   # Customize the plot
   plt.xlabel('Date', fontsize=12)
   plt.ylabel('Price ($/MWh)', fontsize=12)
   plt.title('CAISO Day-Ahead LMP - NP15\nJanuary 1-7, 2024',
             fontsize=14, fontweight='bold')
   plt.grid(True, alpha=0.3, linestyle='--')

   # Add average line
   avg_price = df['VALUE'].mean()
   plt.axhline(y=avg_price, color='red', linestyle='--',
               linewidth=1.5, alpha=0.7,
               label=f'Average: ${avg_price:.2f}/MWh')

   plt.legend(fontsize=10)
   plt.xticks(rotation=45)
   plt.tight_layout()

   # Save and display
   plt.savefig('first_visualization.png', dpi=300, bbox_inches='tight')
   print("\n✓ Visualization saved as 'first_visualization.png'")

   plt.show()

Run it:

.. code-block:: bash

   python analyze_first.py

**Result**: A professional-looking line chart showing price variations over the week!

Understanding Your Results
---------------------------

What the Visualization Shows
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Your chart should show:

1. **Daily Patterns**: Prices typically higher during day (hours 12-20), lower at night
2. **Weekly Variation**: Different days may have different patterns
3. **Peak Hours**: Usually late afternoon/early evening (hour 18-20)
4. **Minimum Hours**: Usually early morning (hours 2-5)

Why Do Prices Vary?
~~~~~~~~~~~~~~~~~~~~

Electricity prices change based on:

* **Demand**: Higher demand = higher prices
* **Generation**: More expensive generators needed during peaks
* **Weather**: Hot/cold weather increases demand
* **Renewables**: More solar during day can lower prices
* **Day of week**: Weekday vs. weekend patterns differ

Common Patterns
~~~~~~~~~~~~~~~

You'll typically see:

* **Morning ramp**: Prices rise as people wake up (6-9 AM)
* **Midday plateau**: Stable prices when solar is abundant (10 AM - 2 PM)
* **Evening peak**: Highest prices as demand peaks (5-8 PM)
* **Night valley**: Lowest prices when demand is minimal (1-5 AM)

Step 7: Compare Multiple Locations
-----------------------------------

Let's compare prices across California:

.. code-block:: python

   import pandas as pd
   import matplotlib.pyplot as plt

   # Load data for three trading hubs
   np15 = pd.read_csv('data/CAISO/20240101_to_20240107_PRC_LMP_TH_NP15_GEN-APND.csv')
   sp15 = pd.read_csv('data/CAISO/20240101_to_20240107_PRC_LMP_TH_SP15_GEN-APND.csv')
   zp26 = pd.read_csv('data/CAISO/20240101_to_20240107_PRC_LMP_TH_ZP26_GEN-APND.csv')

   # Add datetime column to each
   for df in [np15, sp15, zp26]:
       df['datetime'] = pd.to_datetime(df['OPR_DATE']) + \
                        pd.to_timedelta(df['INTERVAL_NUM'] - 1, unit='h')

   # Create comparison plot
   plt.figure(figsize=(14, 8))

   plt.plot(np15['datetime'], np15['VALUE'], label='NP15 (Northern CA)',
            linewidth=2, alpha=0.8)
   plt.plot(sp15['datetime'], sp15['VALUE'], label='SP15 (Southern CA)',
            linewidth=2, alpha=0.8)
   plt.plot(zp26['datetime'], zp26['VALUE'], label='ZP26 (Kern County)',
            linewidth=2, alpha=0.8)

   plt.xlabel('Date', fontsize=12)
   plt.ylabel('Price ($/MWh)', fontsize=12)
   plt.title('CAISO LMP Comparison Across California\nJanuary 1-7, 2024',
             fontsize=14, fontweight='bold')
   plt.legend(fontsize=11)
   plt.grid(True, alpha=0.3)
   plt.xticks(rotation=45)
   plt.tight_layout()

   plt.savefig('location_comparison.png', dpi=300, bbox_inches='tight')
   print("✓ Comparison saved as 'location_comparison.png'")

   # Calculate price spreads
   print("\n=== Average Prices by Location ===")
   print(f"NP15 (Northern CA): ${np15['VALUE'].mean():.2f}/MWh")
   print(f"SP15 (Southern CA): ${sp15['VALUE'].mean():.2f}/MWh")
   print(f"ZP26 (Kern County): ${zp26['VALUE'].mean():.2f}/MWh")

   plt.show()

Troubleshooting
---------------

Issue: "FileNotFoundError"
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom**:

.. code-block:: python

   FileNotFoundError: data/CAISO/20240101_to_20240107_PRC_LMP_TH_NP15_GEN-APND.csv

**Solution**:

1. Check file actually exists: ``ls data/CAISO/``
2. Verify filename matches exactly (case-sensitive)
3. Make sure you're running from the ISO-DART directory

Issue: "No module named 'pandas'"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Solution**:

.. code-block:: bash

   pip install pandas matplotlib

Issue: Empty or Invalid Data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom**: File exists but has no data or all zeros

**Solutions**:

1. Check date range isn't in the future
2. Try a different date range (at least 2 days ago)
3. Verify CAISO OASIS is operational
4. Check logs: ``cat logs/isodart.log``

Issue: Plot Doesn't Display
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Solutions**:

1. **For scripts**: Add ``plt.show()`` at the end
2. **For Jupyter**: Use ``%matplotlib inline`` magic
3. **On servers**: Use ``plt.savefig()`` instead of ``plt.show()``

Next Steps
----------

Congratulations! You've completed your first data download and analysis. Here's what to explore next:

1. **Try Different Markets**

   * Download HASP or RTM data (5-minute resolution)
   * Compare day-ahead vs. real-time prices
   * :doc:`../intermediate/comparison`

2. **Explore More Data Types**

   * Load forecasts: :doc:`../../isos/caiso/load`
   * Wind and solar: :doc:`../../isos/caiso/generation`
   * Ancillary services: :doc:`../../isos/caiso/market`

3. **Try Other ISOs**

   * MISO: :doc:`../../isos/miso/overview`
   * NYISO: :doc:`../../isos/nyiso/overview`
   * SPP: :doc:`../../isos/spp/overview`

4. **Advanced Analysis**

   * :doc:`../examples/price-forecasting`
   * :doc:`../examples/weather-impact`
   * :doc:`../advanced/pipeline`

5. **Automate Downloads**

   * :doc:`../intermediate/automation`
   * Set up daily downloads
   * Create analysis pipelines

Practice Exercises
------------------

To reinforce what you've learned, try these exercises:

Exercise 1: Different Time Period
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download and analyze data for a different week. Do you see similar patterns?

.. code-block:: python

   # Try different dates
   client.get_lmp(Market.DAM, date(2024, 7, 1), date(2024, 7, 7))

Exercise 2: Calculate Volatility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Calculate price volatility (standard deviation):

.. code-block:: python

   volatility = df['VALUE'].std()
   print(f"Price volatility: ${volatility:.2f}/MWh")

   # Find hours with highest volatility
   hourly_vol = df.groupby('INTERVAL_NUM')['VALUE'].std()
   print(f"Most volatile hour: Hour {hourly_vol.idxmax()}")

Exercise 3: Weekend vs. Weekday
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Compare weekend and weekday prices:

.. code-block:: python

   df['datetime'] = pd.to_datetime(df['OPR_DATE']) + \
                    pd.to_timedelta(df['INTERVAL_NUM'] - 1, unit='h')
   df['dayofweek'] = df['datetime'].dt.dayofweek

   # 0-4 = Mon-Fri, 5-6 = Sat-Sun
   weekday = df[df['dayofweek'] < 5]['VALUE'].mean()
   weekend = df[df['dayofweek'] >= 5]['VALUE'].mean()

   print(f"Weekday average: ${weekday:.2f}/MWh")
   print(f"Weekend average: ${weekend:.2f}/MWh")
   print(f"Difference: ${weekday - weekend:.2f}/MWh")

Key Takeaways
-------------

.. important::

   **You've learned how to**:

   * ✓ Download electricity market data from CAISO
   * ✓ Verify your downloads succeeded
   * ✓ Load and explore data with pandas
   * ✓ Calculate summary statistics
   * ✓ Create professional visualizations
   * ✓ Identify price patterns

   **You now understand**:

   * What LMP represents
   * Why electricity prices vary
   * How to interpret price patterns
   * The structure of ISO-DART data files

Resources
---------

* :doc:`../../getting-started/quickstart` - More quick examples
* :doc:`../../user-guide/python-api` - Complete API reference
* :doc:`../../isos/caiso/overview` - CAISO data guide
* :doc:`../examples/index` - Analysis examples

Need Help?
----------

* Check :doc:`../../operations/troubleshooting`
* Ask on `GitHub Discussions <https://github.com/LLNL/ISO-DART/discussions>`_
* Report bugs at `GitHub Issues <https://github.com/LLNL/ISO-DART/issues>`_

Great job completing this tutorial! You're now ready to explore more advanced features of ISO-DART.