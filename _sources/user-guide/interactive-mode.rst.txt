Interactive Mode Guide
======================

Overview
--------

Interactive mode provides a user-friendly command-line interface for downloading ISO data without needing to write code. It's perfect for:

* First-time users learning ISO-DART
* Quick one-off data downloads
* Exploring available data types
* Users who prefer menus over command-line arguments

Starting Interactive Mode
--------------------------

Simply run ISO-DART without any arguments:

.. code-block:: bash

   python isodart.py

You'll see the main menu:

.. code-block:: text

   ============================================================
    ISO-DART v2.0
    Independent System Operator Data Automated Request Tool
   ============================================================

   What type of data do you want to download?
     (1) ISO Data (CAISO, MISO, NYISO, SPP, BPA, PJM, ISO-NE)
     (2) Weather Data

   Your choice (1 or 2):

Main Menu Options
-----------------

Option 1: ISO Data
~~~~~~~~~~~~~~~~~~

Downloads electricity market data from Independent System Operators.

**Supported ISOs**:

1. **CAISO** - California Independent System Operator
2. **MISO** - Midcontinent Independent System Operator
3. **NYISO** - New York Independent System Operator
4. **SPP** - Southwest Power Pool
5. **BPA** - Bonneville Power Administration
6. **PJM** - PJM Interconnection
7. **ISO-NE** - ISO New England

Option 2: Weather Data
~~~~~~~~~~~~~~~~~~~~~~~

Downloads historical weather data from Meteostat and solar radiation data from NREL.

Complete Walkthrough: CAISO Example
------------------------------------

Let's walk through downloading CAISO Day-Ahead LMP data step-by-step.

Step 1: Select Data Source
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   Your choice (1 or 2): 1

   ============================================================
   ISO DATA SELECTION
   ============================================================

   Which ISO do you want data from?
     (1) CAISO - California Independent System Operator
     (2) MISO - Midcontinent Independent System Operator
     (3) NYISO - New York Independent System Operator
     (4) SPP - Southwest Power Pool
     (5) BPA - Bonneville Power Administration
     (6) PJM - Pennsylvania, New Jersey, Maryland Interconnection
     (7) ISO-NE - New England Independent System Operator

   Your choice (1-7): 1

Step 2: Select Data Category
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   ============================================================
   CAISO DATA SELECTION
   ============================================================

   What type of CAISO data?
     (1) Pricing Data
     (2) System Demand Data
     (3) Energy Data
     (4) Ancillary Services Data

   Your choice (1-4): 1

Step 3: Select Specific Data Type
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   ============================================================
   CAISO PRICING DATA
   ============================================================

   What type of pricing data?
     (1) Locational Marginal Prices (LMP)
     (2) Scheduling Point Tie Prices
     (3) Ancillary Services Clearing Prices
     (4) Intertie Constraint Shadow Prices
     (5) Fuel Prices
     (6) GHG Allowance Prices

   Your choice (1-6): 1

Step 4: Select Market
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   Which energy market?
     (1) Day-Ahead Market (DAM)
     (2) Hour-Ahead Scheduling Process (HASP)
     (3) Real-Time Market (RTM)
     (4) Real-Time Pre-Dispatch (RTPD)

   Your choice (1-4): 1

Step 5: Enter Date Range
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   ============================================================
   DATE SELECTION
   ============================================================

   Please enter the start date and duration:
     Year (4-digit format, e.g., 2024): 2024
     Month (1-12): 1
     Day (1-31): 1

   ✓ Date range: 2024-01-01 to 2024-01-08

     Duration (in days): 7

   ✓ Date range: 2024-01-01 to 2024-01-08

Step 6: Download Progress
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   📥 Downloading DAM LMP data...
      Date range: 2024-01-01 to 2024-01-08
      This may take a few minutes...

   2024-01-01 11:45:23 - INFO - Request successful
   2024-01-01 11:45:28 - INFO - Saved: data/CAISO/20240101_to_20240108_PRC_LMP_TH_NP15_GEN-APND.csv

   ✅ Download complete!
      Data saved to: data/CAISO/

