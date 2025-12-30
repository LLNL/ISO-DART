# ISO-DART Migration Guide: v1.1 → v2.0

## Overview

This guide helps you migrate from ISO-DART v1.1 to v2.0, highlighting breaking changes and new features.

## 🎯 Quick Summary

| Aspect | v1.1 | v2.0 |
|--------|------|------|
| Python Version | 3.8+ | 3.10+ |
| Entry Point | `ISODART.py` | `isodart.py` |
| Architecture | Scripts with `exec()` | Modern modules |
| CLI | Basic prompts | argparse + interactive |
| Error Handling | `sys.exit()` | Exceptions + logging |
| Testing | None | Comprehensive pytest suite |
| Type Safety | None | Type hints throughout |
| Documentation | Basic README | Full docs + examples |

## 🚀 Migration Steps

### 1. Backup Your Data

```bash
# Backup existing data
cp -r data data_v1_backup
cp -r raw_data raw_data_v1_backup 2>/dev/null || true

# Backup any custom scripts
cp mainCAISO.py mainCAISO_v1.py.bak 2>/dev/null || true
```

### 2. Update Python Version

```bash
# Check your Python version
python --version

# If < 3.10, install Python 3.10 or higher
# Ubuntu/Debian:
sudo apt update
sudo apt install python3.10 python3.10-venv

# macOS (using Homebrew):
brew install python@3.10

# Windows: Download from python.org
```

### 3. Install v2.0

```bash
# Pull latest changes
git fetch origin
git checkout v2.0  # or main branch

# Create new virtual environment
python3.10 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Verify Installation

```bash
# Test the installation
python isodart.py --help

# Run a quick test
python isodart.py --iso caiso --data-type lmp --market dam \
  --start 2024-01-01 --duration 1
```

## 🔄 Code Migration

### Old Way (v1.1)

```python
# mainCAISO.py - Run with exec()
exec(open("mainCAISO.py").read())

# Direct date input with loops
ind = 1
while ind == 1:
    month = int(input('Month: '))
    day = int(input('Day: '))
    year = int(input('Year (4-digit format): '))
    try:
        datetime.datetime(year=year, month=month, day=day)
        ind = 0
    except:
        print('\nWARNING: The Date Does NOT Exist. Please Try Again!!')

# Query with hardcoded parameters
DAM_LMP().get_csv(start, end, step_size=step_size)
```

### New Way (v2.0)

```python
# isodart.py - Proper module imports
from datetime import date
from lib.iso.caiso import CAISOClient, Market

# Clean date validation
start_date = date(2024, 1, 1)
end_date = date(2024, 1, 31)

# Type-safe client usage
client = CAISOClient()
success = client.get_lmp(
    market=Market.DAM,
    start_date=start_date,
    end_date=end_date
)

if success:
    print("Download successful!")
else:
    print("Download failed, check logs")

client.cleanup()
```

## 📋 Breaking Changes

### 1. File Structure

**Old:**
```
iso-dart/
├── ISODART.py
├── mainCAISO.py
├── mainMISO.py
├── mainNYISO.py
├── mainWeather.py
└── lib/framework/...
```

**New:**
```
iso-dart/
├── isodart.py              # Main entry point
├── lib/
│   ├── iso/
│   │   ├── caiso.py       # CAISO module
│   │   ├── miso.py        # MISO module
│   │   └── nyiso.py       # NYISO module
│   ├── weather/
│   │   └── client.py      # Weather module
│   └── interactive.py     # Interactive mode
└── tests/                  # Test suite
```

**Migration:** No action needed - v2.0 creates new structure automatically.

### 2. Import Changes

**Old:**

```python
from lib.iso.CAISO.query import *
from lib.iso.CAISO.tool_utils import *
```

**New:**
```python
from lib.iso.caiso import CAISOClient, Market, ReportVersion
```

### 3. Query Class Changes

**Old:**
```python
# Direct class instantiation
lmp = DAM_LMP()
lmp.get_csv(start, end, step_size=1)

# Class inheritance based on market
class DAM_LMP(LMP):
    name = 'PRC_LMP'
    market = 'DAM'
```

**New:**
```python
# Client-based approach
client = CAISOClient()
client.get_lmp(Market.DAM, start_date, end_date)

# Enum-based markets
market = Market.DAM  # Type-safe enum
```

### 4. Error Handling

**Old:**
```python
if errDetector == 1:
    sys.exit()  # Abrupt termination
```

**New:**
```python
try:
    success = client.get_lmp(...)
    if not success:
        logger.error("Download failed")
        # Handle error gracefully
except Exception as e:
    logger.error(f"Error: {e}", exc_info=True)
    # Continue or retry
```

### 5. Configuration

**Old:**
```python
# Hardcoded in files
URL = 'http://oasis.caiso.com/oasisapi/SingleZip'
DATA_DIR = os.path.join(os.getcwd(), 'data')
```

**New:**
```python
# Configurable via dataclass
from lib.iso.caiso import CAISOConfig

config = CAISOConfig(
    base_url='http://oasis.caiso.com/oasisapi/SingleZip',
    data_dir=Path('custom/data/dir'),
    max_retries=5
)
client = CAISOClient(config=config)
```

## 🆕 New Features

### 1. Command-Line Interface

```bash
# v2.0 supports command-line arguments
python isodart.py --iso caiso --data-type lmp --market dam \
  --start 2024-01-01 --duration 30 --verbose

# Still supports interactive mode
python isodart.py --interactive
```

### 2. Logging

```python
import logging

# Enable verbose logging
logging.basicConfig(level=logging.DEBUG)

# Or check logs directory
tail -f logs/isodart.log
```

### 3. Type Safety

```python
from datetime import date
from lib.iso.caiso import CAISOClient, Market

