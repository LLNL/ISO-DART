"""
Interactive mode for ISO-DART v2.0

User-friendly command-line interface for data downloads.
Complete coverage of all CAISO, MISO, NYISO, and SPP client methods.
"""

from datetime import date, datetime, timedelta
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def get_date_input() -> Tuple[date, int]:
    """
    Get start date and duration from user with validation.

    Returns:
        Tuple of (start_date, duration_in_days)
    """
    print("\n" + "=" * 60)
    print("DATE SELECTION")
    print("=" * 60)

    while True:
        try:
            print("\nPlease enter the start date and duration:")
            year = int(input("  Year (4-digit format, e.g., 2024): "))
            month = int(input("  Month (1-12): "))
            day = int(input("  Day (1-31): "))

            start_date = date(year, month, day)

            # Validate date is not in the future
            if start_date > date.today():
                print("\n⚠️  Warning: Date is in the future. Please select a past date.")
                continue

            break

        except ValueError as e:
            print(f"\n❌ Invalid date: {e}")
            print("Please try again with valid values.")
            continue

    while True:
        try:
            duration = int(input("\n  Duration (in days): "))
            if duration <= 0:
                print("Duration must be positive!")
                continue
            if duration > 365:
                confirm = input(f"You selected {duration} days (over a year). Continue? (y/n): ")
                if confirm.lower() != "y":
                    continue
            break
        except ValueError:
            print("Please enter a valid number!")
            continue

    end_date = start_date + timedelta(days=duration)
    print(f"\n✓ Date range: {start_date} to {end_date}")

    return start_date, duration


# ============================================================================
# MAIN MENU
# ============================================================================


def run_interactive_mode():
    """Run the interactive command-line interface."""
    print("\n" + "=" * 60)
    print(" ISO-DART v2.0")
    print(" Independent System Operator Data Automated Request Tool")
    print("=" * 60)

    # Main data type selection
    print("\nWhat type of data do you want to download?")
    print("  (1) ISO Data (CAISO, MISO, NYISO, SPP, BPA, PJM, ISO-NE)")
    print("  (2) Weather Data")

    while True:
        try:
            data_type = int(input("\nYour choice (1 or 2): "))
            if data_type in [1, 2]:
                break
            print("Please enter 1 or 2")
        except ValueError:
            print("Please enter a valid number")

    if data_type == 1:
        run_iso_mode()
    else:
        run_weather_mode()


# ============================================================================
# ISO SELECTION
# ============================================================================


def run_iso_mode():
    """Interactive mode for ISO data."""
    print("\n" + "=" * 60)
    print("ISO DATA SELECTION")
    print("=" * 60)

    # ISO selection
    print("\nWhich ISO do you want data from?")
    print("  (1) CAISO - California Independent System Operator")
    print("  (2) MISO - Midcontinent Independent System Operator")
    print("  (3) NYISO - New York Independent System Operator")
    print("  (4) SPP - Southwest Power Pool")
    print("  (5) BPA - Bonneville Power Administration")
    print("  (6) PJM - Pennsylvania, New Jersey, Maryland Interconnection")
    print("  (7) ISO-NE - New England Independent System Operator")

    while True:
        try:
            iso_choice = int(input("\nYour choice (1-7): "))
            if iso_choice in range(1, 8):
                break
            print("Please enter 1, 2, 3, 4, 5, 6, or 7")
        except ValueError:
            print("Please enter a valid number")

    if iso_choice == 1:
        run_caiso_mode()
    elif iso_choice == 2:
        run_miso_mode()
    elif iso_choice == 3:
        run_nyiso_mode()
    elif iso_choice == 4:
        run_spp_mode()
    elif iso_choice == 5:
        run_bpa_mode()
    elif iso_choice == 6:
        run_pjm_mode()
    else:
        run_isone_mode()


# ============================================================================
# CAISO MAIN MENU
# ============================================================================


def run_caiso_mode():
    """Interactive mode for CAISO data."""
    print("\n" + "=" * 60)
    print("CAISO DATA SELECTION")
    print("=" * 60)

    # Data type selection
    print("\nWhat type of CAISO data?")
    print("  (1) Pricing Data")
    print("  (2) System Demand Data")
    print("  (3) Energy Data")
    print("  (4) Ancillary Services Data")

    while True:
        try:
            caiso_type = int(input("\nYour choice (1-4): "))
            if caiso_type in [1, 2, 3, 4]:
                break
            print("Please enter a number between 1 and 4")
        except ValueError:
            print("Please enter a valid number")

    if caiso_type == 1:
        run_caiso_pricing()
    elif caiso_type == 2:
        run_caiso_demand()
    elif caiso_type == 3:
        run_caiso_energy()
    else:
        run_caiso_ancillary()


# ============================================================================
# CAISO - PRICING DATA
# ============================================================================