Navigation Tips
---------------

Going Back
~~~~~~~~~~

* Press ``Ctrl+C`` at any prompt to exit
* The program will guide you back to the main menu after each download
* You can start a new download immediately

Input Validation
~~~~~~~~~~~~~~~~

The interactive mode validates all inputs:

.. code-block:: text

   Your choice (1-4): 5
   Please enter a number between 1 and 4

   Your choice (1-4): abc
   Please enter a valid number

   Your choice (1-4): 2
   ✓ Valid choice

Date Validation
~~~~~~~~~~~~~~~

Dates are validated to ensure they exist and aren't in the future:

.. code-block:: text

   Year (4-digit format): 2024
   Month (1-12): 2
   Day (1-31): 31

   ❌ Invalid date: 2024-02-31 doesn't exist
   Please try again with valid values.

ISO-Specific Features
----------------------

CAISO Interactive Mode
~~~~~~~~~~~~~~~~~~~~~~~

**Available Data Categories**:

1. **Pricing Data**

   * Locational Marginal Prices (all markets)
   * Scheduling Point Tie Prices
   * Ancillary Services Clearing Prices
   * Constraint Shadow Prices
   * Fuel Prices
   * GHG Allowance Prices

2. **System Demand Data**

   * Standard Demand Forecasts (DAM, 2DA, 7DA, RTM)
   * Advisory Demand Forecast (RTPD)

3. **Energy Data**

   * System Load and Resource Schedules
   * Market Power Mitigation Status
   * Flexible Ramping (Requirements, Awards, Demand Curves)
   * EIM Transfer and Limits
   * Wind and Solar Summary

4. **Ancillary Services Data**

   * AS Requirements
   * AS Results/Awards
   * Actual Operating Reserves

MISO Interactive Mode
~~~~~~~~~~~~~~~~~~~~~

**Available Data Categories**:

1. **Pricing Data (LMP & MCP)**

   * Day-Ahead ExAnte/ExPost LMP
   * Real-Time ExAnte/ExPost LMP
   * ASM Market Clearing Prices

2. **Load & Demand Data**

   * Day-Ahead Demand
   * Real-Time Forecast/Actual
   * State Estimator Load
   * Medium-Term Load Forecast

3. **Generation Data**

   * Cleared Generation (Physical/Virtual)
   * Generation by Fuel Type
   * Offered Generation (ECOMAX/ECOMIN)
   * Fuel on the Margin

4. **Interchange Data**

   * Net Scheduled/Actual Interchange
   * Historical Interchange

5. **Outages & Constraints**

   * Outage Forecasts
   * Real-Time Outages
   * Binding Constraints

NYISO Interactive Mode
~~~~~~~~~~~~~~~~~~~~~~

**Available Data Categories**:

1. **Pricing Data**

   * LBMP (Zonal/Generator, DAM/RTM)
   * Ancillary Services Prices

2. **Power Grid Data**

   * Outages (Scheduled/Actual)
   * Transmission Constraints

3. **Load Data**

   * ISO Load Forecast
   * Zonal Bid Load
   * Weather Forecast
   * Actual Load

4. **Bid Data**

   * Generator and AS Bids
   * Load Bids
   * Transaction Bids
   * Commitment Parameters

5. **Generation Data**

   * Fuel Mix
   * Interface Flows
   * Wind Generation
   * BTM Solar

SPP Interactive Mode
~~~~~~~~~~~~~~~~~~~~

**Available Data Categories**:

1. **Pricing Data**

   * LMP (by Settlement Location or Bus)
   * Market Clearing Prices (MCP)

2. **Operating Reserves**

   * Real-Time Operating Reserves

3. **Binding Constraints**

   * Day-Ahead and RTBM Constraints

4. **Fuel On Margin**

   * 5-minute fuel mix data

5. **Load Forecasts**

   * Short-Term Load Forecast (STLF)
   * Medium-Term Load Forecast (MTLF)

6. **Resource Forecasts**

   * Short-Term Resource Forecast (STRF)
   * Medium-Term Resource Forecast (MTRF)

