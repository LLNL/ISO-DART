Installation Guide
==================

This guide walks you through installing ISO-DART on your system.

System Requirements
-------------------

**Python Version**: 3.10 or higher

**Supported Operating Systems**:

* Linux (Ubuntu 20.04+, CentOS 7+, etc.)
* macOS (10.15+)
* Windows (10/11)

**Hardware Requirements**:

* Minimum: 2 GB RAM, 500 MB disk space
* Recommended: 4 GB RAM, 2 GB disk space (for data storage)

**Internet Connection**: Required for downloading data from ISOs

Quick Install
-------------

For most users, these three commands will install ISO-DART:

.. code-block:: bash

   git clone https://github.com/LLNL/ISO-DART.git
   cd ISO-DART
   pip install -r requirements.txt

Then verify:

.. code-block:: bash

   python isodart.py --help

If you see the help message, installation was successful! Skip to :ref:`verify-installation`.

Detailed Installation
---------------------

Step 1: Check Python Version
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open a terminal and check your Python version:

.. code-block:: bash

   python --version
   # or
   python3 --version

You should see ``Python 3.10.x`` or higher.

**If you don't have Python 3.10+**:

**Ubuntu/Debian**:

.. code-block:: bash

   sudo apt update
   sudo apt install python3.10 python3.10-venv python3.10-dev

**macOS (using Homebrew)**:

.. code-block:: bash

   brew install python@3.10

**Windows**:

Download from https://www.python.org/downloads/ and install.

Step 2: Install Git
~~~~~~~~~~~~~~~~~~~~

**Check if Git is installed**:

.. code-block:: bash

   git --version

**If Git is not installed**:

**Ubuntu/Debian**:

.. code-block:: bash

   sudo apt install git

**macOS**:

.. code-block:: bash

   brew install git
   # or use Xcode command line tools
   xcode-select --install

**Windows**:

Download from https://git-scm.com/download/win

Step 3: Clone Repository
~~~~~~~~~~~~~~~~~~~~~~~~~

Clone the ISO-DART repository:

.. code-block:: bash

   git clone https://github.com/LLNL/ISO-DART.git
   cd ISO-DART

This creates a directory called ``ISO-DART`` with all the source code.

