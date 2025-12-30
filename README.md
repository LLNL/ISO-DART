# ISO-DART v2.0

<div align="center">

**Independent System Operator Data Automated Request Tool**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![codecov](https://codecov.io/github/LLNL/ISO-DART/branch/dev/graph/badge.svg)](https://codecov.io/github/LLNL/ISO-DART)

*A modern Python toolkit for downloading and analyzing electricity market data from US Independent System Operators*

[Quick Start](#-quick-start) • [Documentation](http://software.llnl.gov/ISO-DART/) • [Examples](#-examples) • [Contributing](#-contributing)

</div>

---

## 🌟 What is ISO-DART?

ISO-DART simplifies access to electricity market data across the United States. Whether you're a researcher, energy analyst, or data scientist, ISO-DART provides a unified interface to download pricing, load, generation, and weather data from multiple ISOs.

### Key Features

- 🔌 **7 ISO Coverage**: CAISO, MISO, NYISO, SPP, BPA, PJM, ISO-NE
- 🌤️ **Weather Integration**: Historical weather and solar radiation data
- 🚀 **Modern Python**: Type hints, async support, comprehensive error handling
- 🎯 **User-Friendly**: Interactive CLI or programmatic API
- 📊 **Analysis-Ready**: CSV output compatible with pandas, Excel, and R
- ⚡ **Performance**: Automatic retry logic, connection pooling, rate limiting

## 📊 Supported Data Types

<details>
<summary><b>CAISO (California)</b> - Click to expand</summary>

- **Pricing**: LMP (DAM/HASP/RTM/RTPD), Scheduling Point Tie Prices, AS Clearing Prices
- **Load**: System load forecasts (DAM/RTM/2DA/7DA/RTPD Advisory)
- **Generation**: Wind & Solar Summary, EIM Transfer, Flexible Ramping
- **Ancillary Services**: Requirements, Awards, Operating Reserves
- **Market Data**: MPM Status, Fuel Prices, GHG Allowance Prices, Constraint Shadow Prices

</details>

<details>
<summary><b>MISO (Midcontinent)</b> - Click to expand</summary>

- **Pricing**: LMP (DA/RT ExAnte/ExPost), MCP (ASM DA/RT)
- **Load**: Demand (DA/RT Forecast/Actual), Load Forecasts (MTLF)
- **Generation**: Fuel Mix, Cleared Generation (DA/RT), Fuel Type
- **Interchange**: Net Scheduled/Actual Interchange
- **Constraints**: Binding Constraints, Outage Forecasts

</details>

<details>
<summary><b>NYISO (New York)</b> - Click to expand</summary>

- **Pricing**: LBMP (Zonal/Generator, DAM/RTM), AS Prices
- **Load**: ISO Forecast, Zonal Bid Load, Weather Forecast, Actual Load
- **Generation**: Fuel Mix, Interface Flows, Wind Generation, BTM Solar
- **Market Data**: Bid Data (Generator/Load/Transaction), Outages, Constraints

</details>

<details>
<summary><b>SPP (Southwest)</b> - Click to expand</summary>

- **Pricing**: LMP (DA/RTBM by Settlement Location/Bus), MCP
- **Reserves**: Operating Reserves (RTBM)
- **Forecasts**: Load (STLF/MTLF), Resource/Wind (STRF/MTRF)
- **Constraints**: Binding Constraints (DA/RTBM), Fuel On Margin
- **Clearing**: Market Clearing, Virtual Clearing

</details>

<details>
<summary><b>BPA (Bonneville)</b> - Click to expand</summary>

- **Load & Generation**: Wind Generation, Total Load (5-min resolution)
- **Reserves**: Operating Reserves Deployed (Regulation Up/Down, Contingency)
- **Historical Data**: Full calendar year datasets (2000-present)

</details>

<details>
<summary><b>PJM</b> - Click to expand</summary>

- **Pricing**: LMP (DA Hourly, RT 5-min, RT Hourly)
- **Load**: Forecasts (5-min, Historical, 7-day), Hourly Load (Estimated/Metered/Prelim)
- **Generation**: Solar, Wind
- **Ancillary Services**: Hourly/5-min LMPs, Reserve Market Results
- **Grid Data**: Outages by Type, Transfer Limits & Flows

</details>

<details>
<summary><b>ISO-NE (New England)</b> - Click to expand</summary>

- **Pricing**: Hourly LMP (DA/RT), 5-Minute RT LMP
- **Ancillary Services**: Regulation Clearing Prices, Operating Reserves
- **Load**: 5-Minute System Demand, DA Hourly Demand

</details>

<details>
<summary><b>Weather & Solar</b> - Click to expand</summary>

- **Meteostat**: Temperature, humidity, wind, precipitation (hourly)
- **NSRDB**: Solar irradiance (GHI, DHI, DNI) from NREL

</details>

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/LLNL/ISO-DART.git
cd ISO-DART

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Your First Download

**Interactive Mode** (easiest):
```bash
python isodart.py
```

**Command Line** (fastest):
```bash
# Download last week's CAISO Day-Ahead LMP
python isodart.py --iso caiso --data-type lmp --market dam \
  --start 2024-01-01 --duration 7
```

**Python API** (most flexible):
```python
from datetime import date
from lib.iso.caiso import CAISOClient, Market

client = CAISOClient()
client.get_lmp(Market.DAM, date(2024, 1, 1), date(2024, 1, 7))
client.cleanup()
```

### 5-Minute Tutorial

1. **Download data**:
```bash
python isodart.py --iso caiso --data-type lmp --market dam \
  --start 2024-01-01 --duration 7
```

2. **Analyze in Python**:
```python
import pandas as pd
import matplotlib.pyplot as plt

# Load data
df = pd.read_csv('data/CAISO/20240101_to_20240107_PRC_LMP_TH_NP15_GEN-APND.csv')

# Quick statistics
print(df['VALUE'].describe())

# Plot prices
df['OPR_DT'] = pd.to_datetime(df['OPR_DATE'])
plt.figure(figsize=(12, 6))
plt.plot(df['OPR_DT'], df['VALUE'])
plt.xlabel('Date')
plt.ylabel('Price ($/MWh)')
plt.title('Day-Ahead LMP - NP15')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('lmp_analysis.png')
```

3. **Done!** You now have data and a visualization.

## 📖 Documentation

### Essential Guides

- **[Quick Start Guide](docs/source/getting-started/QUICKSTART.md)** - Get running in 5 minutes
- **[Migration Guide](docs/source/getting-started/MIGRATION_GUIDE.md)** - Upgrading from v1.x
- **[API Reference](docs/api/)** - Complete function documentation
- **[Examples Gallery](examples/)** - Jupyter notebooks and scripts

### Common Use Cases

#### Automated Daily Downloads

```python
# daily_download.py
from datetime import date, timedelta
from lib.iso.caiso import CAISOClient, Market

def download_yesterday():
    yesterday = date.today() - timedelta(days=1)
    client = CAISOClient()
    
    try:
        success = client.get_lmp(Market.DAM, yesterday, yesterday)
        if success:
            print(f"✓ Downloaded {yesterday}")
    finally:
        client.cleanup()

if __name__ == '__main__':
    download_yesterday()
```

Schedule with cron:
```bash
0 2 * * * cd /path/to/ISO-DART && /path/to/venv/bin/python daily_download.py
```

#### Multi-ISO Comparison

```python
from datetime import date
from lib.iso.caiso import CAISOClient, Market as CAISOMarket
from lib.iso.miso import MISOClient, MISOConfig
from lib.iso.nyiso import NYISOClient, NYISOMarket

start = date(2024, 1, 1)

# CAISO
caiso = CAISOClient()
caiso.get_lmp(CAISOMarket.DAM, start, start)

# MISO
miso_config = MISOConfig.from_ini_file()
miso = MISOClient(miso_config)
miso.get_lmp("da_exante", start, 1)

# NYISO
nyiso = NYISOClient()
nyiso.get_lbmp(NYISOMarket.DAM, "zonal", start, 1)

print("✓ Downloaded data from all three ISOs")
```

#### Weather-Correlated Analysis

```python
import pandas as pd
import matplotlib.pyplot as plt

# Load LMP data
lmp = pd.read_csv('data/CAISO/20240101_to_20240131_PRC_LMP_TH_NP15_GEN-APND.csv')
lmp['datetime'] = pd.to_datetime(lmp['OPR_DATE'])

# Load weather data
weather = pd.read_csv('data/weather/2024-01-01_to_2024-01-31_San_Francisco_CA.csv',
                      index_col='time', parse_dates=True)

# Resample to daily averages
lmp_daily = lmp.groupby(lmp['datetime'].dt.date)['VALUE'].mean()
temp_daily = weather['temperature'].resample('D').mean()

# Plot correlation
fig, ax1 = plt.subplots(figsize=(14, 6))
ax2 = ax1.twinx()

ax1.plot(lmp_daily.index, lmp_daily.values, 'b-', label='LMP')
ax2.plot(temp_daily.index, temp_daily.values, 'r-', label='Temperature')

ax1.set_xlabel('Date')
ax1.set_ylabel('LMP ($/MWh)', color='b')
ax2.set_ylabel('Temperature (°F)', color='r')

plt.title('Electricity Prices vs. Temperature')
plt.tight_layout()
plt.savefig('price_temp_correlation.png')
```

## 🔧 Configuration

### API Keys (Optional)

Some ISOs and data sources require API keys:

**MISO & PJM**: Create `user_config.ini`:
```ini
[miso]
pricing_api_key = your-miso-pricing-key
lgi_api_key = your-miso-lgi-key

[pjm]
api_key = your-pjm-key
```

Get keys from:
- MISO: https://data-exchange.misoenergy.org/
- PJM: https://dataminer2.pjm.com/

**NSRDB (Solar Data)**: Get free API key at https://developer.nrel.gov/signup/

**ISO-NE**: Requires ISO Express credentials
```ini
[isone]
username = your-username
password = your-password
```

Or set environment variables:
```bash
export ISONE_USERNAME="your-username"
export ISONE_PASSWORD="your-password"
```

### Advanced Configuration

Create `config.yaml`:
```yaml
caiso:
  max_retries: 5
  timeout: 60
  step_size: 1

miso:
  rate_limit_delay: 0.8

logging:
  level: DEBUG
  file: logs/isodart.log
```

Use: `python isodart.py --config config.yaml`

## 💻 Development

### Running Tests

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=lib --cov-report=html

# Run specific tests
pytest tests/test_caiso.py -v
```

### Code Quality

```bash
# Format code
black lib/ tests/

# Lint
flake8 lib/ tests/

# Type check
mypy lib/
```

### Project Structure

```
ISO-DART/
├── isodart.py              # Main entry point
├── lib/
│   ├── iso/                # ISO client modules
│   │   ├── caiso.py
│   │   ├── miso.py
│   │   ├── nyiso.py
│   │   ├── spp.py
│   │   ├── bpa.py
│   │   ├── pjm.py
│   │   └── isone.py
│   ├── weather/            # Weather client
│   │   └── client.py
│   └── interactive.py      # Interactive mode
├── tests/                  # Test suite
├── docs/                   # Documentation
├── examples/               # Example scripts & notebooks
└── data/                   # Downloaded data (created automatically)
```

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### Ways to Contribute

- 🐛 **Report bugs** - Create an issue with details
- 💡 **Suggest features** - We'd love to hear your ideas
- 📝 **Improve docs** - Fix typos, add examples
- 🔧 **Submit code** - Fix bugs or add features
- ⭐ **Star the repo** - Show your support!

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Add tests for new functionality
5. Run tests: `pytest tests/`
6. Format code: `black lib/ tests/`
7. Submit a pull request

### Adding a New ISO

To add support for a new ISO:

1. Create `lib/iso/new_iso.py` following the pattern of existing clients
2. Add configuration dataclass
3. Implement download methods
4. Add tests in `tests/test_new_iso.py`
5. Update `lib/interactive.py` for CLI support
6. Document in README.md

See [Contributing Guide](CONTRIBUTING.md) for details.

## 📊 Data Formats

### CSV Output

All data is saved as CSV files with ISO-specific naming:

**CAISO**:
```
{start_date}_to_{end_date}_{query_name}_{data_item}.csv
```
Example: `20240101_to_20240131_PRC_LMP_TH_NP15_GEN-APND.csv`

**MISO**:
```
miso_{data_type}_{date}.csv
```
Example: `miso_da_exante_lmp_2024-01-01.csv`

**NYISO**:
```
{start_date}_to_{end_date}_{dataid}_{aggregation}.csv
```
Example: `20240101_to_20240131_damlbmp_zone.csv`

### Data Compatibility

- ✅ Pandas: `pd.read_csv()`
- ✅ Excel: Direct import
- ✅ R: `read.csv()`
- ✅ Power BI / Tableau: CSV connector
- ✅ SQL databases: `COPY FROM` or bulk insert

## 🚨 Troubleshooting

<details>
<summary><b>No data returned from API</b></summary>

**Symptoms**: Empty CSV files or "No data" errors

**Solutions**:
- Verify date range is not in the future
- Check if data exists for that period on ISO website
- Try a smaller date range
- Use `--verbose` flag for detailed logs
- Check `logs/isodart.log` for API errors

</details>

<details>
<summary><b>Import errors / ModuleNotFoundError</b></summary>

**Symptoms**: `ModuleNotFoundError: No module named 'lib'`

**Solutions**:
- Ensure you're running from the ISO-DART directory
- Activate virtual environment: `source venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

</details>

<details>
<summary><b>API authentication failures</b></summary>

**Symptoms**: 401 Unauthorized, "Check API key" messages

**Solutions**:
- Verify API key is correct in `user_config.ini`
- Check key hasn't expired
- For MISO/PJM: Ensure you have the right API product subscription
- For ISO-NE: Verify credentials at https://webservices.iso-ne.com/

</details>

<details>
<summary><b>Slow downloads</b></summary>

**Symptoms**: Downloads take a long time

**Solutions**:
- This is normal for large date ranges (ISO APIs can be slow)
- Use smaller `step_size` values
- Download during off-peak hours (early morning)
- For SPP: FTP is naturally slower than REST APIs

</details>

<details>
<summary><b>SSL certificate errors</b></summary>

**Symptoms**: `SSLError: Certificate verification failed`

**Solutions**:
```bash
pip install --upgrade certifi requests
```

</details>

## 📄 License & Citation

### License

MIT License - Copyright (c) 2025, Lawrence Livermore National Security, LLC

See [LICENSE](LICENSE) file for full terms.

### Citation

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

### Acknowledgments

This work was produced under the auspices of the U.S. Department of Energy by Lawrence Livermore National Laboratory under Contract DE-AC52-07NA27344.

## 🔗 Resources

### Official ISO Websites

- [CAISO OASIS](http://oasis.caiso.com/)
- [MISO Data Exchange](https://data-exchange.misoenergy.org/)
- [NYISO Market Data](http://mis.nyiso.com/)
- [SPP Marketplace](https://marketplace.spp.org/)
- [BPA Operations](https://transmission.bpa.gov/)
- [PJM Data Miner](https://dataminer2.pjm.com/)
- [ISO-NE Web Services](https://webservices.iso-ne.com/)

### Related Projects

- [GridStatus](https://github.com/kmax12/gridstatus) - Real-time grid data
- [PyISO](https://github.com/WattTime/pyiso) - Alternative ISO library
- [Open Energy Dashboard](https://openenergydashboard.org/) - Energy visualization

### Getting Help

- 📖 **Documentation**: Check [docs/](docs/) directory
- 💬 **Discussions**: [GitHub Discussions](https://github.com/LLNL/ISO-DART/discussions)
- 🐛 **Issues**: [Report bugs](https://github.com/LLNL/ISO-DART/issues)
- 📧 **Email**: Contact LLNL support

## 🎯 Roadmap

### v2.1 (Planned)

- [ ] ERCOT support
- [ ] ISO-NE full coverage
- [ ] Async/concurrent downloads
- [ ] Data validation & quality checks
- [ ] Built-in visualization tools
- [ ] PostgreSQL/SQLite export
- [ ] Web dashboard (Flask/FastAPI)

### Community Requests

- Database integration (PostgreSQL, InfluxDB)
- Parquet output format
- Real-time data streaming
- Machine learning integration
- Docker containerization

[Vote on features →](https://github.com/LLNL/ISO-DART/discussions)

## ⭐ Show Your Support

If ISO-DART helps your work, please:
- ⭐ Star this repository
- 📢 Share with colleagues
- 🐛 Report bugs you find
- 💡 Suggest improvements
- 📝 Contribute documentation or code

---

<div align="center">

**Made with ❤️ by Lawrence Livermore National Laboratory**

[Report Bug](https://github.com/LLNL/ISO-DART/issues) · [Request Feature](https://github.com/LLNL/ISO-DART/discussions) · [Documentation](docs/)

</div>
