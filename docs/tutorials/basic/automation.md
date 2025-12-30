# Automating Data Downloads

## Overview

This tutorial shows you how to automate ISO-DART downloads for regular data collection.

**Time Required:** 30 minutes

**What You'll Learn:**
- Creating automated download scripts
- Scheduling with cron (Linux/Mac) or Task Scheduler (Windows)
- Error handling and notifications
- Logging best practices

## Prerequisites

- ISO-DART installed and working
- Basic Python knowledge
- Understanding of your operating system's scheduler

## Part 1: Daily Download Script

### Create the Script

Create `daily_download.py`:

```python
#!/usr/bin/env python3
"""
Daily automated download script for ISO-DART.
Downloads yesterday's CAISO Day-Ahead LMP data.
"""

import logging
from datetime import date, timedelta
from pathlib import Path
from lib.iso.caiso import CAISOClient, Market

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'daily_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def download_yesterday():
    """Download yesterday's CAISO DAM LMP data."""
    yesterday = date.today() - timedelta(days=1)
    
    logger.info(f"Starting download for {yesterday}")
    
    client = CAISOClient()
    
    try:
        success = client.get_lmp(
            market=Market.DAM,
            start_date=yesterday,
            end_date=yesterday
        )
        
        if success:
            logger.info(f"✓ Successfully downloaded data for {yesterday}")
            return True
        else:
            logger.error(f"✗ Failed to download data for {yesterday}")
            return False
            
    except Exception as e:
        logger.error(f"Error during download: {e}", exc_info=True)
        return False
        
    finally:
        client.cleanup()


if __name__ == '__main__':
    success = download_yesterday()
    exit(0 if success else 1)
```

Make it executable (Linux/Mac):

```bash
chmod +x daily_download.py
```

### Test the Script

```bash
python daily_download.py
```

Check the output:

```bash
cat logs/daily_download.log
```

## Part 2: Multi-ISO Download Script

Create `download_all_isos.py`:

```python
#!/usr/bin/env python3
"""Download data from multiple ISOs."""

import logging
from datetime import date, timedelta
from pathlib import Path
from lib.iso.caiso import CAISOClient, Market as CAISOMarket
from lib.iso.miso import MISOClient, MISOConfig
from lib.iso.nyiso import NYISOClient, NYISOMarket

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/multi_iso_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def download_caiso(target_date):
    """Download CAISO data."""
    logger.info(f"Downloading CAISO data for {target_date}")
    client = CAISOClient()
    
    try:
        # Download DAM LMP
        success_lmp = client.get_lmp(
            CAISOMarket.DAM, target_date, target_date
        )
        
        # Download load forecast
        success_load = client.get_load_forecast(
            CAISOMarket.DAM, target_date, target_date
        )
        
        return success_lmp and success_load
        
    except Exception as e:
        logger.error(f"CAISO error: {e}", exc_info=True)
        return False
    finally:
        client.cleanup()


def download_miso(target_date):
    """Download MISO data."""
    logger.info(f"Downloading MISO data for {target_date}")
    
    try:
        config = MISOConfig.from_ini_file()
        client = MISOClient(config)
        
        # Download LMP
        data = client.get_lmp('da_exante', target_date, 1)
        
        if data:
            client.save_to_csv(data, f'miso_lmp_{target_date}.csv')
            return True
        return False
        
    except Exception as e:
        logger.error(f"MISO error: {e}", exc_info=True)
        return False


def download_nyiso(target_date):
    """Download NYISO data."""
    logger.info(f"Downloading NYISO data for {target_date}")
    client = NYISOClient()
    
    try:
        success = client.get_lbmp(
            NYISOMarket.DAM, 'zonal', target_date, 1
        )
        return success
        
    except Exception as e:
        logger.error(f"NYISO error: {e}", exc_info=True)
        return False
    finally:
        client.cleanup()


def main():
    """Download from all ISOs."""
    yesterday = date.today() - timedelta(days=1)
    
    logger.info(f"=== Starting multi-ISO download for {yesterday} ===")
    
    results = {
        'CAISO': download_caiso(yesterday),
        'MISO': download_miso(yesterday),
        'NYISO': download_nyiso(yesterday)
    }
    
    # Log results
    logger.info("=== Download Summary ===")
    for iso, success in results.items():
        status = "✓" if success else "✗"
        logger.info(f"{status} {iso}: {'Success' if success else 'Failed'}")
    
    # Return success if all downloads succeeded
    return all(results.values())


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
```

## Part 3: Scheduling on Linux/Mac (cron)

### Basic Cron Setup

Edit your crontab:

```bash
crontab -e
```

Add daily download at 2 AM:

```cron
# Download yesterday's data every day at 2 AM
0 2 * * * cd /path/to/ISO-DART && /path/to/venv/bin/python daily_download.py >> logs/cron.log 2>&1
```

