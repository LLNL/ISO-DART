# Command Line Usage Guide

## Overview

ISO-DART provides a powerful command-line interface for downloading electricity market data. This guide covers all command-line options and common usage patterns.

## Basic Syntax

```bash
python isodart.py [OPTIONS]
```

## Quick Examples

```bash
# Interactive mode (easiest)
python isodart.py

# Download CAISO Day-Ahead LMP
python isodart.py --iso caiso --data-type lmp --market dam \
  --start 2024-01-01 --duration 7

# Download MISO fuel mix
python isodart.py --iso miso --data-type fuel-mix \
  --start 2024-01-01 --duration 30

# Download weather data
python isodart.py --data-type weather --state CA \
  --start 2024-01-01 --duration 30
```

## Global Options

### Required Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `--iso` | ISO to download from | `--iso caiso` |
| `--data-type` | Type of data to download | `--data-type lmp` |
| `--start` | Start date (YYYY-MM-DD) | `--start 2024-01-01` |
| `--duration` | Duration in days | `--duration 7` |

### Optional Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--market` | Market type | None |
| `--verbose` | Enable verbose logging | False |
| `--config` | Path to config file | None |
| `--interactive` | Force interactive mode | False |

## ISO-Specific Options

### CAISO Options

```bash
# LMP data
python isodart.py --iso caiso --data-type lmp --market dam \
  --start 2024-01-01 --duration 7

# Available markets: dam, rtm, hasp, rtpd, ruc
# Available data types: lmp, load, wind-solar, fuel-prices, ghg-prices, as-prices
```

### MISO Options

```bash
# LMP data
python isodart.py --iso miso --data-type lmp --lmp-type da_exante \
  --start 2024-01-01 --duration 7

# Available LMP types: da_exante, da_expost, rt_exante, rt_expost
# Available data types: lmp, mcp, load, fuel-mix, generation
```

### NYISO Options

```bash
# LBMP data
python isodart.py --iso nyiso --data-type lbmp --market dam --level zonal \
  --start 2024-01-01 --duration 7

# Available levels: zonal, generator
# Available data types: lbmp, load, fuel-mix, btm-solar
```

### SPP Options

```bash
# LMP by settlement location
python isodart.py --iso spp --data-type lmp --market dam \
  --start 2024-01-01 --duration 7

# LMP by bus
python isodart.py --iso spp --data-type lmp --market dam --by-bus \
  --start 2024-01-01 --duration 7

# Available markets: dam, rtbm
# Available data types: lmp, mcp, operating-reserves, binding-constraints
```

### BPA Options

```bash
# Wind and load data
python isodart.py --iso bpa --data-type wind_gen_total_load \
  --start 2024-01-01 --duration 7

# Available data types: wind_gen_total_load, reserves_deployed, all
```

### PJM Options

```bash
# Day-ahead LMP
python isodart.py --iso pjm --data-type lmp --lmp-type da_hourly \
  --start 2024-01-01 --duration 7

# With specific pricing node
python isodart.py --iso pjm --data-type lmp --lmp-type da_hourly \
  --pnode-id 51288 --start 2024-01-01 --duration 7

# Available LMP types: da_hourly, rt_5min, rt_hourly
```

### ISO-NE Options

```bash
# Day-ahead hourly LMP
python isodart.py --iso isone --data-type lmp --lmp-type da_hourly \
  --start 2024-01-01 --duration 7

# Available data types: lmp, ancillary, demand
```

## Weather Data Options

```bash
# Download weather data
python isodart.py --data-type weather --state CA \
  --start 2024-01-01 --duration 30

# Include solar data
python isodart.py --data-type weather --state CA \
  --start 2024-01-01 --duration 30 --include-solar
```

## Advanced Usage

### Using Configuration Files

Create a `config.yaml`:

```yaml
caiso:
  max_retries: 5
  timeout: 60

logging:
  level: DEBUG
  file: logs/isodart.log
```

