.. ISO-DART documentation master file

ISO-DART Documentation
======================

Welcome to the comprehensive documentation for **ISO-DART v2.0** - the Independent System Operator Data Automated Request Tool.

.. image:: https://img.shields.io/badge/python-3.10+-blue.svg
   :target: https://www.python.org/downloads/
   :alt: Python 3.10+

.. image:: https://img.shields.io/badge/License-MIT-yellow.svg
   :target: https://opensource.org/licenses/MIT
   :alt: MIT License

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
   :alt: Code style: black

.. image:: https://codecov.io/github/LLNL/ISO-DART/branch/dev/graph/badge.svg
   :target: https://codecov.io/github/LLNL/ISO-DART
   :alt: Codecov

----

Quick Links
-----------

.. grid:: 2

    .. grid-item-card:: 🚀 Quick Start
        :link: getting-started/quickstart
        :link-type: doc

        Get up and running in 5 minutes

    .. grid-item-card:: 📖 User Guide
        :link: user-guide/index
        :link-type: doc

        Complete usage documentation

    .. grid-item-card:: 🔌 ISO Coverage
        :link: isos/index
        :link-type: doc

        7 ISOs fully supported

    .. grid-item-card:: 💻 API Reference
        :link: api/index
        :link-type: doc

        Complete API documentation

----

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   getting-started/installation
   getting-started/quickstart
   getting-started/first-download
   getting-started/migration

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user-guide/index
   user-guide/interactive-mode
   user-guide/command-line
   user-guide/python-api
   user-guide/configuration
   user-guide/data-formats

.. toctree::
   :maxdepth: 2
   :caption: ISO Coverage

   isos/index
   isos/caiso/index
   isos/miso/index
   isos/nyiso/index
   isos/spp/index
   isos/bpa/index
   isos/pjm/index
   isos/isone/index

.. toctree::
   :maxdepth: 2
   :caption: Weather & Solar

   weather/index
   weather/overview
   weather/stations
   weather/solar
   weather/analysis

.. toctree::
   :maxdepth: 2
   :caption: Tutorials

   tutorials/basic/index
   tutorials/intermediate/index
   tutorials/advanced/index
   tutorials/examples/index

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/index
   api/caiso
   api/miso
   api/nyiso
   api/spp
   api/bpa
   api/pjm
   api/isone
   api/weather
   api/configuration

.. toctree::
   :maxdepth: 2
   :caption: Developer Guide

   developer/index
   developer/architecture
   developer/new-iso
   developer/testing
   developer/code-style
   developer/contributing
   developer/releases

.. toctree::
   :maxdepth: 2
   :caption: Operations

   operations/index
   operations/deployment
   operations/performance
   operations/monitoring
   operations/troubleshooting
   operations/faq

.. toctree::
   :maxdepth: 2
   :caption: Reference

   reference/index
   reference/cli-arguments
   reference/config-format
   reference/data-dictionary
   reference/iso-comparison
   reference/glossary
   reference/changelog

----

What is ISO-DART?
------------------

ISO-DART simplifies access to electricity market data across the United States. Whether you're a researcher, energy analyst, or data scientist, ISO-DART provides a unified interface to download pricing, load, generation, and weather data from multiple ISOs.

Key Features
~~~~~~~~~~~~

* 🔌 **7 ISO Coverage**: CAISO, MISO, NYISO, SPP, BPA, PJM, ISO-NE
* 🌤️ **Weather Integration**: Historical weather and solar radiation data
* 🚀 **Modern Python**: Type hints, async support, comprehensive error handling
* 🎯 **User-Friendly**: Interactive CLI or programmatic API
* 📊 **Analysis-Ready**: CSV output compatible with pandas, Excel, and R
* ⚡ **Performance**: Automatic retry logic, connection pooling, rate limiting

Supported ISOs
--------------

California (CAISO)
~~~~~~~~~~~~~~~~~~

Complete coverage of CAISO OASIS API including LMP (all markets), load forecasts, wind/solar generation, ancillary services, and EIM data.

:doc:`CAISO Documentation <isos/caiso/index>`

Midcontinent (MISO)
~~~~~~~~~~~~~~~~~~~

