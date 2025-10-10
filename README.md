# ISO-DART v2.0
## Independent System Operator Data Automated Request Tool

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Major revamp of the original ISO-DART tool with modernized architecture, improved error handling, and enhanced user experience.**

## What's New in v2.0

### 🚀 Major Improvements
- **Modern Python practices**: Type hints, dataclasses, enums, and proper error handling
- **Command-line interface**: Use arguments or interactive mode
- **Robust API handling**: Automatic retries, better error messages, connection pooling
- **Enhanced logging**: Track operations and debug issues easily
- **Testing framework**: Comprehensive unit and integration tests
- **Removed debug code**: No more `pdb.set_trace()` blocking execution
- **Updated dependencies**: Compatible with latest pandas, requests, and meteostat

### 📊 Supported Data Sources

#### Independent System Operators (ISOs)
- **CAISO** (California ISO) - ✅ Fully updated
  - Locational Marginal Prices (LMP)
  - Load forecasts (DAM, RTM, HASP, RTPD)
  - Ancillary services
  - Renewable generation
  - System demand
  
- **MISO** (Midcontinent ISO) - 🔄 Legacy support (update planned)
- **NYISO** (New York ISO) - 🔄 Legacy support (update planned)

#### Weather & Solar Data
- **Meteostat**: Historical weather data for any US location
- **NSRDB** (National Solar Radiation Database): Solar irradiance data

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

## Usage

### Interactive Mode (Recommended for New Users)

Simply run:
```bash
python isodart.py
```

Follow the prompts to:
1. Select ISO or weather data
2. Choose specific data type
3. Enter date range
4. Select location (for weather data)

### Command-Line Mode

For automation and scripting:

```bash
# Download CAISO Day-Ahead LMP data
python isodart.py --iso caiso --data-type lmp --market dam \
  --start 2024-01-01 --duration 7

# Download CAISO load forecast
python isodart.py --iso caiso --data-type load --market rtm \
  --start 2024-01-01 --duration 30

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
--config PATH                Path to configuration file
```

## Examples

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

#### Download Multiple Data Types (Interactive Mode)
```bash
python isodart.py --interactive
# Then follow prompts to select multiple datasets
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

### Python API Usage

For integration into your own scripts:

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

# Clean up temporary files
client.cleanup()
```

#### Weather API
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

### Output File Format

#### CAISO Files
Format: `{start_date}_to_{end_date}_{query_name}_{data_item}.csv`

Example: `20240101_to_20240131_PRC_LMP_TH_NP15_GEN-APND.csv`

Columns vary by data type but typically include:
- `OPR_DATE`: Operating date
- `INTERVAL_NUM`: Time interval within the day
- `DATA_ITEM`: Specific location/node
- `VALUE`: Price, load, or other metric
- `MW`: Power values (for load data)

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
- And more (depending on station)

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

weather:
  data_dir: data/weather
  solar_dir: data/solar

logging:
  level: INFO
  file: logs/isodart.log
```

Use with: `python isodart.py --config config.yaml`

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
pytest tests/ --cov=iso --cov-report=html
```

### Code Quality

```bash
# Format code
black iso/ tests/

# Lint code
flake8 iso/ tests/

# Type checking
mypy iso/
```

### Project Structure

```
iso-dart/
├── lib/
│   ├── iso/
│   │   ├── caiso.py        # CAISO client
│   │   ├── miso.py         # MISO client (legacy)
│   │   └── nyiso.py        # NYISO client (legacy)
│   ├── weather/
│   │   └── client.py       # Weather/solar client
│   └── interactive.py      # Interactive CLI mode
├── tests/
│   ├── test_caiso.py       # CAISO tests
│   └── test_weather.py     # Weather tests
├── isodart.py              # Main entry point
├── requirements.txt        # Production dependencies
└── requirements-dev.txt    # Development dependencies
```

## Migration from v1.x

### Key Changes