Use it:

```bash
python isodart.py --config config.yaml --iso caiso --data-type lmp \
  --market dam --start 2024-01-01 --duration 7
```

### Automation with Cron

```bash
# Daily download at 2 AM
0 2 * * * cd /path/to/ISO-DART && /path/to/venv/bin/python isodart.py --iso caiso --data-type lmp --market dam --start $(date -d "yesterday" +\%Y-\%m-\%d) --duration 1

# Weekly download on Monday
0 3 * * 1 cd /path/to/ISO-DART && /path/to/venv/bin/python isodart.py --iso caiso --data-type lmp --market dam --start $(date -d "7 days ago" +\%Y-\%m-\%d) --duration 7
```

### Batch Processing

Create a shell script `download_all.sh`:

```bash
#!/bin/bash

START_DATE="2024-01-01"
DURATION=7

# Download multiple data types
python isodart.py --iso caiso --data-type lmp --market dam --start $START_DATE --duration $DURATION
python isodart.py --iso caiso --data-type lmp --market rtm --start $START_DATE --duration $DURATION
python isodart.py --iso caiso --data-type load --market dam --start $START_DATE --duration $DURATION
python isodart.py --iso caiso --data-type wind-solar --start $START_DATE --duration $DURATION

echo "All downloads complete!"
```

Make it executable:

```bash
chmod +x download_all.sh
./download_all.sh
```

## Output Files

Downloaded files are saved to:

```
data/
├── CAISO/
│   └── YYYYMMDD_to_YYYYMMDD_datatype.csv
├── MISO/
│   └── miso_datatype_YYYY-MM-DD.csv
├── NYISO/
│   └── YYYYMMDD_to_YYYYMMDD_dataid.csv
├── SPP/
│   └── YYYYMMDD_to_YYYYMMDD_SPP_datatype.csv
├── BPA/
│   └── YYYY_BPA_datatype.csv
├── PJM/
│   └── MM-DD-YYYY_to_MM-DD-YYYY_datatype.csv
└── weather/
    └── YYYY-MM-DD_to_YYYY-MM-DD_station_STATE.csv
```

## Logging

Enable verbose logging:

```bash
python isodart.py --verbose --iso caiso --data-type lmp --market dam \
  --start 2024-01-01 --duration 7
```

Check logs:

```bash
tail -f logs/isodart.log
```

## Error Handling

### Common Errors

**"API Error 404: Data not found"**
- Date range may be too recent or too old
- Data may not exist for that period
- Try a different date range

**"ModuleNotFoundError"**
- Activate virtual environment
- Install dependencies: `pip install -r requirements.txt`

**"Authentication failed"**
- Check API keys in `user_config.ini`
- Verify credentials are correct

### Exit Codes

- `0`: Success
- `1`: Download failed or error occurred

Check exit code:

```bash
python isodart.py --iso caiso --data-type lmp --market dam --start 2024-01-01 --duration 7
echo $?  # 0 = success, 1 = failure
```

## Best Practices

1. **Start with small date ranges** to test connectivity
2. **Use verbose mode** when debugging
3. **Check logs** for detailed error messages
4. **Automate wisely** - respect API rate limits
5. **Validate data** after download

## Command Reference

### Quick Reference Table

| Command | Purpose |
|---------|---------|
| `python isodart.py` | Interactive mode |
| `python isodart.py --help` | Show help |
| `python isodart.py --iso caiso --data-type lmp --market dam --start 2024-01-01 --duration 7` | Download CAISO DAM LMP |
| `python isodart.py --verbose` | Enable debug output |
| `python isodart.py --config file.yaml` | Use custom config |

## Next Steps

- See [Python API Guide](python-api.md) for programmatic usage
- See [Configuration Guide](configuration.md) for setup details
- See [Examples](../tutorials/examples/index.rst) for more usage patterns