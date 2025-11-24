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
    print("  (1) ISO Data (CAISO, MISO, NYISO, SPP, BPA)")
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

    while True:
        try:
            iso_choice = int(input("\nYour choice (1-5): "))
            if iso_choice in range(1, 6):
                break
            print("Please enter 1, 2, 3, 4, or 5")
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
    else:
        run_bpa_mode()

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
    from lib.iso.miso import MISOClient

    print("\n" + "=" * 60)
    print("MISO DATA SELECTION")
    print("=" * 60)

    print("\nWhat type of data?")
    print("  (1) Historical Locational Marginal Prices (LMP)")
    print("  (2) Historical Marginal Clearing Prices (MCP)")
    print("  (3) Summary Reports")
    print("  (4) Fuel Mix")
    print("  (5) Area Control Error (ACE)")
    print("  (6) Wind Generation")
    print("  (7) Market Totals")

    while True:
        try:
            data_type = int(input("\nYour choice (1-7): "))
            if data_type in range(1, 8):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 7")

    if data_type == 1:
        run_miso_lmp()
    elif data_type == 2:
        run_miso_mcp()
    elif data_type == 3:
        run_miso_summary()
    elif data_type == 4:
        run_miso_fuel_mix()
    elif data_type == 5:
        run_miso_ace()
    elif data_type == 6:
        run_miso_wind()
    else:
        run_miso_market_totals()


def run_miso_lmp():
    """MISO LMP data selection."""
    from lib.iso.miso import MISOClient

    print("\n" + "=" * 60)
    print("MISO LMP DATA")
    print("=" * 60)

    print("\nWhat type of LMP?")
    print("  (1) Day-Ahead EPNode LMPs")
    print("  (2) Day-Ahead Market ExAnte LMPs")
    print("  (3) Day-Ahead Market ExPost LMPs")
    print("  (4) Real-Time EPNode LMPs")
    print("  (5) Real-Time 5-min ExAnte LMPs")
    print("  (6) Real-Time Final Market LMPs")

    while True:
        try:
            lmp_type = int(input("\nYour choice (1-6): "))
            if lmp_type in range(1, 7):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 6")

    lmp_map = {
        1: "da_epnodes",
        2: "da_exante",
        3: "da_expost",
        4: "rt_epnodes",
        5: "rt_5min_exante",
        6: "rt_final",
    }

    lmp_choice = lmp_map[lmp_type]

    start_date, duration = get_date_input()

    client = MISOClient()
    try:
        print(f"\n📥 Downloading MISO {lmp_choice.upper()} LMP data...")
        success = client.get_lmp(lmp_choice, start_date, duration)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/MISO/")
        else:
            print("\n❌ Download failed. Check logs for details.")
    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


def run_miso_mcp():
    """MISO MCP data selection."""
    from lib.iso.miso import MISOClient

    print("\n" + "=" * 60)
    print("MISO MCP DATA")
    print("=" * 60)

    print("\nWhat type of MCP?")
    print("  (1) ASM Day-Ahead Market ExAnte MCPs")
    print("  (2) ASM Day-Ahead Market ExPost MCPs")
    print("  (3) ASM Real-Time 5-min ExAnte MCPs")
    print("  (4) ASM Real-Time Final Market MCPs")
    print("  (5) Day-Ahead ExAnte Ramp MCPs")
    print("  (6) Day-Ahead ExPost Ramp MCPs")

    while True:
        try:
            mcp_type = int(input("\nYour choice (1-6): "))
            if mcp_type in range(1, 7):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 6")

    mcp_map = {
        1: "asm_da_exante",
        2: "asm_da_expost",
        3: "asm_rt_5min_exante",
        4: "asm_rt_final",
        5: "da_exante_ramp",
        6: "da_expost_ramp",
    }

    mcp_choice = mcp_map[mcp_type]

    start_date, duration = get_date_input()

    client = MISOClient()
    try:
        print(f"\n📥 Downloading MISO {mcp_choice.upper()} MCP data...")
        success = client.get_mcp(mcp_choice, start_date, duration)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/MISO/")
        else:
            print("\n❌ Download failed. Check logs for details.")
    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