### Advanced Cron Examples

```cron
# Daily at 2 AM
0 2 * * * cd /path/to/ISO-DART && /path/to/venv/bin/python daily_download.py

# Hourly downloads
0 * * * * cd /path/to/ISO-DART && /path/to/venv/bin/python hourly_download.py

# Weekly on Monday at 3 AM
0 3 * * 1 cd /path/to/ISO-DART && /path/to/venv/bin/python weekly_download.py

# Monthly on 1st at midnight
0 0 1 * * cd /path/to/ISO-DART && /path/to/venv/bin/python monthly_download.py

# Weekdays only at 6 AM
0 6 * * 1-5 cd /path/to/ISO-DART && /path/to/venv/bin/python weekday_download.py
```

### Cron with Virtual Environment

Create a wrapper script `run_download.sh`:

```bash
#!/bin/bash

# ISO-DART download wrapper
cd /path/to/ISO-DART
source venv/bin/activate
python daily_download.py
deactivate
```

Make it executable:

```bash
chmod +x run_download.sh
```

Add to crontab:

```cron
0 2 * * * /path/to/ISO-DART/run_download.sh
```

### Verify Cron Jobs

```bash
# List current cron jobs
crontab -l

# Check cron logs
grep CRON /var/log/syslog
```

## Part 4: Scheduling on Windows (Task Scheduler)

### Create Batch File

Create `daily_download.bat`:

```batch
@echo off
cd C:\path\to\ISO-DART
call venv\Scripts\activate
python daily_download.py
deactivate
```

### Create Scheduled Task

1. Open Task Scheduler (search in Start menu)
2. Click "Create Basic Task"
3. Name: "ISO-DART Daily Download"
4. Trigger: Daily at 2:00 AM
5. Action: Start a program
6. Program: `C:\path\to\ISO-DART\daily_download.bat`
7. Finish

### PowerShell Script Alternative

Create `daily_download.ps1`:

```powershell
# ISO-DART daily download
$ErrorActionPreference = "Stop"

Set-Location "C:\path\to\ISO-DART"
& .\venv\Scripts\Activate.ps1
python daily_download.py

if ($LASTEXITCODE -ne 0) {
    Write-Error "Download failed"
    exit 1
}
```

## Part 5: Email Notifications

### Add Email to Script

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(subject, body, to_email):
    """Send email notification."""
    from_email = "your-email@gmail.com"
    password = "your-app-password"
    
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logger.error(f"Email error: {e}")
        return False


def download_with_notification():
    """Download with email notification."""
    yesterday = date.today() - timedelta(days=1)
    
    client = CAISOClient()
    try:
        success = client.get_lmp(Market.DAM, yesterday, yesterday)
        
        if success:
            subject = f"✓ ISO-DART: Download successful for {yesterday}"
            body = f"Successfully downloaded CAISO DAM LMP data for {yesterday}"
        else:
            subject = f"✗ ISO-DART: Download failed for {yesterday}"
            body = f"Failed to download data. Check logs for details."
        
        send_email(subject, body, "your-email@example.com")
        return success
        
    finally:
        client.cleanup()
```

## Part 6: Error Handling and Retry Logic

### Robust Download Script

```python
import time
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)