def run_caiso_pricing():
    """CAISO pricing data selection."""
    from lib.iso.caiso import CAISOClient, Market

    print("\n" + "=" * 60)
    print("CAISO PRICING DATA")
    print("=" * 60)

    print("\nWhat type of pricing data?")
    print("  (1) Locational Marginal Prices (LMP)")
    print("  (2) Scheduling Point Tie Prices")
    print("  (3) Ancillary Services Clearing Prices")
    print("  (4) Intertie Constraint Shadow Prices")
    print("  (5) Fuel Prices")
    print("  (6) GHG Allowance Prices")

    while True:
        try:
            price_type = int(input("\nYour choice (1-6): "))
            if price_type in range(1, 7):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 6")

    if price_type == 1:
        # LMP selection
        print("\nWhich energy market?")
        print("  (1) Day-Ahead Market (DAM)")
        print("  (2) Hour-Ahead Scheduling Process (HASP)")
        print("  (3) Real-Time Market (RTM)")
        print("  (4) Real-Time Pre-Dispatch (RTPD)")

        while True:
            try:
                market_choice = int(input("\nYour choice (1-4): "))
                if market_choice in range(1, 5):
                    break
            except ValueError:
                pass
            print("Please enter a number between 1 and 4")

        market_map = {1: Market.DAM, 2: Market.HASP, 3: Market.RTM, 4: Market.RTPD}
        market = market_map[market_choice]

        # Get date range
        start_date, duration = get_date_input()
        end_date = start_date + timedelta(days=duration)

        # Download data
        print(f"\n📥 Downloading {market.value} LMP data...")
        print(f"   Date range: {start_date} to {end_date}")
        print("   This may take a few minutes...\n")

        client = CAISOClient()
        try:
            success = client.get_lmp(market, start_date, end_date, step_size=1)
            if success:
                print("\n✅ Download complete!")
                print(f"   Data saved to: data/CAISO/")
            else:
                print("\n❌ Download failed. Check logs for details.")
        except Exception as e:
            logger.error(f"Error downloading data: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
        finally:
            client.cleanup()

    elif price_type == 2:
        # Scheduling Point Tie Prices
        print("\nWhich market?")
        print("  (1) Day-Ahead Market (DAM)")
        print("  (2) Real-Time Pre-Dispatch (RTPD)")

        while True:
            try:
                market_choice = int(input("\nYour choice (1-2): "))
                if market_choice in [1, 2]:
                    break
            except ValueError:
                pass

        market = Market.DAM if market_choice == 1 else Market.RTPD

        start_date, duration = get_date_input()
        end_date = start_date + timedelta(days=duration)

        client = CAISOClient()
        try:
            print(f"\n📥 Downloading {market.value} Scheduling Point Tie Prices...")
            success = client.get_scheduling_point_tie_prices(market, start_date, end_date)
            if success:
                print("\n✅ Download complete!")
                print(f"   Data saved to: data/CAISO/")
            else:
                print("\n❌ Download failed. Check logs for details.")
        finally:
            client.cleanup()

    elif price_type == 3:
        # AS Prices
        print("\nWhich market?")
        print("  (1) Day-Ahead Market (DAM)")
        print("  (2) Real-Time Market (RTM)")

        while True:
            try:
                market_choice = int(input("\nYour choice (1-2): "))
                if market_choice in [1, 2]:
                    break
            except ValueError:
                pass

        market = Market.DAM if market_choice == 1 else Market.RTM

        start_date, duration = get_date_input()
        end_date = start_date + timedelta(days=duration)

        client = CAISOClient()
        try:
            print(f"\n📥 Downloading {market.value} AS Prices...")
            success = client.get_ancillary_services_prices(market, start_date, end_date)
            if success:
                print("\n✅ Download complete!")
                print(f"   Data saved to: data/CAISO/")
            else:
                print("\n❌ Download failed. Check logs for details.")
        finally:
            client.cleanup()

    elif price_type == 4:
        # Constraint Shadow Prices
        start_date, duration = get_date_input()
        end_date = start_date + timedelta(days=duration)

        client = CAISOClient()
        try:
            print(f"\n📥 Downloading Intertie Constraint Shadow Prices...")
            success = client.get_intertie_constraint_shadow_prices(start_date, end_date)
            if success:
                print("\n✅ Download complete!")
                print(f"   Data saved to: data/CAISO/")
            else:
                print("\n❌ Download failed. Check logs for details.")
        finally:
            client.cleanup()

    elif price_type == 5:
        # Fuel Prices
        start_date, duration = get_date_input()
        end_date = start_date + timedelta(days=duration)

        client = CAISOClient()
        try:
            print(f"\n📥 Downloading Fuel Prices...")
            success = client.get_fuel_prices(start_date, end_date)
            if success:
                print("\n✅ Download complete!")
                print(f"   Data saved to: data/CAISO/")
            else:
                print("\n❌ Download failed. Check logs for details.")
        finally:
            client.cleanup()

    elif price_type == 6:
        # GHG Allowance Prices
        start_date, duration = get_date_input()
        end_date = start_date + timedelta(days=duration)

        client = CAISOClient()
        try:
            print(f"\n📥 Downloading GHG Allowance Prices...")
            success = client.get_ghg_allowance_prices(start_date, end_date)
            if success:
                print("\n✅ Download complete!")
                print(f"   Data saved to: data/CAISO/")
            else:
                print("\n❌ Download failed. Check logs for details.")
        finally:
            client.cleanup()


# ============================================================================
# CAISO - SYSTEM DEMAND DATA
# ============================================================================


def run_caiso_demand():
    """CAISO demand forecast selection."""
    from lib.iso.caiso import CAISOClient, Market

    print("\n" + "=" * 60)
    print("CAISO DEMAND FORECAST")
    print("=" * 60)

    print("\nWhat type of demand forecast?")
    print("  (1) Standard Demand Forecast")
    print("  (2) Advisory Demand Forecast (RTPD)")

    while True:
        try:
            forecast_type = int(input("\nYour choice (1-2): "))
            if forecast_type in [1, 2]:
                break
        except ValueError:
            pass
        print("Please enter 1 or 2")

    if forecast_type == 1:
        print("\nWhich forecast market?")
        print("  (1) Day-Ahead Market (DAM)")
        print("  (2) Two Day-Ahead (2DA)")
        print("  (3) Seven Day-Ahead (7DA)")
        print("  (4) Real-Time Market (RTM)")

        while True:
            try:
                market_choice = int(input("\nYour choice (1-4): "))
                if market_choice in range(1, 5):
                    break
            except ValueError:
                pass
            print("Please enter a number between 1 and 4")

        market_map = {1: Market.DAM, 2: Market.TWO_DA, 3: Market.SEVEN_DA, 4: Market.RTM}
        market = market_map[market_choice]

        start_date, duration = get_date_input()
        end_date = start_date + timedelta(days=duration)

        print(f"\n📥 Downloading {market.value} Load Forecast...")

        client = CAISOClient()
        try:
            success = client.get_load_forecast(market, start_date, end_date)
            if success:
                print("\n✅ Download complete!")
                print(f"   Data saved to: data/CAISO/")
            else:
                print("\n❌ Download failed. Check logs for details.")
        finally:
            client.cleanup()

    else:  # Advisory forecast
        start_date, duration = get_date_input()
        end_date = start_date + timedelta(days=duration)

        print(f"\n📥 Downloading Advisory Demand Forecast...")

        client = CAISOClient()
        try:
            success = client.get_advisory_demand_forecast(start_date, end_date)
            if success:
                print("\n✅ Download complete!")
                print(f"   Data saved to: data/CAISO/")
            else:
                print("\n❌ Download failed or no data available.")
        finally:
            client.cleanup()


# ============================================================================
# CAISO - ENERGY DATA
# ============================================================================


def run_caiso_energy():
    """CAISO energy data selection."""
    from lib.iso.caiso import CAISOClient, Market

    print("\n" + "=" * 60)
    print("CAISO ENERGY DATA")
    print("=" * 60)

    print("\nWhat type of energy data?")
    print("  (1) System Load and Resource Schedules")
    print("  (2) Market Power Mitigation (MPM) Status")
    print("  (3) Flexible Ramping Requirements")
    print("  (4) Flexible Ramping Awards")
    print("  (5) Flexible Ramping Demand Curves")
    print("  (6) EIM Transfer")
    print("  (7) EIM Transfer Limits")
    print("  (8) Wind and Solar Summary")

    while True:
        try:
            energy_type = int(input("\nYour choice (1-8): "))
            if energy_type in range(1, 9):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 8")

    start_date, duration = get_date_input()
    end_date = start_date + timedelta(days=duration)

    client = CAISOClient()

    try:
        if energy_type == 1:
            # System Load
            print("\nWhich market?")
            print("  (1) Day-Ahead Market (DAM)")
            print("  (2) Residual Unit Commitment (RUC)")
            print("  (3) Hour-Ahead Scheduling Process (HASP)")
            print("  (4) Real-Time Market (RTM)")

            while True:
                try:
                    market_choice = int(input("\nYour choice (1-4): "))
                    if market_choice in range(1, 5):
                        break
                except ValueError:
                    pass

            market_map = {1: Market.DAM, 2: Market.RUC, 3: Market.HASP, 4: Market.RTM}
            market = market_map[market_choice]

            print(f"\n📥 Downloading {market.value} System Load...")
            success = client.get_system_load(market, start_date, end_date)

        elif energy_type == 2:
            # MPM Status
            print("\nWhich market?")
            print("  (1) Day-Ahead Market (DAM)")
            print("  (2) Hour-Ahead Scheduling Process (HASP)")
            print("  (3) Real-Time Pre-Dispatch (RTPD)")

            while True:
                try:
                    market_choice = int(input("\nYour choice (1-3): "))
                    if market_choice in range(1, 4):
                        break
                except ValueError:
                    pass

            market_map = {1: Market.DAM, 2: Market.HASP, 3: Market.RTPD}
            market = market_map[market_choice]

            print(f"\n📥 Downloading {market.value} MPM Status...")
            success = client.get_market_power_mitigation(market, start_date, end_date)

        elif energy_type == 3:
            print("\n📥 Downloading Flexible Ramping Requirements...")
            success = client.get_flex_ramp_requirements(start_date, end_date)

        elif energy_type == 4:
            print("\n📥 Downloading Flexible Ramping Awards...")
            success = client.get_flex_ramp_awards(start_date, end_date)

        elif energy_type == 5:
            print("\n📥 Downloading Flexible Ramping Demand Curves...")
            success = client.get_flex_ramp_demand_curve(start_date, end_date)

        elif energy_type == 6:
            print("\n📥 Downloading EIM Transfer...")
            success = client.get_eim_transfer(start_date, end_date)

        elif energy_type == 7:
            print("\n📥 Downloading EIM Transfer Limits...")
            success = client.get_eim_transfer_limits(start_date, end_date)

        elif energy_type == 8:
            print("\n📥 Downloading Wind and Solar Summary...")
            success = client.get_wind_solar_summary(start_date, end_date)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/CAISO/")
        else:
            print("\n❌ Download failed. Check logs for details.")

    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
    finally:
        client.cleanup()


# ============================================================================
# CAISO - ANCILLARY SERVICES DATA
# ============================================================================


def run_caiso_ancillary():
    """CAISO ancillary services selection."""
    from lib.iso.caiso import CAISOClient, Market

    print("\n" + "=" * 60)
    print("CAISO ANCILLARY SERVICES DATA")
    print("=" * 60)

    print("\nWhat type of ancillary services data?")
    print("  (1) AS Requirements")
    print("  (2) AS Results/Awards")
    print("  (3) Actual Operating Reserves")

    while True:
        try:
            anc_type = int(input("\nYour choice (1-3): "))
            if anc_type in range(1, 4):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 3")

    if anc_type in [1, 2]:
        print("\nWhich market?")
        print("  (1) Day-Ahead Market (DAM)")
        print("  (2) Hour-Ahead Scheduling Process (HASP)")
        print("  (3) Real-Time Market (RTM)")

        while True:
            try:
                market_choice = int(input("\nYour choice (1-3): "))
                if market_choice in range(1, 4):
                    break
            except ValueError:
                pass

        market_map = {1: Market.DAM, 2: Market.HASP, 3: Market.RTM}
        market = market_map[market_choice]

    start_date, duration = get_date_input()
    end_date = start_date + timedelta(days=duration)

    client = CAISOClient()

    try:
        if anc_type == 1:
            print(f"\n📥 Downloading {market.value} AS Requirements...")
            success = client.get_ancillary_services_requirements(market, start_date, end_date)
        elif anc_type == 2:
            print(f"\n📥 Downloading {market.value} AS Results...")
            success = client.get_ancillary_services_results(market, start_date, end_date)
        else:  # Operating reserves
            print(f"\n📥 Downloading Operating Reserves...")
            success = client.get_operating_reserves(start_date, end_date)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/CAISO/")
        else:
            print("\n❌ Download failed. Check logs for details.")

    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
    finally:
        client.cleanup()


# ============================================================================
# MISO MODE
# ============================================================================


def run_miso_mode():
    """Interactive mode for MISO data."""
    from lib.iso.miso import MISOConfig, MISOClient

    print("\n" + "=" * 60)
    print("MISO DATA SELECTION")
    print("=" * 60)

    print("\nWhat type of data?")
    print("  (1) Pricing Data (LMP & MCP)")
    print("  (2) Load & Demand Data")
    print("  (3) Generation Data")
    print("  (4) Interchange Data")
    print("  (5) Outages & Constraints")

    while True:
        try:
            data_type = int(input("\nYour choice (1-5): "))
            if data_type in range(1, 6):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 5")

    if data_type == 1:
        run_miso_pricing()
    elif data_type == 2:
        run_miso_load()
    elif data_type == 3:
        run_miso_generation()
    elif data_type == 4:
        run_miso_interchange()
    else:
        run_miso_outages()


def run_miso_pricing():
    """MISO pricing data selection."""
    from lib.iso.miso import MISOConfig, MISOClient

    print("\n" + "=" * 60)
    print("MISO PRICING DATA")
    print("=" * 60)

    print("\nWhat type of pricing data?")
    print("  (1) Locational Marginal Prices (LMP)")
    print("  (2) Market Clearing Prices (MCP)")

    while True:
        try:
            price_type = int(input("\nYour choice (1-2): "))
            if price_type in [1, 2]:
                break
        except ValueError:
            pass
        print("Please enter 1 or 2")

    if price_type == 1:
        run_miso_lmp()
    else:
        run_miso_mcp()


def run_miso_lmp():
    """MISO LMP data selection."""
    from lib.iso.miso import MISOConfig, MISOClient

    print("\n" + "=" * 60)
    print("MISO LMP DATA")
    print("=" * 60)

    print("\nWhat type of LMP?")
    print("  (1) Day-Ahead ExAnte LMP")
    print("  (2) Day-Ahead ExPost LMP")
    print("  (3) Real-Time ExAnte LMP")
    print("  (4) Real-Time ExPost LMP")

    while True:
        try:
            lmp_type = int(input("\nYour choice (1-4): "))
            if lmp_type in range(1, 5):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 4")

    lmp_map = {
        1: "da_exante",
        2: "da_expost",
        3: "rt_exante",
        4: "rt_expost",
    }

    lmp_choice = lmp_map[lmp_type]

    start_date, duration = get_date_input()

    config = MISOConfig.from_ini_file()
    client = MISOClient(config)

    try:
        print(f"\n📥 Downloading MISO {lmp_choice.upper()} LMP data...")
        data = client.get_lmp(lmp_choice, start_date, duration)

        if data:
            filename = f"miso_{lmp_choice}_lmp_{start_date}.csv"
            client.save_to_csv(data, filename)
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/MISO/{filename}")
            print(f"   Records: {sum(len(records) for records in data.values())}")
        else:
            print("\n❌ Download failed. Check logs for details.")
    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


def run_miso_mcp():
    """MISO MCP data selection."""
    from lib.iso.miso import MISOConfig, MISOClient

    print("\n" + "=" * 60)
    print("MISO MCP DATA")
    print("=" * 60)

    print("\nWhat type of MCP?")
    print("  (1) ASM Day-Ahead ExAnte MCP")
    print("  (2) ASM Day-Ahead ExPost MCP")
    print("  (3) ASM Real-Time ExAnte MCP")
    print("  (4) ASM Real-Time ExPost MCP")
    print("  (5) ASM Real-Time Summary MCP")

    while True:
        try:
            mcp_type = int(input("\nYour choice (1-5): "))
            if mcp_type in range(1, 6):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 5")

    mcp_map = {
        1: "asm_da_exante",
        2: "asm_da_expost",
        3: "asm_rt_exante",
        4: "asm_rt_expost",
        5: "asm_rt_summary",
    }

    mcp_choice = mcp_map[mcp_type]

    start_date, duration = get_date_input()

    config = MISOConfig.from_ini_file()
    client = MISOClient(config)

    try:
        print(f"\n📥 Downloading MISO {mcp_choice.upper()} MCP data...")
        data = client.get_mcp(mcp_choice, start_date, duration)

        if data:
            filename = f"miso_{mcp_choice}_mcp_{start_date}.csv"
            client.save_to_csv(data, filename)
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/MISO/{filename}")
            print(f"   Records: {sum(len(records) for records in data.values())}")
        else:
            print("\n❌ Download failed. Check logs for details.")
    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


def run_miso_load():
    """MISO load and demand data selection."""
    from lib.iso.miso import MISOConfig, MISOClient

    print("\n" + "=" * 60)
    print("MISO LOAD & DEMAND DATA")
    print("=" * 60)

    print("\nWhat type of load data?")
    print("  (1) Day-Ahead Demand")
    print("  (2) Real-Time Demand Forecast")
    print("  (3) Real-Time Actual Load")
    print("  (4) Real-Time State Estimator Load")
    print("  (5) Medium-Term Load Forecast")

    while True:
        try:
            load_type = int(input("\nYour choice (1-5): "))
            if load_type in range(1, 6):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 5")

    start_date, duration = get_date_input()

    config = MISOConfig.from_ini_file()
    client = MISOClient(config)

    try:
        if load_type == 1:
            print(f"\n📥 Downloading Day-Ahead Demand...")
            data = client.get_demand("da_demand", start_date, duration, time_resolution="daily")
            filename = f"miso_da_demand_{start_date}.csv"

        elif load_type == 2:
            print(f"\n📥 Downloading Real-Time Demand Forecast...")
            data = client.get_demand("rt_forecast", start_date, duration, time_resolution="daily")
            filename = f"miso_rt_demand_forecast_{start_date}.csv"

        elif load_type == 3:
            print(f"\n📥 Downloading Real-Time Actual Load...")
            data = client.get_demand("rt_actual", start_date, duration, time_resolution="daily")
            filename = f"miso_rt_actual_load_{start_date}.csv"

        elif load_type == 4:
            print(f"\n📥 Downloading State Estimator Load...")
            data = client.get_demand(
                "rt_state_estimator", start_date, duration, time_resolution="daily"
            )
            filename = f"miso_state_estimator_load_{start_date}.csv"

        else:  # load_type == 5
            print(f"\n📥 Downloading Medium-Term Load Forecast...")
            data = client.get_load_forecast(start_date, duration, time_resolution="daily")
            filename = f"miso_load_forecast_{start_date}.csv"

        if data:
            client.save_to_csv(data, filename)
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/MISO/{filename}")
            print(f"   Records: {sum(len(records) for records in data.values())}")
        else:
            print("\n❌ Download failed. Check logs for details.")

    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


def run_miso_generation():
    """MISO generation data selection."""
    from lib.iso.miso import MISOConfig, MISOClient

    print("\n" + "=" * 60)
    print("MISO GENERATION DATA")
    print("=" * 60)

    print("\nWhat type of generation data?")
    print("  (1) Day-Ahead Cleared Generation (Physical)")
    print("  (2) Day-Ahead Cleared Generation (Virtual)")
    print("  (3) Day-Ahead Generation Fuel Type")
    print("  (4) Day-Ahead Offered Generation (ECOMAX)")
    print("  (5) Day-Ahead Offered Generation (ECOMIN)")
    print("  (6) Real-Time Cleared Generation")
    print("  (7) Real-Time Committed Generation (ECOMAX)")
    print("  (8) Real-Time Fuel on the Margin")
    print("  (9) Real-Time Generation Fuel Type")
    print(" (10) Real-Time Offered Generation (ECOMAX)")

    while True:
        try:
            gen_type = int(input("\nYour choice (1-10): "))
            if gen_type in range(1, 11):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 10")

    gen_map = {
        1: ("da_cleared_physical", "Day-Ahead Cleared Physical"),
        2: ("da_cleared_virtual", "Day-Ahead Cleared Virtual"),
        3: ("da_fuel_type", "Day-Ahead Fuel Type"),
        4: ("da_offered_ecomax", "Day-Ahead Offered ECOMAX"),
        5: ("da_offered_ecomin", "Day-Ahead Offered ECOMIN"),
        6: ("rt_cleared", "Real-Time Cleared"),
        7: ("rt_committed_ecomax", "Real-Time Committed ECOMAX"),
        8: ("rt_fuel_margin", "Real-Time Fuel on Margin"),
        9: ("rt_fuel_type", "Real-Time Fuel Type"),
        10: ("rt_offered_ecomax", "Real-Time Offered ECOMAX"),
    }

    gen_choice, gen_name = gen_map[gen_type]

    start_date, duration = get_date_input()

    config = MISOConfig.from_ini_file()
    client = MISOClient(config)

    try:
        print(f"\n📥 Downloading {gen_name}...")

        # Special handling for fuel on margin
        if gen_choice == "rt_fuel_margin":
            data = client.get_fuel_mix(start_date, duration)
        else:
            data = client.get_generation(gen_choice, start_date, duration)

        if data:
            filename = f"miso_{gen_choice}_{start_date}.csv"
            client.save_to_csv(data, filename)
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/MISO/{filename}")
            print(f"   Records: {sum(len(records) for records in data.values())}")
        else:
            print("\n❌ Download failed. Check logs for details.")

    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


def run_miso_interchange():
    """MISO interchange data selection."""
    from lib.iso.miso import MISOConfig, MISOClient

    print("\n" + "=" * 60)
    print("MISO INTERCHANGE DATA")
    print("=" * 60)

    print("\nWhat type of interchange data?")
    print("  (1) Day-Ahead Net Scheduled Interchange")
    print("  (2) Real-Time Net Actual Interchange")
    print("  (3) Real-Time Net Scheduled Interchange")
    print("  (4) Historical Net Scheduled Interchange")

    while True:
        try:
            interchange_type = int(input("\nYour choice (1-4): "))
            if interchange_type in range(1, 5):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 4")

    interchange_map = {
        1: "da_net_scheduled",
        2: "rt_net_actual",
        3: "rt_net_scheduled",
        4: "historical",
    }

    interchange_choice = interchange_map[interchange_type]

    start_date, duration = get_date_input()

    config = MISOConfig.from_ini_file()
    client = MISOClient(config)

    try:
        print(f"\n📥 Downloading {interchange_choice.replace('_', ' ').title()}...")
        data = client.get_interchange(interchange_choice, start_date, duration)

        if data:
            filename = f"miso_{interchange_choice}_{start_date}.csv"
            client.save_to_csv(data, filename)
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/MISO/{filename}")
            print(f"   Records: {sum(len(records) for records in data.values())}")
        else:
            print("\n❌ Download failed. Check logs for details.")

    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


def run_miso_outages():
    """MISO outages and constraints data selection."""
    from lib.iso.miso import MISOConfig, MISOClient

    print("\n" + "=" * 60)
    print("MISO OUTAGES & CONSTRAINTS")
    print("=" * 60)

    print("\nWhat type of data?")
    print("  (1) Outage Forecast")
    print("  (2) Real-Time Outages")
    print("  (3) Real-Time Binding Constraints")

    while True:
        try:
            data_type = int(input("\nYour choice (1-3): "))
            if data_type in range(1, 4):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 3")

    start_date, duration = get_date_input()

    config = MISOConfig.from_ini_file()
    client = MISOClient(config)

    try:
        if data_type == 1:
            print(f"\n📥 Downloading Outage Forecast...")
            data = client.get_outages("forecast", start_date, duration)
            filename = f"miso_outage_forecast_{start_date}.csv"

        elif data_type == 2:
            print(f"\n📥 Downloading Real-Time Outages...")
            data = client.get_outages("rt_outage", start_date, duration)
            filename = f"miso_rt_outages_{start_date}.csv"

        else:  # data_type == 3
            print(f"\n📥 Downloading Binding Constraints...")
            data = client.get_binding_constraints(start_date, duration)
            filename = f"miso_binding_constraints_{start_date}.csv"

        if data:
            client.save_to_csv(data, filename)
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/MISO/{filename}")
            print(f"   Records: {sum(len(records) for records in data.values())}")
        else:
            print("\n❌ Download failed. Check logs for details.")

    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


# ============================================================================
# NYISO MODE
# ============================================================================


def run_nyiso_mode():
    """Interactive mode for NYISO data."""
    from lib.iso.nyiso import NYISOClient

    print("\n" + "=" * 60)
    print("NYISO DATA SELECTION")
    print("=" * 60)

    # NOTE: Keep this menu in sync with NYISOClient methods.
    # NYISO publishes several datasets as monthly ZIPs (most methods), and a couple
    # as direct CSVs (outage schedule + generation maintenance).
    print("\nWhat type of data?")
    print("  (1) Pricing Data")
    print("  (2) Power Grid Data (Outages, Constraints, Schedules)")
    print("  (3) Load Data")
    print("  (4) Bid Data")
    print("  (5) Fuel Mix")
    print("  (6) Interface Flows")
    print("  (7) BTM Solar Generation")

    while True:
        try:
            data_type = int(input("\nYour choice (1-7): "))
            if data_type in range(1, 8):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 7")

    if data_type == 1:
        run_nyiso_pricing()
    elif data_type == 2:
        run_nyiso_power_grid()
    elif data_type == 3:
        run_nyiso_load()
    elif data_type == 4:
        run_nyiso_bid()
    elif data_type == 5:
        run_nyiso_fuel_mix()
    elif data_type == 6:
        run_nyiso_interface_flows()
    else:
        run_nyiso_btm_solar()


def run_nyiso_pricing():
    """NYISO pricing data selection."""
    from lib.iso.nyiso import NYISOClient, NYISOMarket

    print("\n" + "=" * 60)
    print("NYISO PRICING DATA")
    print("=" * 60)

    print("\nWhat type of pricing data?")
    print("  (1) Locational Based Marginal Prices (LBMP)")
    print("  (2) Ancillary Services Prices")

    while True:
        try:
            price_type = int(input("\nYour choice (1-2): "))
            if price_type in [1, 2]:
                break
        except ValueError:
            pass
        print("Please enter 1 or 2")

    print("\nWhich energy market?")
    print("  (1) Day-Ahead Market (DAM)")
    print("  (2) Real-Time Market (RTM)")

    while True:
        try:
            market_choice = int(input("\nYour choice (1-2): "))
            if market_choice in [1, 2]:
                break
        except ValueError:
            pass
        print("Please enter 1 or 2")

    market = NYISOMarket.DAM if market_choice == 1 else NYISOMarket.RTM

    if price_type == 1:
        print("\nWhat degree of detail?")
        print("  (1) Zonal")
        print("  (2) Generator")

        while True:
            try:
                level_choice = int(input("\nYour choice (1-2): "))
                if level_choice in [1, 2]:
                    break
            except ValueError:
                pass

        level = "zonal" if level_choice == 1 else "generator"

        start_date, duration = get_date_input()

        client = NYISOClient()
        try:
            print(f"\n📥 Downloading {market.value} LBMP ({level})...")
            success = client.get_lbmp(market, level, start_date, duration)

            if success:
                print("\n✅ Download complete!")
                print(f"   Data saved to: data/NYISO/")
            else:
                print("\n❌ Download failed. Check logs for details.")
        except Exception as e:
            logger.error(f"Error downloading data: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")

    else:  # AS Prices
        start_date, duration = get_date_input()

        client = NYISOClient()
        try:
            print(f"\n📥 Downloading {market.value} Ancillary Services Prices...")
            success = client.get_ancillary_services_prices(market, start_date, duration)

            if success:
                print("\n✅ Download complete!")
                print(f"   Data saved to: data/NYISO/")
            else:
                print("\n❌ Download failed. Check logs for details.")
        except Exception as e:
            logger.error(f"Error downloading data: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")


def run_nyiso_power_grid():
    """NYISO power grid data selection."""
    from lib.iso.nyiso import NYISOClient, NYISOMarket

    print("\n" + "=" * 60)
    print("NYISO POWER GRID DATA")
    print("=" * 60)

    print("\nWhat type of power grid data?")
    print("  (1) Transmission Outages (monthly ZIPs; DAM / RTM scheduled / RTM actual)")
    print("  (2) Constraints")
    print("  (3) Outage Schedule (P-14B direct CSV)")
    print("  (4) Generation Maintenance Report (P-15 direct CSV)")

    while True:
        try:
            grid_type = int(input("\nYour choice (1-4): "))
            if grid_type in [1, 2, 3, 4]:
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 4")

    # Direct CSV products do not depend on DAM/RTM market selection.
    if grid_type in [3, 4]:
        start_date, duration = get_date_input()
        client = NYISOClient()
        try:
            if grid_type == 3:
                print("\n📥 Downloading NYISO Outage Schedule (P-14B)...")
                success = client.get_outage_schedule(start_date, duration)
            else:
                print("\n📥 Downloading NYISO Generation Maintenance Report (P-15)...")
                success = client.get_generation_maintenance_report(start_date, duration)

            if success:
                print("\n✅ Download complete!")
                print("   Data saved to: data/NYISO/")
            else:
                print("\n❌ Download failed. Check logs for details.")
        except Exception as e:
            logger.error(f"Error downloading data: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
        return

    print("\nWhich energy market?")
    print("  (1) Day-Ahead Market (DAM)")
    print("  (2) Real-Time Market (RTM)")

    while True:
        try:
            market_choice = int(input("\nYour choice (1-2): "))
            if market_choice in [1, 2]:
                break
        except ValueError:
            pass
        print("Please enter 1 or 2")

    market = NYISOMarket.DAM if market_choice == 1 else NYISOMarket.RTM

    if grid_type == 1:  # Transmission Outages
        outage_type = None
        if market == NYISOMarket.RTM:
            print("\nWhat type of outages?")
            print("  (1) Scheduled")
            print("  (2) Actual")

            while True:
                try:
                    outage_choice = int(input("\nYour choice (1-2): "))
                    if outage_choice in [1, 2]:
                        break
                except ValueError:
                    pass

            outage_type = "scheduled" if outage_choice == 1 else "actual"

        start_date, duration = get_date_input()

        client = NYISOClient()
        try:
            print(f"\n📥 Downloading {market.value} Outages...")
            success = client.get_outages(market, outage_type, start_date, duration)

            if success:
                print("\n✅ Download complete!")
                print(f"   Data saved to: data/NYISO/")
            else:
                print("\n❌ Download failed. Check logs for details.")
        except Exception as e:
            logger.error(f"Error downloading data: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")

    else:  # Constraints
        start_date, duration = get_date_input()

        client = NYISOClient()
        try:
            print(f"\n📥 Downloading {market.value} Constraints...")
            success = client.get_constraints(market, start_date, duration)

            if success:
                print("\n✅ Download complete!")
                print(f"   Data saved to: data/NYISO/")
            else:
                print("\n❌ Download failed. Check logs for details.")
        except Exception as e:
            logger.error(f"Error downloading data: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")


def run_nyiso_load():
    """NYISO load data selection."""
    from lib.iso.nyiso import NYISOClient

    print("\n" + "=" * 60)
    print("NYISO LOAD DATA")
    print("=" * 60)

    print("\nWhat type of load data?")
    print("  (1) ISO Load Forecast")
    print("  (2) Zonal Bid Load")
    print("  (3) Weather Forecast")
    print("  (4) Actual Load")

    while True:
        try:
            load_type = int(input("\nYour choice (1-4): "))
            if load_type in range(1, 5):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 4")

    load_map = {1: "iso_forecast", 2: "zonal_bid", 3: "weather_forecast", 4: "actual"}

    load_choice = load_map[load_type]

    start_date, duration = get_date_input()

    client = NYISOClient()
    try:
        print(f"\n📥 Downloading NYISO Load Data...")
        success = client.get_load_data(load_choice, start_date, duration)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/NYISO/")
        else:
            print("\n❌ Download failed. Check logs for details.")
    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


def run_nyiso_bid():
    """NYISO bid data selection."""
    from lib.iso.nyiso import NYISOClient

    print("\n" + "=" * 60)
    print("NYISO BID DATA")
    print("=" * 60)

    print("\nWhat type of bid data?")
    print("  (1) Generator and Ancillary Service Bids")
    print("  (2) Load Bids")
    print("  (3) Transaction Bids")
    print("  (4) Generator Commitment Parameter Bids")

    while True:
        try:
            bid_type = int(input("\nYour choice (1-4): "))
            if bid_type in range(1, 5):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 4")

    bid_map = {1: "generator", 2: "load", 3: "transaction", 4: "commitment"}

    bid_choice = bid_map[bid_type]

    start_date, duration = get_date_input()

    client = NYISOClient()
    try:
        print(f"\n📥 Downloading NYISO Bid Data...")
        success = client.get_bid_data(bid_choice, start_date, duration)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/NYISO/")
        else:
            print("\n❌ Download failed. Check logs for details.")
    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


def run_nyiso_fuel_mix():
    """NYISO fuel mix data selection."""
    from lib.iso.nyiso import NYISOClient

    print("\n" + "=" * 60)
    print("NYISO FUEL MIX DATA")
    print("=" * 60)

    start_date, duration = get_date_input()

    client = NYISOClient()
    try:
        print(f"\n📥 Downloading NYISO Real-Time Fuel Mix...")
        success = client.get_fuel_mix(start_date, duration)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/NYISO/")
        else:
            print("\n❌ Download failed. Check logs for details.")
    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


def run_nyiso_interface_flows():
    """NYISO interface flows data selection."""
    from lib.iso.nyiso import NYISOClient

    print("\n" + "=" * 60)
    print("NYISO INTERFACE FLOWS DATA")
    print("=" * 60)

    start_date, duration = get_date_input()

    client = NYISOClient()
    try:
        print(f"\n📥 Downloading NYISO Interface Flows...")
        success = client.get_interface_flows(start_date, duration)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/NYISO/")
        else:
            print("\n❌ Download failed. Check logs for details.")
    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


def run_nyiso_wind():
    """NYISO wind generation data selection."""
    from lib.iso.nyiso import NYISOClient

    print("\n" + "=" * 60)
    print("NYISO WIND GENERATION DATA")
    print("=" * 60)

    start_date, duration = get_date_input()

    client = NYISOClient()
    try:
        print(f"\n📥 Downloading NYISO Wind Generation...")
        success = client.get_wind_generation(start_date, duration)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/NYISO/")
        else:
            print("\n❌ Download failed. Check logs for details.")
    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


def run_nyiso_btm_solar():
    """NYISO BTM solar generation data selection."""
    from lib.iso.nyiso import NYISOClient

    print("\n" + "=" * 60)
    print("NYISO BEHIND-THE-METER SOLAR DATA")
    print("=" * 60)

    start_date, duration = get_date_input()

    client = NYISOClient()
    try:
        print(f"\n📥 Downloading NYISO BTM Solar Generation...")
        success = client.get_btm_solar(start_date, duration)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/NYISO/")
        else:
            print("\n❌ Download failed. Check logs for details.")
    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


# ============================================================================
# SPP MODE
# ============================================================================


def run_spp_mode():
    """Interactive mode for SPP data."""
    from lib.iso.spp import SPPClient, SPPMarket

    print("\n" + "=" * 60)
    print("SPP DATA SELECTION")
    print("=" * 60)

    print("\nWhat type of data?")
    print("  (1) Pricing Data")
    print("  (2) Operating Reserves")
    print("  (3) Binding Constraints")
    print("  (4) Fuel On Margin")
    print("  (5) Load Forecast")
    print("  (6) Resource Forecast")
    print("  (7) Clearing Data")

    while True:
        try:
            data_category = int(input("\nYour choice (1-7): "))
            if data_category in range(1, 8):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 7")

    client = SPPClient()

    try:
        if data_category == 1:  # Pricing Data
            print("\n" + "=" * 60)
            print("SPP PRICING DATA")
            print("=" * 60)

            print("\nWhat type of pricing data?")
            print("  (1) Locational Marginal Prices (LMP)")
            print("  (2) Market Clearing Prices (MCP)")

            while True:
                try:
                    price_type = int(input("\nYour choice (1-2): "))
                    if price_type in [1, 2]:
                        break
                except ValueError:
                    pass
                print("Please enter 1 or 2")

            print("\nWhich market?")
            print("  (1) Day-Ahead Market (DAM)")
            print("  (2) Real-Time Balancing Market (RTBM)")

            while True:
                try:
                    market_choice = int(input("\nYour choice (1-2): "))
                    if market_choice in [1, 2]:
                        break
                except ValueError:
                    pass
                print("Please enter 1 or 2")

            market = SPPMarket.DAM if market_choice == 1 else SPPMarket.RTBM

            if price_type == 1:  # LMP
                print("\nLMP by:")
                print("  (1) Settlement Location")
                print("  (2) Bus")

                while True:
                    try:
                        loc_choice = int(input("\nYour choice (1-2): "))
                        if loc_choice in [1, 2]:
                            break
                    except ValueError:
                        pass
                    print("Please enter 1 or 2")

                by_location = loc_choice == 1
                loc_type = "Settlement Location" if by_location else "Bus"

                start_date, duration = get_date_input()
                end_date = start_date + timedelta(days=duration)

                print(f"\n📥 Downloading {market.value} LMP by {loc_type}...")
                success = client.get_lmp(market, start_date, end_date, by_location=by_location)

            else:  # MCP
                start_date, duration = get_date_input()
                end_date = start_date + timedelta(days=duration)

                print(f"\n📥 Downloading {market.value} Market Clearing Prices...")
                success = client.get_mcp(market, start_date, end_date)

        elif data_category == 2:  # Operating Reserves
            print("\n" + "=" * 60)
            print("SPP OPERATING RESERVES")
            print("=" * 60)

            start_date, duration = get_date_input()
            end_date = start_date + timedelta(days=duration)

            print(f"\n📥 Downloading Operating Reserves...")
            success = client.get_operating_reserves(start_date, end_date)

        elif data_category == 3:  # Binding Constraints
            print("\n" + "=" * 60)
            print("SPP BINDING CONSTRAINTS")
            print("=" * 60)

            print("\nWhich market?")
            print("  (1) Day-Ahead Market (DAM)")
            print("  (2) Real-Time Balancing Market (RTBM)")

            while True:
                try:
                    market_choice = int(input("\nYour choice (1-2): "))
                    if market_choice in [1, 2]:
                        break
                except ValueError:
                    pass
                print("Please enter 1 or 2")

            market = SPPMarket.DAM if market_choice == 1 else SPPMarket.RTBM

            start_date, duration = get_date_input()
            end_date = start_date + timedelta(days=duration)

            print(f"\n📥 Downloading {market.value} Binding Constraints...")
            success = client.get_binding_constraints(market, start_date, end_date)

        elif data_category == 4:  # Fuel On Margin
            print("\n" + "=" * 60)
            print("SPP FUEL ON MARGIN")
            print("=" * 60)

            start_date, duration = get_date_input()
            end_date = start_date + timedelta(days=duration)

            print(f"\n📥 Downloading Fuel On Margin...")
            success = client.get_fuel_on_margin(start_date, end_date)

        elif data_category == 5:  # Load Forecast
            print("\n" + "=" * 60)
            print("SPP LOAD FORECAST")
            print("=" * 60)

            print("\nForecast Type?")
            print("  (1) Short-Term")
            print("  (2) Medium-Term")

            while True:
                try:
                    forecast_choice = int(input("\nYour choice (1-2): "))
                    if forecast_choice in [1, 2]:
                        break
                except ValueError:
                    pass
                print("Please enter 1 or 2")

            forecast_type = "stlf" if forecast_choice == 1 else "mtlf"

            start_date, duration = get_date_input()
            end_date = start_date + timedelta(days=duration)

            print(f"\n📥 Downloading {forecast_type} Load Forecast...")
            success = client.get_load_forecast(start_date, end_date, forecast_type=forecast_type)

        elif data_category == 6:  # Resource Forecast
            print("\n" + "=" * 60)
            print("SPP RESOURCE (SOLAR + WIND) FORECAST")
            print("=" * 60)

            print("\nForecast Type?")
            print("  (1) Short-Term")
            print("  (2) Medium-Term")

            while True:
                try:
                    forecast_choice = int(input("\nYour choice (1-2): "))
                    if forecast_choice in [1, 2]:
                        break
                except ValueError:
                    pass
                print("Please enter 1 or 2")

            forecast_type = "strf" if forecast_choice == 1 else "mtrf"

            start_date, duration = get_date_input()
            end_date = start_date + timedelta(days=duration)

            print(f"\n📥 Downloading {forecast_type} Resource (solar + wind) Forecast...")
            success = client.get_resource_forecast(
                start_date, end_date, forecast_type=forecast_type
            )

        elif data_category == 7:  # Clearing Data
            print("\n" + "=" * 60)
            print("SPP CLEARING DATA")
            print("=" * 60)

            print("\nClearing Type?")
            print("  (1) Market Clearing Data")
            print("  (2) Virtual Clearing Data")

            while True:
                try:
                    clearing_choice = int(input("\nYour choice (1-2): "))
                    if clearing_choice in [1, 2]:
                        break
                except ValueError:
                    pass
                print("Please enter 1 or 2")

            clearing_type = "market" if clearing_choice == 1 else "virtual"

            start_date, duration = get_date_input()
            end_date = start_date + timedelta(days=duration)

            print(f"\n📥 Downloading {clearing_type} Clearing Data...")
            if clearing_type == "market":
                success = client.get_market_clearing(start_date, end_date)
            else:
                success = client.get_virtual_clearing(start_date, end_date)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/SPP/")
        else:
            print("\n❌ Download failed. Check logs for details.")

    except Exception as e:
        logger.error(f"Error downloading SPP data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
    finally:
        client.cleanup()


# ============================================================================
# BPA MODE
# ============================================================================


def run_bpa_mode():
    """Interactive mode for BPA historical data."""
    from lib.iso.bpa import BPAClient, BPAPathsKind, get_bpa_data_availability
    from datetime import date, timedelta
    import difflib

    print("\n" + "=" * 60)
    print("BPA DATA SELECTION")
    print("=" * 60)

    # Show BPA data availability info
    info = get_bpa_data_availability()

    print("\n📊 BPA Historical Data Information")
    print("=" * 60)
    print(f"• Coverage: {info['temporal_coverage']}")
    print(f"• Resolution: {info['temporal_resolution']}")
    print(f"• Update Frequency: {info['update_frequency']}")
    print(f"• Geographic Area: {info['geographic_coverage']}")
    print(f"• Data Format: Excel (.xlsx)")

    available_years = info["available_years"]
    print(f"\n• Available Years: {min(available_years)} - {max(available_years)}")

    print("\n" + "=" * 60)

    # Data type selection
    print("\nWhat type of BPA data?")
    print("  (1) Wind Generation and Total Load")
    print("      - Hourly wind generation (MW)")
    print("      - Hourly total load (MW)")
    print("  (2) Operating Reserves Deployed")
    print("      - Regulation Up/Down reserves")
    print("      - Contingency reserves")
    print("  (3) Outages")
    print("  (4) Transmission Paths")

    data_type = None
    kind = None  # BPAPathsKind
    report_id = None  # str

    while True:
        try:
            data_type = int(input("\nYour choice (1-4): "))
            if data_type in range(1, 5):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 4")

    # Extra prompts for Transmission Paths
    if data_type == 4:
        print("\nWhat kind of transmission path?")
        print("  (1) Flowgate")
        print("  (2) Intertie")

        while True:
            try:
                kind_choice = int(input("\nYour choice (1-2): "))
                if kind_choice in (1, 2):
                    break
            except ValueError:
                pass
            print("Please enter a number between 1 and 2")

        kind = BPAPathsKind.FLOWGATE if kind_choice == 1 else BPAPathsKind.INTERTIE

        # Pull available ReportIDs (best-effort). If it fails, allow manual entry.
        options = []
        try:
            print("\n🔎 Fetching available BPA Transmission Path ReportIDs...")
            tmp = BPAClient()
            try:
                available = tmp.list_paths() if hasattr(tmp, "list_paths") else None
            finally:
                tmp.cleanup()

            if available:
                flowgates = available.get("Flowgate") or available.get("flowgates") or []
                interties = available.get("Intertie") or available.get("interties") or []
                options = sorted(flowgates if kind == BPAPathsKind.FLOWGATE else interties)

                print(f"\n✓ Found {len(options)} {kind.value} ReportIDs.")
                if options:
                    preview = options[:25]
                    print("  Examples:")
                    for rid in preview:
                        print(f"   • {rid}")
                    if len(options) > len(preview):
                        print(f"   ... (+{len(options) - len(preview)} more)")
                    print(
                        "\nTip: type 'list' to print all IDs, or type a partial ID and I'll suggest matches."
                    )
        except Exception as e:
            logger.warning(f"Could not fetch BPA path list (continuing with manual entry): {e}")

        # Choose ReportID
        while True:
            raw = input(f"\nEnter {kind.value} ReportID: ").strip()
            if not raw:
                print("Please enter a non-empty ReportID.")
                continue

            if raw.lower() == "list" and options:
                print(f"\nAll {kind.value} ReportIDs:")
                for rid in options:
                    print(f"  - {rid}")
                continue

            if options:
                # Accept exact (case-insensitive) match
                lowered = {r.lower(): r for r in options}
                if raw.lower() in lowered:
                    report_id = lowered[raw.lower()]
                    break

                # Suggest close matches
                suggestions = difflib.get_close_matches(raw, options, n=8, cutoff=0.4)
                if suggestions:
                    print("\nNot an exact match. Did you mean one of these?")
                    for s in suggestions:
                        print(f"  - {s}")
                    continue

                print("\n❌ Unknown ReportID for this category.")
                print("   Type 'list' to see all ReportIDs, or try again.")
                continue

            # No options fetched; accept whatever they type
            report_id = raw
            break

    # Year selection
    print("\n" + "=" * 60)
    print("YEAR SELECTION")
    print("=" * 60)
    print(f"\nBPA provides historical data by full calendar year.")
    print(f"Available years: {min(available_years)} - {max(available_years)}")

    while True:
        try:
            year = int(input(f"\nEnter year ({min(available_years)}-{max(available_years)}): "))
            if year in available_years:
                break
            else:
                print(f"Year must be between {min(available_years)} and {max(available_years)}")
        except ValueError:
            print("Please enter a valid year")

    # Optional date range filtering
    print("\n" + "=" * 60)
    print("DATE RANGE FILTERING (OPTIONAL)")
    print("=" * 60)

    print("\nWould you like to filter to a specific date range within the year?")
    print("This can reduce file size if you only need part of the year.")
    print("  (1) Yes - specify date range")
    print("  (2) No - download entire year")

    while True:
        try:
            date_choice = int(input("\nYour choice (1-2): "))
            if date_choice in (1, 2):
                break
        except ValueError:
            pass
        print("Please enter 1 or 2")

    start_date = None
    end_date = None

    if date_choice == 1:
        print("\nEnter start and end dates (within the selected year).")
        print("Note: BPA data is typically hourly. Dates are inclusive.")

        # Get start date
        while True:
            try:
                month = int(input("\n  Start Month (1-12): "))
                day = int(input("  Start Day (1-31): "))
                start_date = date(year, month, day)

                if start_date.year != year:
                    print(f"\n⚠️  Start date must be within {year}.")
                    continue

                if start_date > date.today():
                    print("\n⚠️  Date is in the future. Please select a past date.")
                    continue

                break

            except ValueError as e:
                print(f"\n❌ Invalid date: {e}")
                print("Please try again.")
                continue

        # Get end date
        while True:
            try:
                month = int(input("\n  End Month (1-12): "))
                day = int(input("  End Day (1-31): "))
                end_date = date(year, month, day)

                if end_date.year != year:
                    print(f"\n⚠️  End date must be within {year}.")
                    continue

                if end_date < start_date:
                    print("\n⚠️  End date must be after start date.")
                    continue

                if end_date > date.today():
                    print("\n⚠️  End date cannot be in the future.")
                    continue

                break

            except ValueError as e:
                print(f"\n❌ Invalid date: {e}")
                print("Please try again.")
                continue

        print(f"\n✓ Date range: {start_date} to {end_date}")
    else:
        print(f"\n✓ Will download entire year {year}")

    # Download data
    print("\n" + "=" * 60)
    print("DOWNLOADING DATA")
    print("=" * 60)
    print("\nDownloading BPA historical data (Excel format)...")
    print("This may take a moment depending on file size...")

    client = BPAClient()

    try:
        if data_type == 1:
            print("\n📥 Downloading Wind Generation and Total Load data...")
            print(f"   Year: {year}")
            if start_date:
                print(f"   Filtering: {start_date} to {end_date}")
            success = client.get_wind_gen_total_load(year, start_date, end_date)

        elif data_type == 2:
            print("\n📥 Downloading Operating Reserves Deployed data...")
            print(f"   Year: {year}")
            if start_date:
                print(f"   Filtering: {start_date} to {end_date}")
            success = client.get_reserves_deployed(year, start_date, end_date)

        elif data_type == 3:
            print("\n📥 Downloading Outages data...")
            print(f"   Year: {year}")
            if start_date:
                print(f"   Filtering: {start_date} to {end_date}")
            success = client.get_outages(year, start_date, end_date)

        elif data_type == 4:
            if not kind or not report_id:
                raise ValueError("Transmission Paths requires both a path kind and a ReportID.")
            print("\n📥 Downloading Transmission Paths data...")
            print(f"   Kind: {kind.value}")
            print(f"   ReportID: {report_id}")
            print(f"   Year: {year}")
            if start_date:
                print(f"   Filtering: {start_date} to {end_date}")
            success = client.get_transmission_paths(
                kind=kind,
                report_id=report_id,
                year=year,
                start_date=start_date,
                end_date=end_date,
                combine_months=True,
            )

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/BPA/")
            print("\n📊 Data Details:")
            print(f"   • Year: {year}")
            print(f"   • Resolution: {info['temporal_resolution']}")
            print(f"   • Format: Excel")
            print(f"   • Time Zone: Pacific Time")

            print("\n📁 Files Created:")
            if data_type == 1:
                print(f"   • {year}_BPA_Wind_Generation_Total_Load.xlsx")
            elif data_type == 2:
                print(f"   • {year}_BPA_Reserves_Deployed.xlsx")
            elif data_type == 3:
                print(f"   • {year}_BPA_Outages.xlsx")
            elif data_type == 4:
                print(
                    f"   • BPA/Transmission_Paths/{kind.value}/{report_id}/{report_id}_{year}_combined.xlsx"
                )

            print("\n💡 Tips:")
            print("   • Use isodart.py for batch downloads")
            print("   • Check data/BPA/ for additional output files")
            if data_type == 4:
                print(
                    "   • For Transmission Paths, ReportIDs come from BPA's PathFileLocations workbook"
                )

        else:
            print("\n⚠️  Download failed or no data was available for the selected period.")
            print("   Common issues:")
            print("   • Network connection problems")
            print("   • BPA website temporarily unavailable")
            print("   • Year not available on BPA servers")
            print(f"   • Try a different year from: {min(available_years)}-{max(available_years)}")

    except Exception as e:
        logger.error(f"Error downloading BPA data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        print("   Check logs/isodart.log for details")

    finally:
        client.cleanup()


# ============================================================================
# PJM MODE
# ============================================================================


def run_pjm_mode():
    """Interactive mode for PJM data."""
    from lib.iso.pjm import PJMClient, PJMConfig

    print("\n" + "=" * 60)
    print("PJM DATA SELECTION")
    print("=" * 60)

    print("\nWhat type of data?")
    print("  (1) Locational Marginal Prices (LMP)")
    print("  (2) Load Data")
    print("  (3) Renewable Generation")
    print("  (4) Ancillary Services")
    print("  (5) Outages and Transfer Limits")

    while True:
        try:
            data_type = int(input("\nYour choice (1-5): "))
            if data_type in range(1, 6):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 5")

    if data_type == 1:
        run_pjm_lmp()
    elif data_type == 2:
        run_pjm_load()
    elif data_type == 3:
        run_pjm_renewable()
    elif data_type == 4:
        run_pjm_ancillary()
    else:
        run_pjm_outages()


def run_pjm_lmp():
    """PJM LMP data selection."""
    from lib.iso.pjm import PJMClient, PJMConfig

    print("\n" + "=" * 60)
    print("PJM LOCATIONAL MARGINAL PRICES")
    print("=" * 60)

    print("\nWhat type of LMP?")
    print("  (1) Day-Ahead Hourly LMPs")
    print("  (2) Real-Time Five Minute LMPs")
    print("  (3) Real-Time Hourly LMPs")

    while True:
        try:
            lmp_type = int(input("\nYour choice (1-3): "))
            if lmp_type in range(1, 4):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 3")

    lmp_map = {
        1: ("da_hourly", "Day-Ahead Hourly"),
        2: ("rt_5min", "Real-Time 5-Minute"),
        3: ("rt_hourly", "Real-Time Hourly"),
    }

    lmp_choice, lmp_name = lmp_map[lmp_type]

    # Ask for pricing node ID
    print("\n" + "=" * 60)
    print("PRICING NODE SELECTION")
    print("=" * 60)
    print("\nDo you want to filter by a specific pricing node?")
    print("(Leave blank to download all nodes)")

    pnode_input = input("\nEnter Pricing Node ID (or press Enter for all): ").strip()
    pnode_id = int(pnode_input) if pnode_input else None

    if pnode_id:
        print(f"\n✓ Will download data for pricing node: {pnode_id}")
    else:
        print(f"\n✓ Will download data for all pricing nodes")

    # Get date range
    start_date, duration = get_date_input()

    # Download data
    print("\n" + "=" * 60)
    print("DOWNLOADING DATA")
    print("=" * 60)
    print(f"\n📥 Downloading {lmp_name} LMP data...")
    if pnode_id:
        print(f"   Pricing Node: {pnode_id}")
    print(f"   Date range: {start_date} to {start_date + timedelta(days=duration)}")
    print("   This may take a few minutes...\n")

    config = PJMConfig.from_ini_file()
    client = PJMClient(config)

    try:
        success = client.get_lmp(lmp_choice, start_date, duration, pnode_id=pnode_id)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/PJM/")
        else:
            print("\n❌ Download failed. Check logs for details.")

    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
    finally:
        client.cleanup()


def run_pjm_load():
    """PJM load data selection."""
    from lib.iso.pjm import PJMClient, PJMConfig

    print("\n" + "=" * 60)
    print("PJM LOAD DATA")
    print("=" * 60)

    print("\nWhat type of load data?")
    print("  (1) Load Forecast")
    print("  (2) Hourly Load")

    while True:
        try:
            load_category = int(input("\nYour choice (1-2): "))
            if load_category in [1, 2]:
                break
        except ValueError:
            pass
        print("Please enter 1 or 2")

    if load_category == 1:
        print("\nWhat type of load forecast?")
        print("  (1) Five Minute Load Forecast")
        print("  (2) Historical Load Forecast")
        print("  (3) Seven-Day Load Forecast")

        while True:
            try:
                forecast_type = int(input("\nYour choice (1-3): "))
                if forecast_type in range(1, 4):
                    break
            except ValueError:
                pass
            print("Please enter a number between 1 and 3")

        forecast_map = {
            1: ("5min", "Five Minute Load Forecast"),
            2: ("historical", "Historical Load Forecast"),
            3: ("7day", "Seven-Day Load Forecast"),
        }

        forecast_choice, forecast_name = forecast_map[forecast_type]

        start_date, duration = get_date_input()

        config = PJMConfig.from_ini_file()
        client = PJMClient(config)

        try:
            print(f"\n📥 Downloading {forecast_name}...")
            success = client.get_load_forecast(forecast_choice, start_date, duration)

            if success:
                print("\n✅ Download complete!")
                print(f"   Data saved to: data/PJM/")
            else:
                print("\n❌ Download failed. Check logs for details.")
        except Exception as e:
            logger.error(f"Error downloading data: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
        finally:
            client.cleanup()

    else:  # Hourly load
        print("\nWhat type of hourly load?")
        print("  (1) Estimated")
        print("  (2) Metered")
        print("  (3) Preliminary")

        while True:
            try:
                load_type = int(input("\nYour choice (1-3): "))
                if load_type in range(1, 4):
                    break
            except ValueError:
                pass
            print("Please enter a number between 1 and 3")

        load_map = {
            1: ("estimated", "Estimated Hourly Load"),
            2: ("metered", "Metered Hourly Load"),
            3: ("preliminary", "Preliminary Hourly Load"),
        }

        load_choice, load_name = load_map[load_type]

        start_date, duration = get_date_input()

        config = PJMConfig.from_ini_file()
        client = PJMClient(config)

        try:
            print(f"\n📥 Downloading {load_name}...")
            success = client.get_hourly_load(load_choice, start_date, duration)

            if success:
                print("\n✅ Download complete!")
                print(f"   Data saved to: data/PJM/")
            else:
                print("\n❌ Download failed. Check logs for details.")
        except Exception as e:
            logger.error(f"Error downloading data: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
        finally:
            client.cleanup()


def run_pjm_renewable():
    """PJM renewable generation data selection."""
    from lib.iso.pjm import PJMClient, PJMConfig

    print("\n" + "=" * 60)
    print("PJM RENEWABLE GENERATION")
    print("=" * 60)

    print("\nWhat type of renewable generation?")
    print("  (1) Solar Generation")
    print("  (2) Wind Generation")

    while True:
        try:
            renewable_type = int(input("\nYour choice (1-2): "))
            if renewable_type in [1, 2]:
                break
        except ValueError:
            pass
        print("Please enter 1 or 2")

    renewable_map = {
        1: ("solar", "Solar Generation"),
        2: ("wind", "Wind Generation"),
    }

    renewable_choice, renewable_name = renewable_map[renewable_type]

    start_date, duration = get_date_input()

    config = PJMConfig.from_ini_file()
    client = PJMClient(config)

    try:
        print(f"\n📥 Downloading {renewable_name}...")
        success = client.get_renewable_generation(renewable_choice, start_date, duration)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/PJM/")
        else:
            print("\n❌ Download failed. Check logs for details.")
    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
    finally:
        client.cleanup()


def run_pjm_ancillary():
    """PJM ancillary services data selection."""
    from lib.iso.pjm import PJMClient, PJMConfig

    print("\n" + "=" * 60)
    print("PJM ANCILLARY SERVICES")
    print("=" * 60)

    print("\nWhat type of ancillary services data?")
    print("  (1) Hourly LMPs")
    print("  (2) Five Minute LMPs")
    print("  (3) Reserve Market Results")

    while True:
        try:
            as_type = int(input("\nYour choice (1-3): "))
            if as_type in range(1, 4):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 3")

    as_map = {
        1: ("hourly", "Hourly Ancillary Services LMPs"),
        2: ("5min", "Five Minute Ancillary Services LMPs"),
        3: ("reserve_market", "Reserve Market Results"),
    }

    as_choice, as_name = as_map[as_type]

    start_date, duration = get_date_input()

    config = PJMConfig.from_ini_file()
    client = PJMClient(config)

    try:
        print(f"\n📥 Downloading {as_name}...")
        success = client.get_ancillary_services(as_choice, start_date, duration)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/PJM/")
        else:
            print("\n❌ Download failed. Check logs for details.")
    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
    finally:
        client.cleanup()


def run_pjm_outages():
    """PJM outages and transfer limits data selection."""
    from lib.iso.pjm import PJMClient, PJMConfig

    print("\n" + "=" * 60)
    print("PJM OUTAGES AND TRANSFER LIMITS")
    print("=" * 60)

    print("\nWhich one?")
    print("  (1) Generation Outage for Seven Days by Type")
    print("  (2) RTO Transfer Limit and Flows")

    while True:
        try:
            data_type = int(input("\nYour choice (1-2): "))
            if data_type in [1, 2]:
                break
        except ValueError:
            pass
        print("Please enter 1 or 2")

    data_map = {
        1: ("outages", "Generation Outages by Type"),
        2: ("transfer_limits", "RTO Transfer Limits and Flows"),
    }

    data_choice, data_name = data_map[data_type]

    start_date, duration = get_date_input()

    config = PJMConfig.from_ini_file()
    client = PJMClient(config)

    try:
        print(f"\n📥 Downloading {data_name}...")
        success = client.get_outages_and_limits(data_choice, start_date, duration)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/PJM/")
        else:
            print("\n❌ Download failed. Check logs for details.")
    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
    finally:
        client.cleanup()


# ============================================================================
# ISO-NE MODE
# ============================================================================


def run_isone_mode():
    """Interactive mode for ISO-NE data."""
    from lib.iso.isone import ISONEClient

    print("\n" + "=" * 60)
    print("ISO-NE DATA SELECTION")
    print("=" * 60)

    print("\nWhat type of data?")
    print("  (1) Locational Marginal Prices (LMP)")
    print("  (2) Ancillary Services")
    print("  (3) Demand/Load Data")
    print("  (4) Transmission Outages")
    print("  (5) Annual Maintenance Schedule (AMS)")

    while True:
        try:
            data_type = int(input("\nYour choice (1-5): "))
            if data_type in range(1, 6):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 5")

    if data_type == 1:
        run_isone_lmp()
    elif data_type == 2:
        run_isone_ancillary()
    elif data_type == 3:
        run_isone_demand()
    elif data_type == 4:
        run_isone_outage()
    else:
        run_isone_ams()


def run_isone_lmp():
    """ISO-NE LMP data selection (updated for new ISONEClient)."""
    from lib.iso.isone import ISONEClient

    print("\n" + "=" * 60)
    print("ISO-NE LOCATIONAL MARGINAL PRICES")
    print("=" * 60)

    print("\nWhat type of LMP?")
    print("  (1) Day-Ahead Hourly LMPs (REST)")
    print("  (2) Real-Time Five-Minute LMPs (REST)")

    while True:
        try:
            lmp_type = int(input("\nYour choice (1-2): "))
            if lmp_type in [1, 2]:
                break
        except ValueError:
            pass
        print("Please enter 1 or 2")

    start_date, duration = get_date_input()
    end_excl = start_date + timedelta(days=duration)

    client = ISONEClient()

    def _yyyymmdd(d: date) -> str:
        return d.strftime("%Y%m%d")

    def _download_fivemin_lmp(location_id=None):
        out_paths = []
        for i in range(duration):
            d = start_date + timedelta(days=i)
            day_str = _yyyymmdd(d)
            loc = int(location_id) if location_id is not None else 4000  # ISO-NE Internal Hub
            path = f"fiveminutelmp/day/{day_str}/location/{loc}"
            payload = client._request_json(path, authenticated=True)
            suffix = f"_loc{int(location_id)}" if location_id is not None else ""
            out_path = client.config.data_dir / f"fiveminutelmp_{day_str}{suffix}.json"
            client._save_json(payload, out_path)
            out_paths.append(out_path)
        return out_paths

    try:
        if lmp_type == 1:
            print("\n📥 Downloading Day-Ahead Hourly LMPs (REST)...")
            print(f"   Date range: {start_date} to {end_excl}")
            print("   This may take a moment...\n")

            paths = client.get_hourly_lmp(start_date, end_excl, market="da", report="final")
            success = bool(paths)

        else:  # lmp_type == 2
            print("\n📥 Downloading Real-Time 5-Minute LMPs (REST)...")
            print(f"   Date range: {start_date} to {end_excl}")
            loc = input("   Optional: location id (press Enter for ALL locations): ").strip()
            location_id = int(loc) if loc else None
            print("   This may take a bit (large payloads if ALL locations)...\n")

            paths = _download_fivemin_lmp(location_id=location_id)
            success = bool(paths)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: {client.config.data_dir}/")
        else:
            print("\n❌ Download failed. Check logs for details.")

    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


def run_isone_ancillary():
    """ISO-NE ancillary services data selection (updated for new ISONEClient)."""
    from lib.iso.isone import ISONEClient

    print("\n" + "=" * 60)
    print("ISO-NE ANCILLARY SERVICES")
    print("=" * 60)

    print("\nWhat type of ancillary services data?")
    print("  (1) Five-Minute Regulation Clearing Prices (Final) (REST)")
    print("  (2) Hourly Regulation Clearing Prices (Final) (REST)")
    print("  (3) Real-Time Hourly Operating Reserve (REST)")
    print("  (4) Day-Ahead Hourly Operating Reserve (REST)")

    while True:
        try:
            anc_type = int(input("\nYour choice (1-4): "))
            if anc_type in [1, 2, 3, 4]:
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 4")

    start_date, duration = get_date_input()
    end_excl = start_date + timedelta(days=duration)

    client = ISONEClient()

    def _yyyymmdd(d: date) -> str:
        return d.strftime("%Y%m%d")

    def _download_hourly_rcp_final():
        out_paths = []
        for i in range(duration):
            d = start_date + timedelta(days=i)
            day_str = _yyyymmdd(d)
            path = f"hourlyrcp/final/day/{day_str}"
            payload = client._request_json(path, authenticated=True)
            out_path = client.config.data_dir / f"hourlyrcp_final_{day_str}.json"
            client._save_json(payload, out_path)
            out_paths.append(out_path)
        return out_paths

    try:
        if anc_type == 1:
            print("\n📥 Downloading 5-Minute Regulation Clearing Prices (Final)...")
            paths = client.get_5min_regulation_prices(start_date, end_excl)
            success = bool(paths)

        elif anc_type == 2:
            print("\n📥 Downloading Hourly Regulation Clearing Prices (Final)...")
            paths = _download_hourly_rcp_final()
            success = bool(paths)

        elif anc_type == 3:
            loc = input(
                "   Location id for Operating Reserve (default 7000 = REST OF SYSTEM): "
            ).strip()
            location_id = int(loc) if loc else 7000
            print(
                f"\n📥 Downloading Real-Time Hourly Operating Reserve (location {location_id})..."
            )
            paths = client.get_real_time_hourly_operating_reserve(
                start_date, end_excl, location_id=location_id
            )
            success = bool(paths)

        else:  # anc_type == 4
            loc = input(
                "   Location id for Operating Reserve (default 7000 = REST OF SYSTEM): "
            ).strip()
            location_id = int(loc) if loc else 7000
            print(
                f"\n📥 Downloading Day-Ahead Hourly Operating Reserve (location {location_id})..."
            )
            paths = client.get_day_ahead_hourly_operating_reserve(
                start_date, end_excl, location_id=location_id
            )
            success = bool(paths)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: {client.config.data_dir}/")
        else:
            print("\n❌ Download failed. Check logs for details.")

    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


def run_isone_demand():
    """ISO-NE demand/load data selection (updated for new ISONEClient)."""
    from lib.iso.isone import ISONEClient

    print("\n" + "=" * 60)
    print("ISO-NE DEMAND / LOAD DATA")
    print("=" * 60)

    print("\nWhat type of demand data?")
    print("  (1) Five-Minute System Demand (REST)")
    print("  (2) Day-Ahead Hourly Demand (REST)")

    while True:
        try:
            demand_type = int(input("\nYour choice (1-2): "))
            if demand_type in [1, 2]:
                break
        except ValueError:
            pass
        print("Please enter 1 or 2")

    start_date, duration = get_date_input()
    end_excl = start_date + timedelta(days=duration)

    client = ISONEClient()

    try:
        if demand_type == 1:
            print("\n📥 Downloading 5-Minute System Demand...")
            paths = client.get_5min_system_demand(start_date, end_excl)
            success = bool(paths)
        else:
            print("\n📥 Downloading Day-Ahead Hourly Demand...")
            paths = client.get_day_ahead_hourly_demand(start_date, end_excl)
            success = bool(paths)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: {client.config.data_dir}/")
        else:
            print("\n❌ Download failed. Check logs for details.")

    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


def run_isone_outage():
    """ISO-NE transmission outages data selection (updated for new ISONEClient)."""
    from lib.iso.isone import ISONEClient

    print("\n" + "=" * 60)
    print("ISO-NE TRANSMISSION OUTAGES DATA")
    print("=" * 60)

    print("\nWhat type of transmission outage data?")
    print("  (1) Short-Term")
    print("  (2) Long-Term")

    while True:
        try:
            outage_type = int(input("\nYour choice (1-2): "))
            if outage_type in [1, 2]:
                break
        except ValueError:
            pass
        print("Please enter 1 or 2")

    start_date, duration = get_date_input()
    end_excl = start_date + timedelta(days=duration)

    client = ISONEClient()

    try:
        if outage_type == 1:
            print("\n📥 Downloading short-term transmission outage data...")
            paths = client.get_transmission_outages(start_date, end_excl, outage_type="short-term")
            success = bool(paths)
        else:
            print("\n📥 Downloading long-term transmission outage data...")
            paths = client.get_transmission_outages(start_date, end_excl, outage_type="long-term")
            success = bool(paths)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: {client.config.data_dir}/")
        else:
            print("\n❌ Download failed. Check logs for details.")

    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


def run_isone_ams():
    """ISO-NE annual maintenance schedule (AMS) data selection (updated for new ISONEClient)."""
    from lib.iso.isone import ISONEClient

    print("\n" + "=" * 60)
    print("ISO-NE ANNUAL MAINTENANCE SCHEDULE (AMS) DATA")
    print("=" * 60)

    start_date, duration = get_date_input()
    end_excl = start_date + timedelta(days=duration)

    client = ISONEClient()

    try:
        print("\n📥 Downloading Annual Maintenance Schedule (AMS) data...")
        paths = client.get_annual_maintenance_schedule(start_date, end_excl)
        success = bool(paths)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: {client.config.data_dir}/")
        else:
            print("\n❌ Download failed. Check logs for details.")

    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


# ============================================================================
# WEATHER MODE
# ============================================================================


def run_weather_mode():
    """Interactive mode for weather data."""
    from lib.weather.client import WeatherClient

    print("\n" + "=" * 60)
    print("WEATHER DATA SELECTION")
    print("=" * 60)

    # Get date range
    start_date, duration = get_date_input()

    # Get location
    print("\n" + "=" * 60)
    print("LOCATION SELECTION")
    print("=" * 60)

    us_states = [
        "AL",
        "AK",
        "AZ",
        "AR",
        "CA",
        "CO",
        "CT",
        "DC",
        "DE",
        "FL",
        "GA",
        "HI",
        "ID",
        "IL",
        "IN",
        "IA",
        "KS",
        "KY",
        "LA",
        "ME",
        "MD",
        "MA",
        "MI",
        "MN",
        "MS",
        "MO",
        "MT",
        "NE",
        "NV",
        "NH",
        "NJ",
        "NM",
        "NY",
        "NC",
        "ND",
        "OH",
        "OK",
        "OR",
        "PA",
        "RI",
        "SC",
        "SD",
        "TN",
        "TX",
        "UT",
        "VT",
        "VA",
        "WA",
        "WV",
        "WI",
        "WY",
    ]

    while True:
        state = input("\nUS State (2-letter code, e.g., CA): ").upper().strip()
        if state in us_states:
            break
        print(f"Invalid state code. Please use one of: {', '.join(us_states[:10])}...")

    print(f"\n📥 Finding weather stations in {state}...")

    client = WeatherClient()
    try:
        success = client.download_weather_data(
            state=state, start_date=start_date, duration=duration
        )

        if success:
            print("\n✅ Weather data download complete!")
            print(f"   Data saved to: data/weather/")

            # Ask about solar data
            solar = input("\n☀️  Download solar data from NSRDB? (y/n): ").lower()
            if solar == "y":
                client.download_solar_data()
        else:
            print("\n❌ Weather data download failed.")

    except Exception as e:
        logger.error(f"Error downloading weather data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