def run_miso_summary():
    """MISO summary data selection."""
    from lib.iso.miso import MISOClient

    print("\n" + "=" * 60)
    print("MISO SUMMARY REPORTS")
    print("=" * 60)

    print("\nWhat type of summary?")
    print("  (1) Daily Forecast and Actual Load by Local Resource Zone")
    print("  (2) Daily Regional Forecast and Actual Load")

    while True:
        try:
            summary_type = int(input("\nYour choice (1-2): "))
            if summary_type in [1, 2]:
                break
        except ValueError:
            pass
        print("Please enter 1 or 2")

    summary_map = {1: "daily_forecast_actual", 2: "regional_forecast_actual"}

    summary_choice = summary_map[summary_type]

    start_date, duration = get_date_input()

    client = MISOClient()
    try:
        print(f"\n📥 Downloading MISO Load Summary...")
        success = client.get_load_summary(summary_choice, start_date, duration)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/MISO/")
        else:
            print("\n❌ Download failed. Check logs for details.")
    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


def run_miso_fuel_mix():
    """MISO fuel mix data selection."""
    from lib.iso.miso import MISOClient

    print("\n" + "=" * 60)
    print("MISO FUEL MIX DATA")
    print("=" * 60)

    start_date, duration = get_date_input()

    client = MISOClient()
    try:
        print(f"\n📥 Downloading MISO Fuel Mix data...")
        success = client.get_fuel_mix(start_date, duration)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/MISO/")
        else:
            print("\n❌ Download failed. Check logs for details.")
    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


def run_miso_ace():
    """MISO ACE data selection."""
    from lib.iso.miso import MISOClient

    print("\n" + "=" * 60)
    print("MISO AREA CONTROL ERROR (ACE) DATA")
    print("=" * 60)

    start_date, duration = get_date_input()

    client = MISOClient()
    try:
        print(f"\n📥 Downloading MISO ACE data...")
        success = client.get_ace(start_date, duration)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/MISO/")
        else:
            print("\n❌ Download failed. Check logs for details.")
    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


