# ISO-DART v2.0 Quick Start Guide

Get up and running with ISO-DART in 5 minutes!

## 🚀 Installation (2 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/LLNL/ISO-DART.git
cd ISO-DART

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify installation
python isodart.py --help
```

## 📊 Your First Download (3 minutes)

### Option 1: Interactive Mode (Easiest)

```bash
python isodart.py
```

Then follow the prompts:
1. Choose "1" for ISO Data
2. Choose "1" for CAISO
3. Choose "1" for Pricing Data
4. Choose "1" for LMP
5. Choose "1" for Day-Ahead Market
6. Enter date range (e.g., today minus 7 days)

**Done!** Your data is in `data/CAISO/`

### Option 2: Command Line (Fastest)

```bash
# Download last week's Day-Ahead LMP data from CAISO
python isodart.py --iso caiso --data-type lmp --market dam \
  --start 2024-01-01 --duration 7
```

**Done!** Check `data/CAISO/` for your CSV files.

## 📈 Using Your Data

### Load and Visualize

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

### Basic Analysis

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

## 🌤️ Weather Data

```bash
# Download weather data for California
python isodart.py --data-type weather --state CA \
  --start 2024-01-01 --duration 30
```

Then select your weather station from the list.

### Analyze Weather Data

```python
import pandas as pd
import matplotlib.pyplot as plt

# Load weather data
df = pd.read_csv('data/weather/2024-01-01_to_2024-01-31_San_Francisco_CA.csv',
                 index_col='time', parse_dates=True)

# Plot temperature
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

## 🔄 Common Workflows

### 1. Download Multiple Markets

```python
from datetime import date
from lib.iso.caiso import CAISOClient, Market

client = CAISOClient()

start = date(2024, 1, 1)
end = date(2024, 1, 31)

# Download multiple markets
for market in [Market.DAM, Market.RTM]:
    print(f"Downloading {market.value}...")
    client.get_lmp(market, start, end)

print("All downloads complete!")
client.cleanup()
```

### 2. Automated Daily Download

Save as `daily_download.py`:

```python
#!/usr/bin/env python
"""Download yesterday's CAISO data automatically."""
from datetime import date, timedelta
from lib.iso.caiso import CAISOClient, Market
import logging

logging.basicConfig(level=logging.INFO)

def download_yesterday():
    yesterday = date.today() - timedelta(days=1)
    
    client = CAISOClient()
    success = client.get_lmp(Market.DAM, yesterday, yesterday)
    
    if success:
        print(f"✓ Downloaded data for {yesterday}")
    else:
        print(f"✗ Failed to download data for {yesterday}")
    
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

### 3. Compare Multiple Locations

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
    plt.plot(df['OPR_DT'], df['VALUE'], label=loc, alpha=0.7)

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

## 🔍 Troubleshooting

### Issue: "ModuleNotFoundError"
```bash
# Make sure you're in the ISO-DART directory
cd /path/to/ISO-DART

# And virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

### Issue: "No data returned"
- Check your date range (not in future)
- Verify CAISO OASIS is online
- Try a smaller date range
- Use `--verbose` flag for details

### Issue: Slow downloads
- This is normal for large date ranges
- CAISO API can be slow during peak hours
- Consider downloading during off-hours
- Use smaller `step_size` values

## 📚 Next Steps

1. **Read the full README.md** for comprehensive documentation
2. **Check examples/** folder for Jupyter notebooks
3. **Run tests** to verify your installation:
   ```bash
   pip install pytest
   pytest tests/ -v
   ```
4. **Join the discussion** on GitHub for questions

## 💡 Pro Tips

1. **Always activate your virtual environment** before running
2. **Use `--verbose`** when debugging
3. **Check logs/** folder for detailed operation logs
4. **Clean up** with `client.cleanup()` to save disk space
5. **Backup your data** regularly from `data/` directory

## 🎯 Useful Commands

```bash
# Check what data you've downloaded
ls -lh data/CAISO/
ls -lh data/weather/

# See logs
tail -f logs/isodart.log

# Clean up old raw data
rm -rf raw_data/

# Get help
python isodart.py --help

# Update dependencies
pip install --upgrade -r requirements.txt
```

## 🤝 Need Help?

- **GitHub Issues**: https://github.com/LLNL/ISO-DART/issues
- **Email**: Contact LLNL support
- **Documentation**: Full README.md in repository

## ⚡ Power User Shortcut

Create an alias in your shell:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias isodart='cd /path/to/ISO-DART && source venv/bin/activate && python isodart.py'

# Then just run:
isodart --iso caiso --data-type lmp --market dam --start 2024-01-01 --duration 7
```

Happy data downloading! 🚀