7. **Clearing Data**

   * Market Clearing
   * Virtual Clearing

BPA Interactive Mode
~~~~~~~~~~~~~~~~~~~~

BPA provides historical yearly datasets:

**Available Data Types**:

1. **Wind Generation and Total Load**

   * Hourly wind generation (MW)
   * Hourly total load (MW)
   * 5-minute resolution
   * Full calendar year datasets

2. **Operating Reserves Deployed**

   * Regulation Up/Down reserves
   * Contingency reserves
   * 5-minute resolution

3. **Outages**

**Special Features**:

* Data organized by full calendar year
* Optional date filtering within year
* Automatic download of Excel files

Weather Data Interactive Mode
------------------------------

Step-by-Step: Weather Download
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Select Weather Data**:

.. code-block:: text

   Your choice (1 or 2): 2

2. **Enter Date Range**:

.. code-block:: text

   Please enter the start date and duration:
     Year (4-digit format): 2024
     Month (1-12): 1
     Day (1-31): 1
     Duration (in days): 30

3. **Select Location**:

.. code-block:: text

   US State (2-letter code, e.g., CA): CA

   📥 Finding weather stations in CA...

   Found 150 weather stations with data:
   ────────────────────────────────────────
     (1) San Francisco International Airport
     (2) Los Angeles International Airport
     (3) Sacramento Executive Airport
     (4) San Diego International Airport
     (5) Oakland Metropolitan Airport
     ... and 145 more

   Select station (1-150): 1

4. **Download Progress**:

.. code-block:: text

   📍 Station: San Francisco International Airport
      Location: 37.6189, -122.3750
      Elevation: 4m

   📥 Downloading weather data...

   ✅ Download complete!

   📊 Data Summary:
      Records: 720
      Columns: temperature, dew_point, relative_humidity,
               precipitation, wind_speed, air_pressure,
               weather_condition
      Date range: 2024-01-01 00:00:00 to 2024-01-31 23:00:00

5. **Optional Solar Data**:

.. code-block:: text

   ☀️  Download solar data from NSRDB? (y/n): y

   Please enter your NREL API key (or press Enter to skip):

If you don't have an API key, the program will open your browser to the registration page.

Tips for Efficient Use
----------------------

Batch Downloads
~~~~~~~~~~~~~~~

You can run multiple downloads in sequence without restarting:

.. code-block:: text

   ✅ Download complete!
      Data saved to: data/CAISO/

   Press Enter to download more data, or Ctrl+C to exit...

   [Press Enter]

   ============================================================
    ISO-DART v2.0
   ============================================================

   What type of data do you want to download?
     (1) ISO Data
     (2) Weather Data

Taking Notes
~~~~~~~~~~~~

Keep track of what you're downloading:

.. code-block:: bash

   # Redirect output to a log file
   python isodart.py 2>&1 | tee download_log.txt

   # Review later
   cat download_log.txt

Large Date Ranges
~~~~~~~~~~~~~~~~~

For large date ranges, the interactive mode shows progress:

.. code-block:: text

   Duration (in days): 365

   You selected 365 days (over a year). Continue? (y/n): y

   ✓ Date range: 2024-01-01 to 2024-12-31

   📥 Downloading DAM LMP data...
      This may take 15-20 minutes for a full year...
      Progress: [████████████░░░░░░░░] 60%

Keyboard Shortcuts
~~~~~~~~~~~~~~~~~~

* ``Ctrl+C`` - Exit program at any time
* ``Ctrl+Z`` - Pause program (Unix/Linux/Mac)
* ``Enter`` - Accept default value (when available)
* ``↑/↓`` - Command history (in some terminals)

Common Workflows
----------------

Daily Price Check
~~~~~~~~~~~~~~~~~

Quick workflow for checking yesterday's prices:

.. code-block:: text

   1. python isodart.py
   2. Select: (1) ISO Data
   3. Select: (1) CAISO
   4. Select: (1) Pricing Data
   5. Select: (1) LMP
   6. Select: (1) DAM
   7. Enter yesterday's date
   8. Duration: 1 day

   Total time: ~2 minutes