Step 4: Create Virtual Environment (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Virtual environments keep ISO-DART's dependencies separate from your system Python.

.. code-block:: bash

   # Create virtual environment
   python3 -m venv venv

   # Activate it
   # On Linux/macOS:
   source venv/bin/activate

   # On Windows:
   venv\Scripts\activate

When activated, you'll see ``(venv)`` in your terminal prompt.

**Why use a virtual environment?**

* Isolates dependencies
* Prevents version conflicts
* Easy to delete and recreate
* Portable across systems

Step 5: Install Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With the virtual environment activated:

.. code-block:: bash

   pip install --upgrade pip
   pip install -r requirements.txt

This installs all required packages:

* ``requests`` - HTTP library for API calls
* ``pandas`` - Data manipulation
* ``numpy`` - Numerical computing
* ``meteostat`` - Weather data
* ``python-dateutil`` - Date parsing
* ``openpyxl`` - Excel file support

Installation takes 1-3 minutes depending on your connection.

Step 6: Verify Installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _verify-installation:

Test that everything works:

.. code-block:: bash

   # Check help message
   python isodart.py --help

   # Try a test download (interactive mode)
   python isodart.py

   # Run a quick test
   python isodart.py --iso caiso --data-type lmp --market dam \
     --start 2024-01-01 --duration 1 --verbose

If you see output and no errors, installation succeeded!

Alternative Installation Methods
---------------------------------

Method 1: Conda/Mamba
~~~~~~~~~~~~~~~~~~~~~

If you use Conda:

.. code-block:: bash

   # Create environment
   conda create -n isodart python=3.10
   conda activate isodart

   # Install dependencies
   cd ISO-DART
   pip install -r requirements.txt

Method 2: Pipenv
~~~~~~~~~~~~~~~~

If you use Pipenv:

.. code-block:: bash

   cd ISO-DART
   pipenv install
   pipenv shell

Method 3: System-Wide Install (Not Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. warning::

   This installs packages system-wide. Use virtual environments instead when possible.

.. code-block:: bash

   cd ISO-DART
   pip install --user -r requirements.txt

Method 4: Development Install
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you plan to modify ISO-DART code:

.. code-block:: bash

   cd ISO-DART
   pip install -e .
   pip install -r requirements.txt

   # Also install dev dependencies
   pip install pytest pytest-cov black flake8 mypy

Optional Dependencies
---------------------

For Documentation Building
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install -r docs/requirements-docs.txt

This installs Sphinx, theme, and extensions.

For Development
~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install pytest pytest-cov black flake8 mypy types-requests

For Data Analysis
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install matplotlib seaborn scipy scikit-learn jupyter

These aren't required but are useful for analysis.

Configuration
-------------

API Keys (Optional)
~~~~~~~~~~~~~~~~~~~

Some ISOs require API keys. You can add them later, but here's how to set up the config file:

Create ``user_config.ini`` in the ISO-DART directory:

.. code-block:: ini

   [miso]
   pricing_api_key = your-miso-pricing-key
   lgi_api_key = your-miso-lgi-key

   [pjm]
   api_key = your-pjm-key

   [isone]
   username = your-username
   password = your-password

   [API]
   api_key = your-nrel-api-key

   [USER_INFO]
   first_name = Your
   last_name = Name
   affiliation = Your Organization
   email = your.email@example.com

Get API keys from:

* MISO: https://data-exchange.misoenergy.org/
* PJM: https://dataminer2.pjm.com/
* ISO-NE: https://webservices.iso-ne.com/
* NREL (solar): https://developer.nrel.gov/signup/

Directory Structure
~~~~~~~~~~~~~~~~~~~

ISO-DART will create these directories automatically:

.. code-block:: text

   ISO-DART/
   ├── data/            # Downloaded data
   │   ├── CAISO/
   │   ├── MISO/
   │   ├── NYISO/
   │   ├── SPP/
   │   ├── BPA/
   │   ├── PJM/
   │   ├── ISONE/
   │   └── weather/
   ├── raw_data/        # Temporary files (auto-deleted)
   └── logs/            # Operation logs

Troubleshooting Installation
-----------------------------

Issue: "python: command not found"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Solution**: Try ``python3`` instead of ``python``

.. code-block:: bash

   python3 --version
   python3 isodart.py --help

Or create an alias:

.. code-block:: bash

   # Add to ~/.bashrc or ~/.zshrc
   alias python=python3

Issue: "pip: command not found"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Solution**: Try ``pip3`` or install pip:

.. code-block:: bash

   # Ubuntu/Debian
   sudo apt install python3-pip

   # macOS
   python3 -m ensurepip

   # Then use
   python3 -m pip install -r requirements.txt

Issue: Permission denied errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Solution 1**: Use virtual environment (recommended):

.. code-block:: bash

   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

**Solution 2**: Use ``--user`` flag:

.. code-block:: bash

   pip install --user -r requirements.txt

**Solution 3**: Fix permissions:

.. code-block:: bash

   # Only if you own the directory
   chmod -R u+w ISO-DART

Issue: SSL certificate errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Solution**:

.. code-block:: bash

   pip install --upgrade certifi
   pip install --upgrade requests

Issue: Dependency conflicts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Solution**: Create fresh virtual environment:

.. code-block:: bash

   # Remove old environment
   rm -rf venv

   # Create new one
   python3 -m venv venv
   source venv/bin/activate

   # Install fresh
   pip install --upgrade pip
   pip install -r requirements.txt

Issue: pandas or numpy install fails
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Ubuntu/Debian**:

.. code-block:: bash

   # Install build dependencies
   sudo apt install python3-dev build-essential

   # Then retry
   pip install -r requirements.txt

**macOS**:

.. code-block:: bash

   # Install Xcode command line tools
   xcode-select --install

   # Then retry
   pip install -r requirements.txt

**Windows**:

* Install Visual C++ Build Tools
* Or use pre-built wheels: ``pip install --only-binary :all: pandas numpy``

Platform-Specific Notes
-----------------------

Linux
~~~~~

**Ubuntu/Debian**:

.. code-block:: bash

   # Install all prerequisites at once
   sudo apt update
   sudo apt install python3.10 python3.10-venv python3-pip git

   # Clone and install
   git clone https://github.com/LLNL/ISO-DART.git
   cd ISO-DART
   python3.10 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

**CentOS/RHEL**:

.. code-block:: bash

   # Enable Python 3.10
   sudo yum install python310 python310-devel git

   # Clone and install
   git clone https://github.com/LLNL/ISO-DART.git
   cd ISO-DART
   python3.10 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

macOS
~~~~~

**Using Homebrew** (recommended):

.. code-block:: bash

   # Install prerequisites
   brew install python@3.10 git

   # Clone and install
   git clone https://github.com/LLNL/ISO-DART.git
   cd ISO-DART
   python3.10 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

**M1/M2 Mac Notes**:

Some packages may need Rosetta or native ARM builds:

.. code-block:: bash

   # If issues with pandas/numpy
   pip install --upgrade pip
   pip install --no-cache-dir pandas numpy

Windows
~~~~~~~

**Using PowerShell**:

.. code-block:: powershell

   # Check Python version
   python --version

   # Clone repository
   git clone https://github.com/LLNL/ISO-DART.git
   cd ISO-DART

   # Create virtual environment
   python -m venv venv

   # Activate (PowerShell)
   .\venv\Scripts\Activate.ps1

   # If execution policy error:
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

   # Install dependencies
   pip install -r requirements.txt

**Using Command Prompt**:

.. code-block:: bat

   REM Activate virtual environment
   venv\Scripts\activate.bat

   REM Install
   pip install -r requirements.txt

Updating ISO-DART
-----------------

To get the latest version:

.. code-block:: bash

   cd ISO-DART
   git pull origin main

   # Update dependencies if needed
   pip install --upgrade -r requirements.txt

Uninstalling
------------

To completely remove ISO-DART:

.. code-block:: bash

   # Deactivate virtual environment if active
   deactivate

   # Remove directory
   cd ..
   rm -rf ISO-DART

If you used system-wide install:

.. code-block:: bash

   pip uninstall requests pandas numpy meteostat python-dateutil openpyxl

Testing Your Installation
--------------------------

Run the test suite to verify everything works:

.. code-block:: bash

   # Install pytest if not already installed
   pip install pytest

   # Run tests
   pytest tests/ -v

   # Run with coverage
   pytest tests/ --cov=lib --cov-report=term-missing

All tests should pass. If any fail, check :doc:`../operations/troubleshooting`.

Post-Installation Setup
-----------------------

1. **Set up API keys** (if using MISO, PJM, ISO-NE, or NREL solar)
2. **Create a test download** to verify connectivity
3. **Set up your workflow** (see :doc:`quickstart`)
4. **Explore the documentation** (:doc:`../user-guide/index`)

Docker Installation (Advanced)
-------------------------------

If you prefer Docker:

.. code-block:: bash

   # Clone repository
   git clone https://github.com/LLNL/ISO-DART.git
   cd ISO-DART

   # Build image
   docker build -t isodart:latest .

   # Run container
   docker run -it -v $(pwd)/data:/app/data isodart:latest

   # Inside container
   python isodart.py --help

Create ``Dockerfile``:

.. code-block:: dockerfile

   FROM python:3.10-slim

   WORKDIR /app

   # Install dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   # Copy application
   COPY . .

   # Create directories
   RUN mkdir -p data logs raw_data

   # Default command
   CMD ["python", "isodart.py", "--help"]

Next Steps
----------

Now that ISO-DART is installed:

1. **Quick Start**: :doc:`quickstart` - Get running in 5 minutes
2. **First Download**: :doc:`../tutorials/basic/first-download` - Detailed tutorial
3. **Interactive Mode**: :doc:`../user-guide/interactive-mode` - User-friendly interface
4. **Command Line**: :doc:`../user-guide/command-line` - For automation

Getting Help
------------

If you encounter issues:

1. Check :doc:`../operations/troubleshooting`
2. Review :doc:`../operations/faq`
3. Search `GitHub Issues <https://github.com/LLNL/ISO-DART/issues>`_
4. Ask on `GitHub Discussions <https://github.com/LLNL/ISO-DART/discussions>`_
5. Create a new issue with:

   * Your OS and Python version
   * Full error message
   * Steps to reproduce

Installation Checklist
----------------------

.. checklist::

   - [ ] Python 3.10+ installed
   - [ ] Git installed
   - [ ] Repository cloned
   - [ ] Virtual environment created
   - [ ] Virtual environment activated
   - [ ] Dependencies installed
   - [ ] ``python isodart.py --help`` works
   - [ ] Data directories created
   - [ ] API keys configured (if needed)
   - [ ] Test download completed

Congratulations! You're ready to start downloading electricity market data.