def download_with_retry(client, market, target_date, max_retries=3):
    """Download with exponential backoff retry."""
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt + 1}/{max_retries}")
            
            success = client.get_lmp(market, target_date, target_date)
            
            if success:
                logger.info(f"✓ Download succeeded on attempt {attempt + 1}")
                return True
            
            # Wait before retry (exponential backoff)
            if attempt < max_retries - 1:
                wait_time = 30 * (2 ** attempt)  # 30s, 60s, 120s
                logger.warning(f"Attempt {attempt + 1} failed. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                
        except Exception as e:
            logger.error(f"Error on attempt {attempt + 1}: {e}", exc_info=True)
            
            if attempt < max_retries - 1:
                wait_time = 30 * (2 ** attempt)
                time.sleep(wait_time)
    
    logger.error(f"✗ All {max_retries} attempts failed")
    return False


def main():
    """Main download function with retry logic."""
    yesterday = date.today() - timedelta(days=1)
    
    client = CAISOClient()
    try:
        success = download_with_retry(client, Market.DAM, yesterday)
        return success
    finally:
        client.cleanup()
```

## Part 7: Monitoring and Alerts

### Check for Missing Data

```python
from pathlib import Path
from datetime import date, timedelta


def check_data_integrity(days_back=7):
    """Check if data exists for past N days."""
    data_dir = Path("data/CAISO")
    missing_dates = []
    
    for i in range(days_back):
        check_date = date.today() - timedelta(days=i+1)
        date_str = check_date.strftime("%Y%m%d")
        
        # Look for files with this date
        files = list(data_dir.glob(f"{date_str}_*_PRC_LMP_*.csv"))
        
        if not files:
            missing_dates.append(check_date)
    
    if missing_dates:
        logger.warning(f"Missing data for dates: {missing_dates}")
        return False, missing_dates
    else:
        logger.info(f"✓ All data present for last {days_back} days")
        return True, []


def backfill_missing_data(missing_dates):
    """Download data for missing dates."""
    client = CAISOClient()
    
    try:
        for target_date in missing_dates:
            logger.info(f"Backfilling {target_date}")
            client.get_lmp(Market.DAM, target_date, target_date)
    finally:
        client.cleanup()


# Use in main script
if __name__ == '__main__':
    # Regular download
    download_yesterday()
    
    # Check integrity
    ok, missing = check_data_integrity()
    
    if not ok:
        # Backfill missing dates
        backfill_missing_data(missing)
```

## Part 8: Complete Production Script

```python
#!/usr/bin/env python3
"""
Production-ready automated download script.
Features: retry logic, email notifications, monitoring.
"""

import logging
import smtplib
import time
from datetime import date, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from lib.iso.caiso import CAISOClient, Market

# Configuration
LOG_DIR = Path("logs")
DATA_DIR = Path("data/CAISO")
MAX_RETRIES = 3
NOTIFICATION_EMAIL = "your-email@example.com"

# Setup logging
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'production_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def send_notification(subject, body):
    """Send email notification."""
    try:
        # Configure your email settings here
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['To'] = NOTIFICATION_EMAIL
        
        # Add email sending code here
        logger.info(f"Notification sent: {subject}")
        
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")


def download_with_retry(target_date, max_retries=MAX_RETRIES):
    """Download with retry logic."""
    client = CAISOClient()
    
    try:
        for attempt in range(max_retries):
            logger.info(f"Attempt {attempt + 1}/{max_retries} for {target_date}")
            
            success = client.get_lmp(Market.DAM, target_date, target_date)
            
            if success:
                logger.info(f"✓ Success on attempt {attempt + 1}")
                return True
            
            if attempt < max_retries - 1:
                wait = 30 * (2 ** attempt)
                logger.warning(f"Retry in {wait}s...")
                time.sleep(wait)
        
        return False
        
    finally:
        client.cleanup()


def check_recent_files(days=7):
    """Verify recent files exist."""
    missing = []
    
    for i in range(1, days + 1):
        check_date = date.today() - timedelta(days=i)
        date_str = check_date.strftime("%Y%m%d")
        
        if not list(DATA_DIR.glob(f"{date_str}_*_PRC_LMP_*.csv")):
            missing.append(check_date)
    
    return missing


def main():
    """Main execution."""
    logger.info("=== Starting automated download ===")
    
    yesterday = date.today() - timedelta(days=1)
    
    # Download yesterday's data
    success = download_with_retry(yesterday)
    
    # Check for missing dates
    missing = check_recent_files()
    
    if missing:
        logger.warning(f"Missing data for: {missing}")
        # Backfill
        for date_to_fill in missing:
            download_with_retry(date_to_fill)
    
    # Send notification
    if success:
        send_notification(
            f"✓ ISO-DART Download Complete",
            f"Successfully downloaded data for {yesterday}"
        )
    else:
        send_notification(
            f"✗ ISO-DART Download Failed",
            f"Failed to download data for {yesterday}. Check logs."
        )
    
    logger.info("=== Download complete ===")
    return success


if __name__ == '__main__':
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        send_notification("✗ ISO-DART Critical Error", str(e))
        exit(1)
```

## Best Practices

1. **Always use logging** - Track what happened
2. **Implement retry logic** - APIs can be unreliable
3. **Check for missing data** - Backfill automatically
4. **Send notifications** - Know when things fail
5. **Use absolute paths** - Cron runs from different directories
6. **Test manually first** - Verify before scheduling
7. **Monitor disk space** - Data accumulates over time

## Troubleshooting

### Cron job not running

```bash
# Check cron is running
service cron status

# Check system logs
grep CRON /var/log/syslog

# Test with simple command first
* * * * * echo "Test" >> /tmp/crontest.txt
```

### Script works manually but not in cron

- Use absolute paths for everything
- Set environment variables in script
- Activate virtual environment properly
- Check file permissions

### Email notifications not working

- Use app-specific passwords (Gmail)
- Check firewall settings
- Test SMTP connection separately
- Verify email credentials

## Next Steps

- Set up monitoring dashboards
- Implement data quality checks
- Create backup strategies
- Build alerting systems

## See Also

- [Command Line Guide](../user-guide/command-line.md)
- [Python API Guide](../user-guide/python-api.md)
- [Operations Guide](../operations/deployment.rst)