Weekly Data Collection
~~~~~~~~~~~~~~~~~~~~~~

Collecting a week of data:

.. code-block:: text

   1. python isodart.py
   2. Select your ISO
   3. Select your data type
   4. Enter start date (7 days ago)
   5. Duration: 7 days

   Repeat for different data types as needed

Monthly Analysis Prep
~~~~~~~~~~~~~~~~~~~~~

Preparing for monthly analysis:

.. code-block:: text

   # Download multiple data types for the same month

   Download 1: LMP data (DAM and RTM)
   Download 2: Load forecast data
   Download 3: Wind and solar data
   Download 4: Weather data for correlation

   All for the same date range (e.g., Jan 1-31, 2024)

Troubleshooting Interactive Mode
---------------------------------

Issue: "Invalid choice" errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause**: Entering values outside the valid range

**Solution**:

* Read the prompt carefully for valid options
* Enter only the number, not extra text
* Check for typos

Issue: No data stations found (weather)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause**: No weather stations have data for your date range in that state

**Solution**:

* Try a different date range
* Try a neighboring state
* Check if state code is correct (2 letters, e.g., "CA" not "California")

Issue: Download hangs or is very slow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause**: Large date range or slow ISO API

**Solution**:

* Be patient - large downloads can take 10-20 minutes
* Try a smaller date range first
* Check your internet connection
* Try during off-peak hours (early morning)

Issue: "Connection error" or "Timeout"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause**: Network issues or ISO API unavailable

**Solution**:

* Check your internet connection
* Verify ISO website is accessible in browser
* Wait a few minutes and retry
* Try a different date range

Getting Help
------------

Within Interactive Mode
~~~~~~~~~~~~~~~~~~~~~~~~

Look for help text in the prompts:

.. code-block:: text

   What type of pricing data?
     (1) Locational Marginal Prices (LMP)
         - Available for DAM, HASP, RTM, RTPD
         - Most common pricing metric
         - Hourly or 5-minute intervals

After Download
~~~~~~~~~~~~~~

The program shows you where files were saved:

.. code-block:: text

   ✅ Download complete!
      Data saved to: data/CAISO/
      Files: 20240101_to_20240108_PRC_LMP_*.csv

Documentation
~~~~~~~~~~~~~

* Check :doc:`../getting-started/quickstart` for examples
* See ISO-specific guides: :doc:`../isos/index`
* Review :doc:`command-line` for automation options

Exiting Interactive Mode
-------------------------

Graceful Exit
~~~~~~~~~~~~~

Press ``Ctrl+C`` at any prompt:

.. code-block:: text

   Your choice (1-4): ^C

   Operation cancelled by user

   Thank you for using ISO-DART!

The program will:

1. Cancel any in-progress downloads
2. Clean up temporary files
3. Close connections properly
4. Save any completed downloads

Comparison with Other Modes
----------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Feature
     - Interactive Mode
     - Command-Line Mode
   * - **Ease of Use**
     - ⭐⭐⭐⭐⭐ Very Easy
     - ⭐⭐⭐ Moderate
   * - **Speed**
     - ⭐⭐⭐ Moderate
     - ⭐⭐⭐⭐⭐ Fast
   * - **Automation**
     - ❌ Not suitable
     - ✅ Excellent
   * - **Learning Curve**
     - ⭐⭐⭐⭐⭐ Minimal
     - ⭐⭐⭐ Some learning
   * - **Flexibility**
     - ⭐⭐⭐ Good
     - ⭐⭐⭐⭐⭐ Excellent
   * - **Best For**
     - First-time users, exploration
     - Automation, scripting

Next Steps
----------

After mastering interactive mode:

1. **Try Command-Line Mode**: :doc:`command-line`
2. **Learn Python API**: :doc:`python-api`
3. **Explore Examples**: :doc:`../tutorials/examples/index`

See Also
--------

* :doc:`../getting-started/quickstart` - Quick start tutorial
* :doc:`command-line` - Command-line usage guide
* :doc:`python-api` - Python API documentation