def run_miso_wind():
    """MISO wind generation data selection."""
    from lib.iso.miso import MISOClient

    print("\n" + "=" * 60)
    print("MISO WIND GENERATION DATA")
    print("=" * 60)

    print("\nWhat type of wind data?")
    print("  (1) Wind Generation Forecast")
    print("  (2) Actual Wind Generation")

    while True:
        try:
            wind_type = int(input("\nYour choice (1-2): "))
            if wind_type in [1, 2]:
                break
        except ValueError:
            pass
        print("Please enter 1 or 2")

    start_date, duration = get_date_input()

    client = MISOClient()
    try:
        if wind_type == 1:
            print(f"\n📥 Downloading MISO Wind Forecast...")
            success = client.get_wind_forecast(start_date, duration)
        else:
            print(f"\n📥 Downloading MISO Actual Wind Generation...")
            success = client.get_wind_actual(start_date, duration)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/MISO/")
        else:
            print("\n❌ Download failed. Check logs for details.")
    except Exception as e:
        logger.error(f"Error downloading data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


def run_miso_market_totals():
    """MISO market totals data selection."""
    from lib.iso.miso import MISOClient

    print("\n" + "=" * 60)
    print("MISO MARKET TOTALS DATA")
    print("=" * 60)

    start_date, duration = get_date_input()

    client = MISOClient()
    try:
        print(f"\n📥 Downloading MISO Day-Ahead Market Totals...")
        success = client.get_market_totals(start_date, duration)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/MISO/")
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

    print("\nWhat type of data?")
    print("  (1) Pricing Data")
    print("  (2) Power Grid Data")
    print("  (3) Load Data")
    print("  (4) Bid Data")
    print("  (5) Fuel Mix")
    print("  (6) Interface Flows")
    print("  (7) Wind Generation")
    print("  (8) BTM Solar Generation")

    while True:
        try:
            data_type = int(input("\nYour choice (1-8): "))
            if data_type in range(1, 9):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 8")

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
    elif data_type == 7:
        run_nyiso_wind()
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
    print("  (1) Outages")
    print("  (2) Constraints")

    while True:
        try:
            grid_type = int(input("\nYour choice (1-2): "))
            if grid_type in [1, 2]:
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

    if grid_type == 1:  # Outages
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
    """Interactive mode for BPA data."""
    from lib.iso.bpa import BPAClient, get_bpa_data_availability
    from datetime import date, timedelta

    print("\n" + "=" * 60)
    print("BPA DATA SELECTION")
    print("=" * 60)

    # Show data availability info
    info = get_bpa_data_availability()

    print("\n⚠️  IMPORTANT: BPA Data Limitations")
    print("=" * 60)
    print(f"• Temporal Coverage: {info['temporal_coverage']}")
    print(f"• Temporal Resolution: {info['temporal_resolution']}")
    print(f"• Update Frequency: {info['update_frequency']}")
    print(f"• Geographic Coverage: {info['geographic_coverage']}")
    print("\n⚠️  BPA only provides real-time data for the LAST 7 DAYS.")
    print("   Historical data beyond 7 days is NOT available.")
    print("=" * 60)

    # Data type selection
    print("\nWhat type of BPA data?")
    print("  (1) Load and Generation (all sources)")
    print("      - Load, VER, Hydro, Fossil/Biomass, Nuclear")
    print("  (2) Wind and Solar Generation (detailed)")
    print("      - Wind, Solar breakdown")
    print("  (3) All Data (both of above)")

    while True:
        try:
            data_type = int(input("\nYour choice (1-3): "))
            if data_type in range(1, 4):
                break
        except ValueError:
            pass
        print("Please enter a number between 1 and 3")

    # Date filtering (optional)
    print("\n" + "=" * 60)
    print("DATE FILTERING (OPTIONAL)")
    print("=" * 60)
    print("BPA data includes the last 7 days automatically.")
    print("You can optionally filter to a specific date range.")

    filter_dates = input("\nFilter by specific dates? (y/n): ").lower()

    start_date = None
    end_date = None

    if filter_dates == 'y':
        print("\nEnter date range (must be within last 7 days):")
        print("Note: BPA data is in Pacific Time")

        # Get start date
        while True:
            try:
                year = int(input("  Start Year (4-digit): "))
                month = int(input("  Start Month (1-12): "))
                day = int(input("  Start Day (1-31): "))
                start_date = date(year, month, day)

                # Check if within last 7 days
                today = date.today()
                seven_days_ago = today - timedelta(days=7)

                if start_date < seven_days_ago:
                    print(f"\n⚠️  Warning: Date is older than 7 days ago.")
                    print(f"   BPA may not have data before {seven_days_ago}")
                    confirm = input("   Continue anyway? (y/n): ")
                    if confirm.lower() != 'y':
                        continue

                if start_date > today:
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
                year = int(input("\n  End Year (4-digit): "))
                month = int(input("  End Month (1-12): "))
                day = int(input("  End Day (1-31): "))
                end_date = date(year, month, day)

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
        print("\n✓ Will download all available data (last 7 days)")

    # Download data
    print("\n" + "=" * 60)
    print("DOWNLOADING DATA")
    print("=" * 60)
    print("\nThis may take a moment...")

    client = BPAClient()

    try:
        if data_type == 1:
            print("\n📥 Downloading Load and Generation data...")
            print("   (Load, VER, Hydro, Fossil/Biomass, Nuclear)")
            success = client.get_load_and_generation(start_date, end_date)

        elif data_type == 2:
            print("\n📥 Downloading Wind and Solar generation data...")
            success = client.get_wind_solar_generation(start_date, end_date)

        else:  # data_type == 3
            print("\n📥 Downloading all BPA data...")
            print("   (1) Load and Generation")
            print("   (2) Wind and Solar")
            success = client.get_all_data(start_date, end_date)

        if success:
            print("\n✅ Download complete!")
            print(f"   Data saved to: data/BPA/")
            print("\n📊 Data Details:")
            print(f"   • Resolution: {info['temporal_resolution']}")
            print(f"   • Coverage: {info['temporal_coverage']}")
            print(f"   • Time Zone: Pacific Time")

            # Show what data types were downloaded
            print("\n📁 Files Created:")
            if data_type == 1:
                print("   • [date]_BPA_Load_and_Generation.csv")
            elif data_type == 2:
                print("   • [date]_BPA_Wind_Solar_Generation.csv")
            else:
                print("   • [date]_BPA_Load_and_Generation.csv")
                print("   • [date]_BPA_Wind_Solar_Generation.csv")

            print("\n💡 Tip: BPA data updates every 5 minutes.")
            print("   Run this again to get the latest data!")

        else:
            print("\n❌ Download failed. Check logs for details.")
            print("   Common issues:")
            print("   • Network connection problems")
            print("   • BPA website temporarily unavailable")
            print("   • Requested dates outside 7-day window")

    except Exception as e:
        logger.error(f"Error downloading BPA data: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        print("   Check logs/isodart.log for details")

    finally:
        client.cleanup()


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
