# ISO-DART v2.0
## Independent System Operator Data Automated Request Tool

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/github/LLNL/ISO-DART/branch/dev/graph/badge.svg)](https://codecov.io/github/LLNL/ISO-DART)

**A comprehensive Python tool for downloading and analyzing electricity market data from Independent System Operators (ISOs) and weather data sources.**

## What's New in v2.0

### 🚀 Major Improvements
- **Modern Python practices**: Type hints, dataclasses, enums, and proper error handling
- **Command-line interface**: Use arguments or interactive mode
- **Robust API handling**: Automatic retries, better error messages, connection pooling
- **Enhanced logging**: Track operations and debug issues easily
- **Comprehensive testing**: Unit and integration test suites
- **Complete coverage**: All ISO data methods accessible via interactive mode
- **Updated dependencies**: Compatible with latest pandas, requests, and meteostat

### 📊 Supported Data Sources

#### Independent System Operators (ISOs)

**CAISO (California ISO)** - ✅ Fully supported
- **Pricing Data**: LMP (DAM, HASP, RTM, RTPD), Scheduling Point Tie Prices, AS Clearing Prices, Constraint Shadow Prices, Fuel Prices, GHG Allowance Prices
- **Load Data**: Load Forecasts (DAM, RTM, 2DA, 7DA, RTPD Advisory)
- **Energy Data**: System Load & Resources, Market Power Mitigation, Flexible Ramping (Requirements, Awards, Demand Curves), EIM Transfer & Limits, Wind & Solar Summary
- **Ancillary Services**: Requirements, Results/Awards, Operating Reserves

**MISO (Midcontinent ISO)** - ✅ Fully supported
- **LMP Data**: Day-Ahead EPNodes, DA ExAnte/ExPost, Real-Time EPNodes, RT 5-min ExAnte, RT Final
- **MCP Data**: ASM DA ExAnte/ExPost, ASM RT 5-min ExAnte/Final, DA ExAnte/ExPost Ramp
- **Summary Reports**: Daily Forecast/Actual Load by LRZ, Regional Forecast/Actual Load
- **Generation Data**: Fuel Mix, Area Control Error (ACE), Wind Forecast/Actual, Market Totals

**NYISO (New York ISO)** - ✅ Fully supported
- **Pricing Data**: LBMP (Zonal/Generator, DAM/RTM), Ancillary Services Prices
- **Power Grid**: Outages (Scheduled/Actual), Constraints
- **Load Data**: ISO Forecast, Zonal Bid Load, Weather Forecast, Actual Load
- **Bid Data**: Generator/AS Bids, Load Bids, Transaction Bids, Commitment Parameters
- **Generation Data**: Fuel Mix, Interface Flows, Wind Generation, BTM Solar

**SPP (Southwest Power Pool)** - ✅ Fully supported
- **Pricing Data**: LMP (DA, RTBM) by Settlement Location and by Bus, MCP (DA, RTBM)
- **Constraint Data**: Binding Constraints (DA, RTBM)
- **Ancillary Services**: Operating Reserves (RTBM)
- **Fuel Data**: Fuel On Margin
- **Load Data**: Load Forecasts (short-term, medium-term)
- **Resource Data**: Resource (solar + wind) Forecasts (day-ahead, short-term)
- **Clearing Data**: Day-Ahead Market Clearing data, Day-Ahead Virtual Clearing data 

#### Weather & Solar Data
- **Meteostat**: Historical weather data for any US location (temperature, humidity, wind, precipitation, etc.)
- **NSRDB** (National Solar Radiation Database): Solar irradiance data (GHI, DHI, DNI)

## Installation

### Requirements
- Python 3.10 or higher
- Git

### Setup

```bash
# Clone the repository
git clone https://github.com/LLNL/ISO-DART.git
cd ISO-DART

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### Interactive Mode (Recommended for New Users)

Simply run:
```bash
python isodart.py
```

The interactive menu will guide you through:
1. Selecting ISO or weather data
2. Choosing specific data type
3. Entering date range
4. Selecting location (for weather data)

**Example workflow:**
```
ISO-DART v2.0
Independent System Operator Data Automated Request Tool
============================================================

What type of data do you want to download?
  (1) ISO Data (CAISO, MISO, NYISO)
  (2) Weather Data

Your choice (1 or 2): 1

ISO DATA SELECTION
============================================================

Which ISO do you want data from?
  (1) CAISO - California Independent System Operator
  (2) MISO - Midcontinent Independent System Operator
  (3) NYISO - New York Independent System Operator

Your choice (1, 2, or 3): 1
```

### Command-Line Mode

For automation and scripting:

```bash
# Download CAISO Day-Ahead LMP data
python isodart.py --iso caiso --data-type lmp --market dam \
  --start 2024-01-01 --duration 7

# Download MISO LMP data
python isodart.py --iso miso --data-type lmp \
  --start 2024-01-01 --duration 30

# Download NYISO LBMP data
python isodart.py --iso nyiso --data-type lbmp \
  --start 2024-01-01 --duration 7

# Download weather data for California
python isodart.py --data-type weather --state CA \
  --start 2024-01-01 --duration 30
```

### Command-Line Arguments

```
--iso {caiso,miso,nyiso}     ISO to download from
--data-type TYPE             Data type (lmp, load, weather, etc.)
--market {dam,rtm,hasp,rtpd} Energy market type
--start YYYY-MM-DD           Start date
--duration N                 Duration in days
--state XX                   US state code (for weather)
--verbose                    Enable detailed logging
--interactive                Force interactive mode
--config PATH                Path to configuration file
```

## Usage Examples

### CAISO Examples

#### Download Day-Ahead LMP for January 2024
```bash
python isodart.py --iso caiso --data-type lmp --market dam \
  --start 2024-01-01 --duration 31
```

#### Download Real-Time Load Forecast
```bash
python isodart.py --iso caiso --data-type load --market rtm \
  --start 2024-06-01 --duration 7
```

#### Download Wind and Solar Summary
```bash
python isodart.py --iso caiso --data-type wind-solar \
  --start 2024-01-01 --duration 30
```

### MISO Examples

#### Download Day-Ahead LMP Data
```bash
python isodart.py --iso miso --data-type lmp \
  --start 2024-01-01 --duration 7
```

#### Download Fuel Mix Data
```bash
python isodart.py --iso miso --data-type fuel-mix \
  --start 2024-01-01 --duration 30
```

### NYISO Examples

#### Download Day-Ahead Zonal LBMP
```bash
python isodart.py --iso nyiso --data-type lbmp --market dam \
  --start 2024-01-01 --duration 7
```

#### Download Wind Generation Data
```bash
python isodart.py --iso nyiso --data-type wind \
  --start 2024-01-01 --duration 30
```

### Weather Data Examples

#### Download Weather Data for San Francisco Area
```bash
python isodart.py --data-type weather --state CA \
  --start 2024-01-01 --duration 365
```

The tool will:
1. Find all weather stations in California
2. Filter stations with data for your date range
3. Let you select the closest station
4. Download hourly weather data
5. Optionally download solar data from NSRDB

## Python API Usage

For integration into your own scripts:

### CAISO Example

```python
from datetime import date
from lib.iso.caiso import CAISOClient, Market

# Initialize client
client = CAISOClient()

# Download Day-Ahead LMP data
success = client.get_lmp(
    market=Market.DAM,
    start_date=date(2024, 1, 1),
    end_date=date(2024, 1, 31)
)

if success:
    print("Data downloaded to data/CAISO/")

# Download wind and solar summary
client.get_wind_solar_summary(
    start_date=date(2024, 1, 1),
    end_date=date(2024, 1, 31)
)

# Clean up temporary files
client.cleanup()
```

### MISO Example

```python
from datetime import date
from lib.iso.miso import MISOClient

# Initialize client
client = MISOClient()

# Download Day-Ahead ExAnte LMP
client.get_lmp("da_exante", date(2024, 1, 1), duration=30)

# Download wind generation forecast
client.get_wind_forecast(date(2024, 1, 1), duration=7)

# Download fuel mix
client.get_fuel_mix(date(2024, 1, 1), duration=30)
```

### NYISO Example

```python
from datetime import date
from lib.iso.nyiso import NYISOClient, NYISOMarket

# Initialize client
client = NYISOClient()

# Download Day-Ahead zonal LBMP
client.get_lbmp(NYISOMarket.DAM, "zonal", date(2024, 1, 1), duration=30)

# Download fuel mix
client.get_fuel_mix(date(2024, 1, 1), duration=7)

# Download wind generation
client.get_wind_generation(date(2024, 1, 1), duration=30)

# Clean up
client.cleanup()
```

### Weather API

```python
from datetime import date
from lib.weather.client import WeatherClient

# Initialize client
client = WeatherClient()

# Download weather data
success = client.download_weather_data(
    state='CA',
    start_date=date(2024, 1, 1),
    duration=30,
    interactive=False  # Auto-select first station
)

# Optionally download solar data
if success:
    client.download_solar_data(year=2024)
```

## Data Output

### Directory Structure
```
iso-dart/
├── data/
│   ├── CAISO/           # CAISO data files
│   ├── MISO/            # MISO data files
│   ├── NYISO/           # NYISO data files
│   ├── weather/         # Weather data
│   └── solar/           # Solar radiation data
├── raw_data/            # Temporary files (auto-cleaned)
├── logs/                # Application logs
└── user_config.ini      # API keys (created on first use)
```

### Output File Formats

#### CAISO Files
Format: `{start_date}_to_{end_date}_{query_name}_{data_item}.csv`

Example: `20240101_to_20240131_PRC_LMP_TH_NP15_GEN-APND.csv`

Typical columns:
- `OPR_DATE`: Operating date
- `INTERVAL_NUM`: Time interval within the day (1-24 for hourly, 1-96 for 15-min)
- `DATA_ITEM`: Specific location/node/resource
- `VALUE`: Price ($/MWh), load (MW), or other metric
- `MW`: Power values (for load data)

#### MISO Files
Format: `{date}_{data_type}.csv` or `{date}_{data_type}.xls`

Examples:
- `20240101_da_exante_lmp.csv`
- `20240101_fuel_on_the_margin.xls`

#### NYISO Files
Format: `{start_date}_to_{end_date}_{dataid}_{aggregation}.csv`

Example: `20240101_to_20240131_damlbmp_zone.csv`

#### Weather Files
Format: `{start_date}_to_{end_date}_{station_name}_{state}.csv`

Example: `2024-01-01_to_2024-01-31_San_Francisco_Airport_CA.csv`

Columns:
- `time`: Timestamp (index)
- `temperature`: Temperature (°F)
- `dew_point`: Dew point (°F)
- `relative_humidity`: Humidity (%)
- `precipitation`: Precipitation (inches)
- `wind_speed`: Wind speed (mph)
- `air_pressure`: Air pressure (hPa)
- `weather_condition`: Weather description (Clear, Rain, etc.)

## Data Analysis Examples

### Load and Visualize CAISO LMP

```python
import pandas as pd
import matplotlib.pyplot as plt

# Load the data
df = pd.read_csv('data/CAISO/20240101_to_20240107_PRC_LMP_TH_NP15_GEN-APND.csv')

# Convert to datetime
df['OPR_DT'] = pd.to_datetime(df['OPR_DATE'])

# Plot prices over time
plt.figure(figsize=(12, 6))
plt.plot(df['OPR_DT'], df['VALUE'])
plt.xlabel('Date')
plt.ylabel('Price ($/MWh)')
plt.title('Day-Ahead LMP - NP15 Generator')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('lmp_plot.png')
plt.show()
```

### Basic Statistics

```python
import pandas as pd

# Load data
df = pd.read_csv('data/CAISO/20240101_to_20240107_PRC_LMP_TH_NP15_GEN-APND.csv')

# Summary statistics
print("Price Statistics:")
print(f"  Mean: ${df['VALUE'].mean():.2f}/MWh")
print(f"  Min:  ${df['VALUE'].min():.2f}/MWh")
print(f"  Max:  ${df['VALUE'].max():.2f}/MWh")
print(f"  Std:  ${df['VALUE'].std():.2f}/MWh")

# Find peak price hours
peak_hours = df.nlargest(10, 'VALUE')[['OPR_DATE', 'INTERVAL_NUM', 'VALUE']]
print("\nTop 10 Peak Price Hours:")
print(peak_hours)
```

### Analyze Weather Data

```python
import pandas as pd
import matplotlib.pyplot as plt

# Load weather data
df = pd.read_csv('data/weather/2024-01-01_to_2024-01-31_San_Francisco_CA.csv',
                 index_col='time', parse_dates=True)

# Plot temperature and wind
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

# Temperature
ax1.plot(df.index, df['temperature'])
ax1.set_ylabel('Temperature (°F)')
ax1.set_title('Temperature Over Time')
ax1.grid(True)

# Wind Speed
ax2.plot(df.index, df['wind_speed'])
ax2.set_ylabel('Wind Speed (mph)')
ax2.set_xlabel('Date')
ax2.set_title('Wind Speed Over Time')
ax2.grid(True)

plt.tight_layout()
plt.savefig('weather_analysis.png')
plt.show()
```

### Compare Multiple Locations

```python
import pandas as pd
import matplotlib.pyplot as plt

# Load data for multiple locations
locations = ['TH_NP15_GEN-APND', 'TH_SP15_GEN-APND', 'TH_ZP26_GEN-APND']
data = {}

for loc in locations:
    file = f'data/CAISO/20240101_to_20240107_PRC_LMP_{loc}.csv'
    df = pd.read_csv(file)
    df['OPR_DT'] = pd.to_datetime(df['OPR_DATE'])
    data[loc] = df

# Plot comparison
plt.figure(figsize=(14, 6))
for loc, df in data.items():
    plt.plot(df['OPR_DT'], df['VALUE'], label=loc.replace('TH_', '').replace('-APND', ''), alpha=0.7)

plt.xlabel('Date')
plt.ylabel('Price ($/MWh)')
plt.title('LMP Comparison Across Locations')
plt.legend()
plt.grid(True, alpha=0.3)
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('location_comparison.png')
plt.show()
```

## Configuration

### User Configuration File

For NSRDB solar data, create `user_config.ini`:

```ini
[API]
api_key = your_nrel_api_key_here

[USER_INFO]
first_name = Your
last_name = Name
affiliation = Your Organization
email = your.email@example.com
```

Get your NREL API key at: https://developer.nrel.gov/signup/

### Custom Configuration

Create a YAML config file for advanced settings:

```yaml
# config.yaml
caiso:
  base_url: http://oasis.caiso.com/oasisapi/SingleZip
  max_retries: 3
  timeout: 30
  step_size: 1  # days per request

miso:
  base_url: https://docs.misoenergy.org/marketreports/
  max_retries: 3
  timeout: 30

nyiso:
  base_url: http://mis.nyiso.com/public/csv
  max_retries: 3
  timeout: 30

weather:
  data_dir: data/weather
  solar_dir: data/solar

logging:
  level: INFO
  file: logs/isodart.log
```

Use with: `python isodart.py --config config.yaml`

## Automation

### Automated Daily Download

Save as `daily_download.py`:

```python
#!/usr/bin/env python
"""Download yesterday's CAISO data automatically."""
from datetime import date, timedelta
from lib.iso.caiso import CAISOClient, Market
import logging

logging.basicConfig(
    level=logging.INFO,
    filename='daily_download.log',
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def download_yesterday():
    yesterday = date.today() - timedelta(days=1)
    
    client = CAISOClient()
    try:
        success = client.get_lmp(Market.DAM, yesterday, yesterday)
        if success:
            logging.info(f"✓ Downloaded data for {yesterday}")
        else:
            logging.error(f"✗ Failed to download data for {yesterday}")
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
    finally:
        client.cleanup()

if __name__ == '__main__':
    download_yesterday()
```

Run daily with cron (Linux/Mac):
```bash
# Edit crontab
crontab -e

# Add line to run daily at 2 AM
0 2 * * * cd /path/to/ISO-DART && /path/to/venv/bin/python daily_download.py
```

Or with Windows Task Scheduler:
```powershell
# Create scheduled task
schtasks /create /tn "ISO-DART Daily" /tr "C:\path\to\venv\Scripts\python.exe C:\path\to\daily_download.py" /sc daily /st 02:00
```

### Multi-Market Download

```python
from datetime import date
from lib.iso.caiso import CAISOClient, Market

client = CAISOClient()
start = date(2024, 1, 1)
end = date(2024, 1, 31)

# Download multiple markets
for market in [Market.DAM, Market.RTM, Market.HASP]:
    print(f"Downloading {market.value}...")
    client.get_lmp(market, start, end)

client.cleanup()
```

## Development

### Running Tests

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_caiso.py -v

# Run with coverage
pytest tests/ --cov=lib --cov-report=html

# View coverage report
open htmlcov/index.html  # Mac/Linux
start htmlcov/index.html  # Windows
```

### Code Quality

```bash
# Format code
black lib/ tests/

# Lint code
flake8 lib/ tests/

# Type checking
mypy lib/
```

### Project Structure

```
iso-dart/
├── lib/
│   ├── iso/
│   │   ├── caiso.py        # CAISO client (complete)
│   │   ├── miso.py         # MISO client (complete)
│   │   └── nyiso.py        # NYISO client (complete)
│   ├── weather/
│   │   └── client.py       # Weather/solar client
│   └── interactive.py      # Interactive CLI (complete coverage)
├── tests/
│   ├── test_caiso.py       # CAISO tests
│   ├── test_miso.py        # MISO tests
│   ├── test_nyiso.py       # NYISO tests
│   └── test_weather.py     # Weather tests
├── isodart.py              # Main entry point
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development dependencies
├── pyproject.toml          # Project configuration
└── README.md               # This file
```

## Troubleshooting

### Common Issues

#### 1. No data returned from API
```
Error: API returned no data
```
**Solution**: 
- Check that date range is valid (not in future)
- Verify data exists for that period on the ISO's website
- Check API is operational
- Try a smaller date range

#### 2. Import errors
```
ModuleNotFoundError: No module named 'lib'
```
**Solution**: Run from project root directory:
```bash
cd /path/to/ISO-DART
python isodart.py
```

#### 3. Weather station not found
```
No weather stations found in XX for date range
```
**Solution**: 
- Try a different date range
- Verify state code is valid (2-letter)
- Some rural areas may have limited station coverage

#### 4. NREL API rate limiting
```
Error 429: Too Many Requests
```
**Solution**: 
- NREL API has rate limits (1,000 requests/hour)
- Wait and retry
- Consider caching downloaded data

#### 5. SSL Certificate Errors
```
SSLError: Certificate verification failed
```
**Solution**:
```bash
pip install --upgrade certifi
```

### Debug Mode

Enable verbose logging:
```bash
python isodart.py --verbose
```

Check logs:
```bash
tail -f logs/isodart.log
```

Or in Python:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Tips

### Large Date Ranges

For requests spanning many days:

1. **Use smaller step sizes**: Adjust `step_size` parameter
2. **Run during off-peak hours**: Less API load
3. **Enable logging**: Monitor progress
4. **Use automation**: Schedule downloads overnight

```python
from datetime import date, timedelta
from lib.iso.caiso import CAISOClient, Market

client = CAISOClient()

# Download year of data in monthly chunks
start = date(2024, 1, 1)
for month in range(12):
    month_start = start + timedelta(days=30 * month)
    month_end = month_start + timedelta(days=30)
    
    print(f"Downloading {month_start} to {month_end}")
    client.get_lmp(Market.DAM, month_start, month_end)

client.cleanup()
```

### Parallel Downloads

For multiple ISOs or data types:

```python
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from lib.iso.caiso import CAISOClient, Market

def download_caiso_lmp(market, start, end):
    client = CAISOClient()
    result = client.get_lmp(market, start, end)
    client.cleanup()
    return result

# Download multiple markets in parallel
markets = [Market.DAM, Market.RTM, Market.HASP]
start = date(2024, 1, 1)
end = date(2024, 1, 31)

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(download_caiso_lmp, m, start, end)
        for m in markets
    ]
    results = [f.result() for f in futures]
```

## Migration from v1.x

If you're upgrading from v1.x, please see [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for detailed migration instructions.

### Quick Summary

**Key Changes:**
1. Entry point changed from `ISODART.py` to `isodart.py`
2. No more `exec()` - proper module imports
3. Configuration via config files instead of hardcoded values
4. Better error handling with exceptions instead of `sys.exit()`
5. Comprehensive logging instead of print statements

**Data Compatibility:** Your existing CSV files are fully compatible! ✅

## Contributing

We welcome contributions! Areas for improvement:

1. **Additional ISOs**: PJM, ERCOT, ISO-NE, SPP
2. **Data validation**: Automated quality checks
3. **Visualization**: Built-in plotting tools
4. **Database integration**: PostgreSQL/SQLite support
5. **Web interface**: Flask/Django dashboard
6. **Enhanced documentation**: More examples and tutorials

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Run test suite: `pytest tests/`
5. Format code: `black lib/ tests/`
6. Lint code: `flake8 lib/ tests/`
7. Submit pull request

## Citation

If you use ISO-DART in your research, please cite:

```bibtex
@software{isodart2024,
  title = {ISO-DART: Independent System Operator Data Automated Request Tool},
  author = {Sotorrio, Pedro and Edmunds, Thomas and Musselman, Amelia and Sun, Chih-Che},
  year = {2024},
  version = {2.0.0},
  publisher = {Lawrence Livermore National Laboratory},
  doi = {LLNL-CODE-815334},
  url = {https://github.com/LLNL/ISO-DART}
}
```

## License

MIT License - Copyright (c) 2025, Lawrence Livermore National Security, LLC

See [LICENSE](LICENSE) file for details.

## Support

- **Issues**: https://github.com/LLNL/ISO-DART/issues
- **Discussions**: https://github.com/LLNL/ISO-DART/discussions
- **Documentation**: See [QUICKSTART.md](QUICKSTART.md) for quick reference
- **Migration Guide**: See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for v1.x→v2.0 migration

## Acknowledgments

This work was produced under the auspices of the U.S. Department of Energy by Lawrence Livermore National Laboratory under Contract DE-AC52-07NA27344.

## Changelog

### v2.0.0 (2024-2025)
- ✅ Complete architecture redesign with modern Python practices
- ✅ Type hints, dataclasses, and enums throughout
- ✅ Command-line interface with argparse
- ✅ Comprehensive interactive mode with 100% method coverage
- ✅ Full support for all CAISO, MISO, and NYISO data types
- ✅ Enhanced error handling and logging
- ✅ Comprehensive test suite with pytest
- ✅ Updated dependencies (pandas 2.0+, requests 2.31+, meteostat 1.6+)
- ✅ Removed debugging code (no more `pdb.set_trace()`)
- ✅ Better documentation with examples
- ✅ Migration guide for v1.x users

### v1.1.0 (2020)
- Initial public release
- CAISO, MISO, NYISO support
- Weather data integration
- Basic CLI interface

## FAQ

**Q: Which Python version do I need?**
A: Python 3.10 or higher is required for v2.0.

**Q: Do I need to re-download all my data?**
A: No! Existing v1.x data files are compatible with v2.0.

**Q: Can I run v1.x and v2.0 side-by-side?**
A: Yes, in different directories or virtual environments.

**Q: How do I get historical data from several years ago?**
A: Just specify the date range. ISOs typically keep several years of historical data available.

**Q: Are there API rate limits?**
A: CAISO, MISO, and NYISO don't have strict rate limits, but be respectful. NREL (solar data) has 1,000 requests/hour.

**Q: Can I use this for commercial purposes?**
A: Yes, under the MIT license. See [LICENSE](LICENSE) for details.

**Q: How do I report a bug?**
A: Please create an issue on GitHub with details about the error and how to reproduce it.

**Q: Can I request support for additional ISOs?**
A: Yes! Please create a feature request issue on GitHub.

---

**Made with ❤️ by Lawrence Livermore National Laboratory**