Full REST API integration for LMP, MCP, load/demand, fuel mix, generation, interchange, and constraints.

:doc:`MISO Documentation <isos/miso/index>`

New York (NYISO)
~~~~~~~~~~~~~~~~

LBMP pricing, load data, fuel mix, wind generation, BTM solar, bid data, and grid operations.

:doc:`NYISO Documentation <isos/nyiso/index>`

Southwest Power Pool (SPP)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

FTP-based access to LMP, MCP, operating reserves, load/resource forecasts, binding constraints, and market clearing.

:doc:`SPP Documentation <isos/spp/index>`

Bonneville Power Administration (BPA)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Historical yearly datasets for wind generation, total load, and operating reserves deployed.

:doc:`BPA Documentation <isos/bpa/index>`

PJM Interconnection
~~~~~~~~~~~~~~~~~~~

Data Miner 2 API integration for LMP, load forecasts, renewable generation, ancillary services, and grid data.

:doc:`PJM Documentation <isos/pjm/index>`

ISO New England (ISO-NE)
~~~~~~~~~~~~~~~~~~~~~~~~

Web Services API for LMP, regulation clearing prices, operating reserves, and system demand.

:doc:`ISO-NE Documentation <isos/isone/index>`

Quick Example
-------------

.. code-block:: bash

   # Interactive Mode (easiest)
   python isodart.py

   # Command Line (fastest)
   python isodart.py --iso caiso --data-type lmp --market dam \
     --start 2024-01-01 --duration 7

   # Python API (most flexible)

.. code-block:: python

   from datetime import date
   from lib.iso.caiso import CAISOClient, Market

   client = CAISOClient()
   client.get_lmp(Market.DAM, date(2024, 1, 1), date(2024, 1, 7))
   client.cleanup()

Reading Recommendations
-----------------------

New Users
~~~~~~~~~

1. Start with :doc:`getting-started/installation`
2. Follow :doc:`getting-started/quickstart`
3. Try :doc:`getting-started/first-download`
4. Explore :doc:`user-guide/interactive-mode`

Researchers & Analysts
~~~~~~~~~~~~~~~~~~~~~~

1. Review :doc:`isos/index` sections for your region
2. Study :doc:`user-guide/data-formats`
3. Explore :doc:`tutorials/examples/index`
4. Learn :doc:`weather/overview`

Developers & Power Users
~~~~~~~~~~~~~~~~~~~~~~~~~

1. Master :doc:`user-guide/python-api`
2. Understand :doc:`developer/architecture`
3. Review :doc:`api/index`
4. Build :doc:`tutorials/advanced/index`

System Administrators
~~~~~~~~~~~~~~~~~~~~~

1. Follow :doc:`operations/deployment`
2. Configure :doc:`operations/monitoring`
3. Optimize :doc:`operations/performance`
4. Review :doc:`operations/troubleshooting`

Getting Help
------------

Can't find what you're looking for?

1. **Search**: Use the search box above
2. **Index**: Check the :ref:`genindex`
3. **FAQ**: Browse :doc:`operations/faq`
4. **Issues**: `Report a bug <https://github.com/LLNL/ISO-DART/issues>`_
5. **Discussions**: `Ask the community <https://github.com/LLNL/ISO-DART/discussions>`_

Contributing
------------

Documentation contributions are welcome!

* :doc:`developer/contributing` - How to contribute
* :doc:`developer/docs-style` - Documentation style guide
* `Submit Documentation PR <https://github.com/LLNL/ISO-DART/pulls>`_

License & Citation
------------------

MIT License - Copyright (c) 2025, Lawrence Livermore National Security, LLC

See :doc:`reference/license` for full terms.

If you use ISO-DART in your research, please cite:

.. code-block:: bibtex

   @software{isodart2024,
     title = {ISO-DART: Independent System Operator Data Automated Request Tool},
     author = {Sotorrio, Pedro and Edmunds, Thomas and Musselman, Amelia and Sun, Chih-Che},
     year = {2024},
     version = {2.0.0},
     publisher = {Lawrence Livermore National Laboratory},
     doi = {LLNL-CODE-815334},
     url = {https://github.com/LLNL/ISO-DART}
   }

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

----

**Last Updated**: December 2024 | **Version**: 2.0.0