1. **Entry Point**: Use `isodart.py` instead of `ISODART.py`
2. **No More exec()**: Scripts are now properly imported as modules
3. **Configuration**: Move from hardcoded values to config files
4. **Error Handling**: Descriptive errors instead of sys.exit()
5. **Logging**: Use logging instead of print statements

### Breaking Changes

- Directory structure changed (automatic migration)
- API interface changed (see Python API examples above)
- Some query names updated to match current CAISO OASIS API

### Migration Script

```python
# migrate_v1_to_v2.py
from pathlib import Path
import shutil

# Backup old data
old_data = Path('data')
if old_data.exists():
    backup = Path('data_v1_backup')
    shutil.copytree(old_data, backup)
    print(f"Backed up v1 data to {backup}")

# Data files are compatible, just need directory structure
print("Run: python isodart.py to set up v2 structure")
```

## Troubleshooting

### Common Issues

#### 1. No data returned from API
```
Error: API returned no data
```
**Solution**: Check that:
- Date range is valid (not in future)
- Data exists for that period
- CAISO OASIS API is operational

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
- Check state code is valid (2-letter)
- Some rural states may have limited stations

#### 4. NREL API rate limiting
```
Error 429: Too Many Requests
```
**Solution**: NREL API has rate limits:
- 1,000 requests per hour
- Wait and retry
- Consider caching downloaded data

### Debug Mode

Enable verbose logging:
```bash
python isodart.py --verbose
```

Check logs:
```bash
tail -f logs/isodart.log
```

## Performance Tips

### Large Date Ranges

For requests spanning many days:

1. **Use smaller step sizes**: Default is 1 day
2. **Run during off-peak hours**: Less API load
3. **Enable logging**: Monitor progress
4. **Use automation**: Schedule downloads overnight

```python
# Example: Download year of data in batches
from datetime import date, timedelta
from lib.iso.caiso import CAISOClient, Market

client = CAISOClient()

# Download in monthly chunks
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

def download_caiso_lmp(market, start, end):
    from lib.iso.caiso import CAISOClient
    client = CAISOClient()
    return client.get_lmp(market, start, end)

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

## Contributing

We welcome contributions! Areas for improvement:

1. **Additional ISOs**: PJM, ERCOT, ISO-NE
2. **Data validation**: Automated quality checks
3. **Visualization**: Built-in plotting tools
4. **Database integration**: PostgreSQL/SQLite support
5. **Web interface**: Flask/Django dashboard

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Run test suite: `pytest tests/`
5. Format code: `black lib/ tests/`
6. Submit pull request

## Citation

If you use ISO-DART in your research, please cite:

```bibtex
@software{isodart2024,
  title = {ISO-DART: Independent System Operator Data Automated Request Tool},
  author = {Sotorrio, Pedro and Edmunds, Thomas and Musselman, Amelia and Sun, Chih-Che},
  year = {2024},
  version = {2.0.0},
  publisher = {Lawrence Livermore National Laboratory},
  doi = {LLNL-CODE-815334}
}
```

## License

MIT License - Copyright (c) 2020, Lawrence Livermore National Security, LLC

See [LICENSE](LICENSE) file for details.

## Support

- **Issues**: https://github.com/LLNL/ISO-DART/issues
- **Discussions**: https://github.com/LLNL/ISO-DART/discussions
- **Email**: Contact LLNL Industrial Partnerships Office

## Acknowledgments

This work was produced under the auspices of the U.S. Department of Energy by Lawrence Livermore National Laboratory under Contract DE-AC52-07NA27344.

## Changelog

### v2.0.0 (2024)
- Complete architecture redesign
- Modern Python practices (type hints, dataclasses)
- Command-line interface with argparse
- Comprehensive test suite
- Updated all dependencies
- Removed debugging code
- Enhanced error handling
- Improved logging
- Better documentation

### v1.1.0 (2020)
- Initial public release
- CAISO, MISO, NYISO support
- Weather data integration
- Basic CLI interface