# IDE autocomplete and type checking work!
client: CAISOClient = CAISOClient()
market: Market = Market.DAM
start: date = date(2024, 1, 1)
```

### 4. Testing

```bash
# Run test suite
pytest tests/ -v

# Test specific functionality
pytest tests/test_caiso.py::TestCAISOClient::test_get_lmp -v

# Check coverage
pytest tests/ --cov=iso --cov-report=html
```

### 5. Better Error Messages

**Old:**
```
WARNING!! ERROR CODE:404	Data not found
Program End!! Please Try Again.
```

**New:**
```
ERROR - API Error 404: Data not found for date range 2024-01-01 to 2024-01-31
INFO - Retrying request (attempt 2/3)...
INFO - Consider checking CAISO OASIS website for data availability
```

## 🔧 Custom Script Migration

### Example: Automated Daily Download

**Old Script (v1.1):**
```python
# daily_download_v1.py
import sys
sys.path.append('/path/to/iso-dart')
exec(open("mainCAISO.py").read())
# Then manually input values...
```

**New Script (v2.0):**
```python
# daily_download_v2.py
from datetime import date, timedelta
from lib.iso.caiso import CAISOClient, Market
import logging

logging.basicConfig(
    level=logging.INFO,
    filename='daily_download.log'
)

def download_yesterday():
    """Download yesterday's CAISO DAM LMP data."""
    yesterday = date.today() - timedelta(days=1)
    
    client = CAISOClient()
    try:
        success = client.get_lmp(Market.DAM, yesterday, yesterday)
        if success:
            logging.info(f"✓ Downloaded {yesterday}")
        else:
            logging.error(f"✗ Failed {yesterday}")
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
    finally:
        client.cleanup()

if __name__ == '__main__':
    download_yesterday()
```

### Example: Multi-Market Download

**Old Script:**
```python
# Complex nested if/else structure
if market == 1:
    DAM_LMP().get_csv(start, end, step_size=step_size)
elif market == 2:
    HASP_LMP().get_csv(start, end, step_size=step_size)
# ... many more lines
```

**New Script:**
```python
from datetime import date
from lib.iso.caiso import CAISOClient, Market

client = CAISOClient()
start = date(2024, 1, 1)
end = date(2024, 1, 31)

# Clean iteration
for market in [Market.DAM, Market.HASP, Market.RTM]:
    print(f"Downloading {market.value}...")
    client.get_lmp(market, start, end)

client.cleanup()
```

## 📊 Data Compatibility

Good news: **Your existing data files are compatible!**

- CSV format unchanged
- Column names unchanged
- Directory structure can coexist

```bash
# Old and new data can live together
data/
├── CAISO/
│   ├── 20240101_to_20240131_PRC_LMP_*.csv  # Old format (still works)
│   └── 20240201_to_20240228_PRC_LMP_*.csv  # New format (same structure)
```

## ⚠️ Known Issues & Solutions

### Issue 1: `pdb.set_trace()` removed

**Symptom:** Old scripts that relied on debugging breakpoints won't pause
**Solution:** Use proper logging or IDE debugger

### Issue 2: `exec(open().read())` not supported

**Symptom:** Old script execution pattern doesn't work
**Solution:** Use imports instead

```python
# Old
exec(open("mainCAISO.py").read())

# New
from lib.iso.caiso import CAISOClient
client = CAISOClient()
```

### Issue 3: Different error handling

**Symptom:** Scripts that caught `sys.exit()` won't work
**Solution:** Catch proper exceptions

```python
# Old
try:
    exec(open("mainCAISO.py").read())
except SystemExit:
    print("Failed")

# New
from lib.iso.caiso import CAISOClient
try:
    client = CAISOClient()
    success = client.get_lmp(...)
    if not success:
        print("Failed")
except Exception as e:
    print(f"Error: {e}")
```

## 🎓 Learning Resources

### For New v2.0 Features

1. **Quick Start:** Read `QUICKSTART.md`
2. **Full Docs:** Read `README.md`
3. **Examples:** Check `examples/` directory
4. **API Docs:** Run `python -m pydoc lib.iso.caiso`

### For Python Modernization

- [Type Hints](https://docs.python.org/3/library/typing.html)
- [Dataclasses](https://docs.python.org/3/library/dataclasses.html)
- [Enums](https://docs.python.org/3/library/enum.html)
- [Logging](https://docs.python.org/3/library/logging.html)

## 📞 Getting Help

### During Migration

1. Check this migration guide
2. Review `QUICKSTART.md` for basic usage
3. Check GitHub Issues for similar problems
4. Create new issue with `[Migration]` tag

### Common Migration Questions

**Q: Do I need to re-download all my data?**
A: No! Existing data files are compatible.

**Q: Can I run v1.1 and v2.0 side-by-side?**
A: Yes, in different directories or virtual environments.

**Q: Will my cron jobs break?**
A: Yes, update them to use new CLI interface (see examples above).

**Q: What about my custom analysis scripts?**
A: They'll work fine - CSV format is unchanged.

## ✅ Migration Checklist

- [ ] Backup existing data and scripts
- [ ] Update Python to 3.10+
- [ ] Create new virtual environment
- [ ] Install v2.0 dependencies
- [ ] Test basic download functionality
- [ ] Migrate custom scripts (if any)
- [ ] Update cron jobs/automation
- [ ] Update documentation/notes
- [ ] Test integrated workflows
- [ ] Archive v1.1 scripts (optional)

## 🎉 You're Ready!

Once you've completed the migration, you'll have:

✅ Modern, maintainable code
✅ Better error handling
✅ Type safety and IDE support
✅ Comprehensive testing
✅ Flexible CLI and API
✅ Active development and support

Welcome to ISO-DART v2.0!
