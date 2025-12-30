CAISO API Reference
===================

.. module:: lib.iso.caiso
   :synopsis: CAISO OASIS API client

.. autoclass:: CAISOClient
   :members:
   :undoc-members:
   :show-inheritance:

   .. automethod:: __init__

Configuration
-------------

.. autoclass:: CAISOConfig
   :members:
   :undoc-members:

Market Types
------------

.. autoclass:: Market
   :members:
   :undoc-members:

Report Versions
---------------

.. autoclass:: ReportVersion
   :members:
   :undoc-members:

Main Methods
------------

Pricing Data
~~~~~~~~~~~~

.. automethod:: CAISOClient.get_lmp

   Download Locational Marginal Price (LMP) data.

   :param market: Market type (DAM, HASP, RTM, or RTPD)
   :type market: Market
   :param start_date: Start date for data
   :type start_date: date
   :param end_date: End date for data
   :type end_date: date
   :param step_size: Number of days per API request (default: 1)
   :type step_size: int
   :return: True if successful, False otherwise
   :rtype: bool

   Example::

       from datetime import date
       from lib.iso.caiso import CAISOClient, Market

       client = CAISOClient()
       success = client.get_lmp(
           market=Market.DAM,
           start_date=date(2024, 1, 1),
           end_date=date(2024, 1, 31)
       )
       client.cleanup()

.. automethod:: CAISOClient.get_ancillary_services_prices

   Download ancillary services clearing prices.

   :param market: Market type (DAM or RTM)
   :type market: Market
   :param start_date: Start date
   :type start_date: date
   :param end_date: End date
   :type end_date: date
   :param step_size: Days per request (default: 1)
   :type step_size: int
   :return: Success status
   :rtype: bool

.. automethod:: CAISOClient.get_fuel_prices

   Download fuel prices by region.

   :param start_date: Start date
   :type start_date: date
   :param end_date: End date
   :type end_date: date
   :param region: Fuel region ('ALL', 'SFBAY', 'SOCAL', 'NP15', 'SP15')
   :type region: str
   :param step_size: Days per request (default: 1)
   :type step_size: int
   :return: Success status
   :rtype: bool

.. automethod:: CAISOClient.get_ghg_allowance_prices

   Download greenhouse gas allowance prices.

Load Data
~~~~~~~~~

.. automethod:: CAISOClient.get_load_forecast

   Download system load forecasts.

   :param market: Forecast type (DAM, RTM, TWO_DA, SEVEN_DA)
   :type market: Market
   :param start_date: Start date
   :type start_date: date
   :param end_date: End date
   :type end_date: date
   :param step_size: Days per request
   :type step_size: int
   :return: Success status
   :rtype: bool

.. automethod:: CAISOClient.get_advisory_demand_forecast

   Download advisory (RTPD) demand forecast.

Generation Data
~~~~~~~~~~~~~~~

.. automethod:: CAISOClient.get_wind_solar_summary

   Download wind and solar generation summary.

   Includes current generation, forecasts, and available capacity
   for both wind and solar resources.

   :param start_date: Start date
   :type start_date: date
   :param end_date: End date
   :type end_date: date
   :param step_size: Days per request
   :type step_size: int
   :return: Success status
   :rtype: bool

.. automethod:: CAISOClient.get_system_load

   Download system load and resource schedules.

   :param market: Market type (DAM, RUC, HASP, RTM)
   :type market: Market
   :param start_date: Start date
   :type start_date: date
   :param end_date: End date
   :type end_date: date
   :param step_size: Days per request
   :type step_size: int
   :return: Success status
   :rtype: bool

Market Operations
~~~~~~~~~~~~~~~~~

.. automethod:: CAISOClient.get_market_power_mitigation

   Download Market Power Mitigation (MPM) status.

.. automethod:: CAISOClient.get_flex_ramp_requirements

   Download flexible ramping requirements.

.. automethod:: CAISOClient.get_flex_ramp_awards

   Download flexible ramping awards.

.. automethod:: CAISOClient.get_flex_ramp_demand_curve

   Download flexible ramping demand curves.

.. automethod:: CAISOClient.get_eim_transfer

   Download Energy Imbalance Market transfer data.

.. automethod:: CAISOClient.get_eim_transfer_limits

   Download Energy Imbalance Market transfer limits.

Ancillary Services
~~~~~~~~~~~~~~~~~~

.. automethod:: CAISOClient.get_ancillary_services_requirements

   Download ancillary services requirements.

   :param market: Market type (DAM, HASP, RTM)
   :type market: Market
   :param start_date: Start date
   :type start_date: date
   :param end_date: End date
   :type end_date: date
   :param anc_type: AS type ('ALL', 'RU', 'RD', 'SR', 'NR')
   :type anc_type: str
   :param anc_region: Region ('ALL' or specific)
   :type anc_region: str
   :param step_size: Days per request
   :type step_size: int
   :return: Success status
   :rtype: bool

.. automethod:: CAISOClient.get_ancillary_services_results

   Download ancillary services results/awards.

.. automethod:: CAISOClient.get_operating_reserves

   Download actual operating reserves deployed.

Utility Methods
~~~~~~~~~~~~~~~

.. automethod:: CAISOClient.cleanup

   Clean up temporary files created during download.

   Should be called after completing downloads to remove
   raw XML and CSV files.

   Example::

       client = CAISOClient()
       try:
           client.get_lmp(Market.DAM, start, end)
       finally:
           client.cleanup()  # Always clean up

Private Methods
---------------

.. automethod:: CAISOClient._build_params
.. automethod:: CAISOClient._make_request
.. automethod:: CAISOClient._extract_zip
.. automethod:: CAISOClient._xml_to_csv
.. automethod:: CAISOClient._process_csv

Examples
--------

Basic LMP Download
~~~~~~~~~~~~~~~~~~

::

    from datetime import date
    from lib.iso.caiso import CAISOClient, Market

    client = CAISOClient()

    # Download Day-Ahead LMP
    client.get_lmp(
        market=Market.DAM,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31)
    )

    client.cleanup()

Custom Configuration
~~~~~~~~~~~~~~~~~~~~

::

    from pathlib import Path
    from lib.iso.caiso import CAISOClient, CAISOConfig

    config = CAISOConfig(
        data_dir=Path('my_data/CAISO'),
        max_retries=5,
        timeout=60
    )

    client = CAISOClient(config)
    client.get_lmp(Market.DAM, date(2024, 1, 1), date(2024, 1, 31))
    client.cleanup()

Multiple Markets
~~~~~~~~~~~~~~~~

::

    from lib.iso.caiso import CAISOClient, Market

    client = CAISOClient()
    start = date(2024, 1, 1)
    end = date(2024, 1, 31)

    # Download multiple markets
    for market in [Market.DAM, Market.RTM]:
        print(f"Downloading {market.value}...")
        client.get_lmp(market, start, end)

    client.cleanup()

See Also
--------

* :doc:`../isos/caiso/overview` - CAISO data overview
* :doc:`../user-guide/python-api` - Python API guide
* :doc:`../tutorials/basic/first-download` - Tutorial

Notes
-----

* All dates are in Pacific Time
* API rate limiting is handled automatically
* Large date ranges are split into smaller requests
* Temporary files are created in raw_data/ directory
* Always call cleanup() to remove temporary files