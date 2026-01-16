"""
ISO-DART v2.0: Independent System Operator Data Automated Request Tool

Main entry point for the application.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_directories():
    """Create necessary directories if they don't exist."""
    dirs = [
        Path("data/CAISO"),
        Path("data/MISO"),
        Path("data/NYISO"),
        Path("data/BPA"),
        Path("data/SPP"),
        Path("data/PJM"),
        Path("data/ISONE"),
        Path("data/weather"),
        Path("data/solar"),
        Path("raw_data/xml_files"),
        Path("logs"),
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    logger.info("Directory structure verified")


def validate_date(date_string: str) -> date:
    """Validate and parse date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_string, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_string}. Use YYYY-MM-DD")


def calculate_end_date(start_date: date, duration: int) -> date:
    """Calculate end date from start date and duration."""
    return start_date + timedelta(days=duration)


def handle_caiso(args):
    """Handle CAISO-specific data download logic."""
    from lib.iso.caiso import CAISOClient, Market

    logger.info(f"Processing CAISO data request: {args.data_type}")

    client = CAISOClient()
    success = False

    try:
        end_date = calculate_end_date(args.start, args.duration)

        # Map string market to enum
        market_map = {
            "dam": Market.DAM,
            "rtm": Market.RTM,
            "hasp": Market.HASP,
            "rtpd": Market.RTPD,
            "ruc": Market.RUC,
        }

        if args.data_type == "lmp":
            if not args.market:
                logger.error("Market type required for LMP data")
                return False

            market = market_map.get(args.market.lower())
            if not market:
                logger.error(f"Invalid market: {args.market}")
                return False

            logger.info(f"Downloading {market.value} LMP data...")
            success = client.get_lmp(market, args.start, end_date)

        elif args.data_type == "load-forecast":
            if not args.market:
                logger.error("Market type required for load forecast data")
                return False

            market = market_map.get(args.market.lower())
            if market not in [Market.DAM, Market.RTM]:
                logger.error(f"Invalid market for load forecast: {args.market}")
                return False

            logger.info(f"Downloading {market.value} load forecast...")
            success = client.get_load_forecast(market, args.start, end_date)

        elif args.data_type == "system-load":
            if not args.market:
                logger.error("Market type required for system load data")
                return False

            market = market_map.get(args.market.lower())
            if market not in [Market.DAM, Market.RTM, Market.RUC, Market.HASP]:
                logger.error(f"Invalid market for system load: {args.market}")
                return False

            logger.info(f"Downloading {market.value} system load...")
            success = client.get_system_load(market, args.start, end_date)

        elif args.data_type == "wind-solar":
            logger.info("Downloading wind and solar summary...")
            success = client.get_wind_solar_summary(args.start, end_date)

        elif args.data_type == "fuel-prices":
            logger.info("Downloading fuel prices...")
            success = client.get_fuel_prices(args.start, end_date)

        elif args.data_type == "ghg-prices":
            logger.info("Downloading GHG allowance prices...")
            success = client.get_ghg_allowance_prices(args.start, end_date)

        elif args.data_type == "as-prices":
            if not args.market:
                logger.error("Market type required for AS prices")
                return False

            market = market_map.get(args.market.lower())
            if market not in [Market.DAM, Market.RTM]:
                logger.error(f"Invalid market for AS prices: {args.market}")
                return False

            logger.info(f"Downloading {market.value} AS prices...")
            success = client.get_ancillary_services_prices(market, args.start, end_date)

        elif args.data_type == "as-requirements":
            if not args.market:
                logger.error("Market type required for AS requirements")
                return False

            market = market_map.get(args.market.lower())
            if market not in [Market.DAM, Market.HASP, Market.RTM]:
                logger.error(f"Invalid market for AS requirements: {args.market}")
                return False

            logger.info(f"Downloading {market.value} AS requirements...")
            success = client.get_ancillary_services_requirements(market, args.start, end_date)

        elif args.data_type == "as-results":
            if not args.market:
                logger.error("Market type required for AS results")
                return False

            market = market_map.get(args.market.lower())
            if market not in [Market.DAM, Market.HASP, Market.RTM]:
                logger.error(f"Invalid market for AS results: {args.market}")
                return False

            logger.info(f"Downloading {market.value} AS results...")
            success = client.get_ancillary_services_results(market, args.start, end_date)

        elif args.data_type == "curtailed-nonop":
            kind = getattr(args, "caiso_report_kind", "both")
            logger.info(
                f"Downloading CAISO curtailed/non-operational generator reports (kind={kind})..."
            )
            success = client.get_curtailed_non_operational_reports(args.start, end_date, kind=kind)

        elif args.data_type == "intertie-prices":
            logger.info("Downloading intertie constraint shadow prices...")
            success = client.get_intertie_constraint_shadow_prices(args.start, end_date)

        elif args.data_type == "mpm-status":
            if not args.market:
                logger.error("Market type required for MPM status")
                return False

            market = market_map.get(args.market.lower())
            if market not in [Market.DAM, Market.HASP, Market.RTPD]:
                logger.error(f"Invalid market for MPM status: {args.market}")
                return False
            logger.info("Downloading Market Power Mitigation (MPM) Status...")
            success = client.get_market_power_mitigation(market, args.start, end_date)

        elif args.data_type == "flex-ramp-req":
            logger.info("Downloading Flexible Ramping Requirements...")
            success = client.get_flex_ramp_requirements(args.start, end_date)

        elif args.data_type == "flex-ramp-awards":
            logger.info("Downloading Flexible Ramping Aggregated Awards...")
            success = client.get_flex_ramp_awards(args.start, end_date)

        elif args.data_type == "flex-ramp-curves":
            logger.info("Downloading Flexible Ramping Demand Curves...")
            success = client.get_flex_ramp_demand_curve(args.start, end_date)

        elif args.data_type == "eim-transfer":
            logger.info("Downloading Energy Imbalance Market (EIM) Transfer data...")
            success = client.get_eim_transfer(args.start, end_date)

        elif args.data_type == "eim-transfer-limits":
            logger.info("Downloading Energy Imbalance Market (EIM) Transfer Limits...")
            success = client.get_eim_transfer_limits(args.start, end_date)

        elif args.data_type == "operating-reserves":
            logger.info("Downloading Actual Operating Reserves...")
            success = client.get_operating_reserves(args.start, end_date)

        elif args.data_type == "point-tie-prices":
            if not args.market:
                logger.error("Market type required for Scheduling Point Tie Prices")
                return False

            market = market_map.get(args.market.lower())
            if market not in [Market.DAM, Market.RTPD]:
                logger.error(f"Invalid market for Scheduling Point Tie Prices: {args.market}")
                return False
            logger.info("Downloading Scheduling Point Tie Prices...")
            success = client.get_scheduling_point_tie_prices(market, args.start, end_date)

        elif args.data_type == "advisory-demand-forecast":
            logger.info("Downloading Advisory Demand Forecast...")
            success = client.get_advisory_demand_forecast(args.start, end_date)

        else:
            logger.error(f"Unknown CAISO data type: {args.data_type}")
            logger.info(
                "Available types: lmp, load-forecast, system-load, wind-solar, fuel-prices, ghg-prices, as-prices, "
                "as-requirements, curtailed-nonop, intertie-prices, mpm-status, flex-ramp-req,"
                "flex-ramp-awards, flex-ramp-curves, eim-transfer, eim-transfer-limits,"
                "operating-reserves, point-tie-prices, advisory-demand-forecast"
            )
            return False

        if success:
            logger.info(f"✅ CAISO data downloaded successfully to data/CAISO/")
        else:
            logger.error("❌ CAISO data download failed")

        return success

    except Exception as e:
        logger.error(f"Error downloading CAISO data: {e}", exc_info=True)
        return False

    finally:
        client.cleanup()


def handle_miso(args):
    """Handle MISO-specific data download logic."""
    from lib.iso.miso import MISOConfig, MISOClient

    logger.info(f"Processing MISO data request: {args.data_type}")

    config = MISOConfig.from_ini_file()
    client = MISOClient(config)

    try:
        data = None
        filename = None

        if args.data_type == "lmp":
            # LMP types: da_exante, da_expost, rt_exante, rt_expost
            lmp_type = getattr(args, "lmp_type", "da_exante")
            logger.info(f"Downloading MISO {lmp_type} LMP data...")

            data = client.get_lmp(lmp_type=lmp_type, start_date=args.start, duration=args.duration)
            filename = f"miso_{lmp_type}_lmp_{args.start}.csv"

        elif args.data_type == "mcp":
            # MCP types: asm_da_exante, asm_da_expost, asm_rt_exante, asm_rt_expost, asm_rt_summary
            mcp_type = getattr(args, "mcp_type", "asm_da_exante")
            logger.info(f"Downloading MISO {mcp_type} MCP data...")

            data = client.get_mcp(mcp_type=mcp_type, start_date=args.start, duration=args.duration)
            filename = f"miso_{mcp_type}_mcp_{args.start}.csv"

        elif args.data_type == "load":
            # Load types: da_demand, rt_forecast, rt_actual, rt_state_estimator
            load_type = getattr(args, "load_type", "rt_actual")
            logger.info(f"Downloading MISO {load_type} load data...")

            data = client.get_demand(
                demand_type=load_type,
                start_date=args.start,
                duration=args.duration,
                time_resolution="daily",
            )
            filename = f"miso_{load_type}_load_{args.start}.csv"

        elif args.data_type == "load-forecast":
            logger.info("Downloading MISO medium-term load forecast...")

            data = client.get_load_forecast(
                start_date=args.start, duration=args.duration, time_resolution="daily"
            )
            filename = f"miso_load_forecast_{args.start}.csv"

        elif args.data_type == "fuel-mix":
            logger.info("Downloading MISO fuel on the margin...")

            data = client.get_fuel_mix(start_date=args.start, duration=args.duration)
            filename = f"miso_fuel_mix_{args.start}.csv"

        elif args.data_type == "generation":
            # Generation types: da_cleared_physical, da_cleared_virtual, da_fuel_type,
            # da_offered_ecomax, da_offered_ecomin, rt_cleared, rt_committed_ecomax,
            # rt_fuel_margin, rt_fuel_type, rt_offered_ecomax
            gen_type = getattr(args, "gen_type", "rt_fuel_type")
            logger.info(f"Downloading MISO {gen_type} generation data...")

            data = client.get_generation(
                gen_type=gen_type, start_date=args.start, duration=args.duration
            )
            filename = f"miso_{gen_type}_generation_{args.start}.csv"

        elif args.data_type == "interchange":
            # Interchange types: da_net_scheduled, rt_net_actual, rt_net_scheduled, historical
            interchange_type = getattr(args, "interchange_type", "rt_net_actual")
            logger.info(f"Downloading MISO {interchange_type} interchange data...")

            data = client.get_interchange(
                interchange_type=interchange_type, start_date=args.start, duration=args.duration
            )
            filename = f"miso_{interchange_type}_interchange_{args.start}.csv"

        elif args.data_type == "outages":
            # Outage types: forecast, rt_outage
            outage_type = getattr(args, "outage_type", "rt_outage")
            logger.info(f"Downloading MISO {outage_type} data...")

            data = client.get_outages(
                outage_type=outage_type, start_date=args.start, duration=args.duration
            )
            filename = f"miso_{outage_type}_{args.start}.csv"

        elif args.data_type == "binding-constraints":
            logger.info("Downloading MISO binding constraints...")

            data = client.get_binding_constraints(start_date=args.start, duration=args.duration)
            filename = f"miso_binding_constraints_{args.start}.csv"

        else:
            logger.error(f"Unknown MISO data type: {args.data_type}")
            logger.info(
                "Available types: lmp, mcp, load, load-forecast, fuel-mix, generation, "
                "interchange, outages, binding-constraints"
            )
            return False

        # Save data if we got any
        if data:
            client.save_to_csv(data, filename)
            logger.info(f"✅ MISO data downloaded successfully to data/MISO/{filename}")
            return True
        else:
            logger.error("❌ MISO data download failed - no data returned")
            return False

    except Exception as e:
        logger.error(f"Error downloading MISO data: {e}", exc_info=True)
        return False


def handle_nyiso(args):
    """Handle NYISO-specific data download logic."""
    from lib.iso.nyiso import NYISOClient, NYISOMarket

    logger.info(f"Processing NYISO data request: {args.data_type}")

    client = NYISOClient()
    success = False

    try:
        # Map string market to enum
        market = None
        if args.market:
            market_map = {"dam": NYISOMarket.DAM, "rtm": NYISOMarket.RTM}
            market = market_map.get(args.market.lower())

        if args.data_type == "lbmp":
            if not market:
                logger.error("Market type required for LBMP data")
                return False

            # Default to zonal if not specified
            level = getattr(args, "level", "zonal")
            logger.info(f"Downloading NYISO {market.value} {level} LBMP...")
            success = client.get_lbmp(market, level, args.start, args.duration)

        elif args.data_type == "load":
            # Default to actual load
            load_type = getattr(args, "load_type", "actual")
            logger.info(f"Downloading NYISO {load_type} load data...")
            success = client.get_load_data(load_type, args.start, args.duration)

        elif args.data_type == "fuel-mix":
            logger.info("Downloading NYISO fuel mix...")
            success = client.get_fuel_mix(args.start, args.duration)

        elif args.data_type == "btm-solar":
            logger.info("Downloading NYISO BTM solar...")
            success = client.get_btm_solar(args.start, args.duration)

        elif args.data_type == "interface-flows":
            logger.info("Downloading NYISO interface flows...")
            success = client.get_interface_flows(args.start, args.duration)

        elif args.data_type == "as-prices":
            if not market:
                logger.error("Market type required for AS prices")
                return False

            logger.info(f"Downloading NYISO {market.value} AS prices...")
            success = client.get_ancillary_services_prices(market, args.start, args.duration)

        elif args.data_type == "bid":
            # Default to generator bid data
            bid_type = getattr(args, "bid_type", "generator")
            logger.info(f"Downloading NYISO {bid_type} bid data...")
            success = client.get_bid_data(bid_type, args.start, args.duration)

        elif args.data_type == "outages":
            # NYISO publishes several "outage" products:
            #   - Real-time transmission line scheduled/actual outages (P-54A/P-54B)
            #   - Day-ahead scheduled outages (P-54C)
            #   - Consolidated outage schedules CSV (P-14B)
            #   - Generation maintenance report (P-15)
            outage_type = getattr(args, "outage_type", None)

            if outage_type in {"outage-schedule", "schedule"}:
                logger.info("Downloading NYISO Outage Schedules CSV (P-14B)...")
                success = client.get_outage_schedule(args.start, args.duration)

            elif outage_type in {"gen-maint", "generation-maintenance", "maintenance"}:
                logger.info("Downloading NYISO Generation Maintenance Report (P-15)...")
                success = client.get_generation_maintenance_report(args.start, args.duration)

            else:
                # Transmission line outage feeds require a market selection (DAM or RTM)
                if not market:
                    logger.error(
                        "Market type required for NYISO transmission outage feeds (use --market dam|rtm), "
                        "or set --outage-type outage-schedule|gen-maint for the schedule/maintenance CSVs."
                    )
                    return False

                if market == NYISOMarket.DAM:
                    outage_type = None
                    logger.info(f"Downloading NYISO {market.value} outage data...")
                else:
                    # Default to actual if not specified (outage type only for RTM)
                    outage_type = outage_type or "actual"
                    logger.info(f"Downloading NYISO {market.value} {outage_type} outage data...")

                success = client.get_outages(
                    market,
                    outage_type=outage_type,
                    start_date=args.start,
                    duration=args.duration,
                )

        elif args.data_type == "constraints":
            if not market:
                logger.error("Market type required for constraints data")
                return False

            logger.info(f"Downloading NYISO {market.value} constraint data...")
            success = client.get_constraints(market, args.start, args.duration)

        else:
            logger.error(f"Unknown NYISO data type: {args.data_type}")
            logger.info(
                "Available types: lbmp, load, fuel-mix, btm-solar, interface-flows, as-prices, bid, outages, constraints"
            )
            return False

        if success:
            logger.info(f"✅ NYISO data downloaded successfully to data/NYISO/")
        else:
            logger.error("❌ NYISO data download failed")

        return success

    except Exception as e:
        logger.error(f"Error downloading NYISO data: {e}", exc_info=True)
        return False

    finally:
        client.cleanup()


def handle_bpa(args):
    """Handle BPA-specific data download logic."""
    from lib.iso.bpa import BPAClient, get_bpa_data_availability

    logger.info(f"Processing BPA data request: {args.data_type}")

    # Show BPA limitations
    info = get_bpa_data_availability()
    logger.warning(f"BPA Data Limitation: {info['temporal_coverage']}")

    client = BPAClient()
    # Optional: list available BPA transmission paths and exit
    if getattr(args, "list_bpa_paths", False):
        try:
            available = client.list_paths() if hasattr(client, "list_paths") else None
            if not available:
                logger.error("BPA client does not support list_paths(). Update lib/iso/bpa.py.")
                return False
            print("\nBPA Transmission Paths (ReportIDs)")
            print("Flowgates:")
            for rid in available.get("Flowgate") or available.get("flowgates") or []:
                print(f"  - {rid}")
            print("\nInterties:")
            for rid in available.get("Intertie") or available.get("interties") or []:
                print(f"  - {rid}")
            return True
        except Exception as e:
            logger.error(f"Failed to list BPA paths: {e}")
            return False

    success = False

    try:
        # Calculate date range
        from datetime import date, timedelta

        end_date = calculate_end_date(args.start, args.duration)

        # Route to appropriate method based on data type
        if args.data_type == "wind_gen_total_load":
            logger.info("Downloading BPA wind, generation and total load data...")
            success = client.get_wind_gen_total_load(
                args.start.year, start_date=args.start, end_date=end_date
            )

        elif args.data_type == "reserves_deployed":
            logger.info("Downloading BPA reserves deployed data...")
            success = client.get_reserves_deployed(
                args.start.year, start_date=args.start, end_date=end_date
            )

        elif args.data_type == "outages":
            logger.info("Downloading BPA outages data...")
            success = client.get_outages(args.start.year, start_date=args.start, end_date=end_date)

        elif args.data_type == "transmission_paths":
            # Requires --path-kind and --path-id
            if not args.path_kind or not args.path_id:
                logger.error(
                    "For BPA transmission_paths you must provide --path-kind (flowgate|intertie) and --path-id"
                )
                print(
                    "\n❌ Missing arguments: --path-kind and --path-id are required for BPA transmission_paths"
                )
                return False

            from lib.iso.bpa import BPAPathsKind  # enum in BPA client

            kind = (
                BPAPathsKind.FLOWGATE
                if args.path_kind.lower() == "flowgate"
                else BPAPathsKind.INTERTIE
            )

            logger.info(
                f"Downloading BPA transmission paths: {kind.value}/{args.path_id} for {args.start.year}..."
            )
            success = client.get_transmission_paths(
                kind=kind,
                report_id=args.path_id,
                year=args.start.year,
                start_date=args.start,
                end_date=end_date,
                combine_months=True,
            )

        else:
            logger.error(f"Unknown BPA data type: {args.data_type}")
            logger.info("Available types: wind_gen_total_load, reserves_deployed, outages, all")
            return False

        if success:
            logger.info(f"✅ BPA data downloaded successfully to data/BPA/")
            print(f"\n✅ BPA data downloaded successfully!")
            print(f"   Location: data/BPA/")
            print(f"   Resolution: {info['temporal_resolution']}")
            print(f"   Coverage: {info['temporal_coverage']}")
        else:
            logger.error("❌ BPA data download failed")
            print(f"\n❌ BPA data download failed. Check logs for details.")

        return success

    except Exception as e:
        logger.error(f"Error downloading BPA data: {e}", exc_info=True)
        print(f"\n❌ Error downloading BPA data: {e}")
        return False

    finally:
        client.cleanup()


def handle_spp(args):
    """Handle SPP-specific data download logic."""
    from lib.iso.spp import SPPClient, SPPMarket

    logger.info(f"Processing SPP data request: {args.data_type}")

    client = SPPClient()
    success = False

    try:
        end_date = calculate_end_date(args.start, args.duration)

        # Map string market to enum
        market = None
        if args.market:
            market_map = {"dam": SPPMarket.DAM, "rtbm": SPPMarket.RTBM}
            market = market_map.get(args.market.lower())

        if args.data_type == "lmp":
            if not market:
                logger.error("Market type required for LMP data")
                return False

            # Default is by settlement location unless --by-bus is specified
            by_location = not getattr(args, "by_bus", False)

            location_type = "by bus" if args.by_bus else "by settlement location"
            logger.info(f"Downloading SPP {market.value} LMP data {location_type}...")
            success = client.get_lmp(market, args.start, end_date, by_location=by_location)

        elif args.data_type == "mcp":
            if not market:
                logger.error("Market type required for MCP data")
                return False

            logger.info(f"Downloading SPP {market.value} MCP data...")
            success = client.get_mcp(market, args.start, end_date)

        elif args.data_type == "operating-reserves":
            logger.info("Downloading SPP Operating Reserves data...")
            success = client.get_operating_reserves(args.start, end_date)

        elif args.data_type == "binding-constraints":
            if not market:
                logger.error("Market type required for Binding Constraints data")
                return False

            logger.info(f"Downloading SPP {market.value} Binding Constraints data...")
            success = client.get_binding_constraints(market, args.start, end_date)

        elif args.data_type == "fuel-on-margin":
            logger.info("Downloading SPP Fuel On Margin data...")
            success = client.get_fuel_on_margin(args.start, end_date)

        elif args.data_type == "short-term-load-forecast":
            logger.info("Downloading SPP short-term load forecast data...")
            success = client.get_load_forecast(args.start, end_date, forecast_type="stlf")

        elif args.data_type == "medium-term-load-forecast":
            logger.info("Downloading SPP medium-term load forecast data...")
            success = client.get_load_forecast(args.start, end_date, forecast_type="mtlf")

        elif args.data_type == "short-term-resource-forecast":
            logger.info("Downloading SPP short-term resource (solar + wind) forecast data...")
            success = client.get_resource_forecast(args.start, end_date, forecast_type="strf")

        elif args.data_type == "medium-term-resource-forecast":
            logger.info("Downloading SPP medium-term resource (solar + wind) forecast data...")
            success = client.get_resource_forecast(args.start, end_date, forecast_type="mtrf")

        elif args.data_type == "market-clearing":
            logger.info("Downloading SPP Market Clearing data...")
            success = client.get_market_clearing(args.start, end_date)

        elif args.data_type == "virtual-clearing":
            logger.info("Downloading SPP Virtual Clearing data...")
            success = client.get_virtual_clearing(args.start, end_date)

        else:
            logger.error(f"Unknown SPP data type: {args.data_type}")
            logger.info(
                "Available types: lmp, mcp, operating-reserves, binding-constraints, fuel-on-margin, "
                "short-term-load-forecast, medium-term-load-forecast, short-term-resource-forecast, "
                "medium-term-resource-forecast, market-clearing, virtual-clearing"
            )
            return False

        if success:
            logger.info(f"✅ SPP data downloaded successfully to data/SPP/")
        else:
            logger.warning("⚠️  SPP data download incomplete")

        return success

    except Exception as e:
        logger.error(f"Error downloading SPP data: {e}", exc_info=True)
        return False

    finally:
        client.cleanup()


def handle_pjm(args):
    """Handle PJM-specific data download logic."""
    from lib.iso.pjm import PJMClient, PJMConfig

    logger.info(f"Processing PJM data request: {args.data_type}")

    config = PJMConfig.from_ini_file()
    client = PJMClient(config)
    success = False

    try:
        end_date = calculate_end_date(args.start, args.duration)

        if args.data_type == "lmp":
            # LMP types: da_hourly, rt_5min, rt_hourly
            lmp_type = getattr(args, "lmp_type", "da_hourly")
            pnode_id = getattr(args, "pnode_id", None)

            logger.info(f"Downloading PJM {lmp_type} LMP data...")
            if pnode_id:
                logger.info(f"Filtering by pricing node: {pnode_id}")

            success = client.get_lmp(
                lmp_type=lmp_type, start_date=args.start, duration=args.duration, pnode_id=pnode_id
            )

        elif args.data_type == "load-forecast":
            # Forecast types: 5min, historical, 7day
            forecast_type = getattr(args, "forecast_type", "historical")
            logger.info(f"Downloading PJM {forecast_type} load forecast...")

            success = client.get_load_forecast(
                forecast_type=forecast_type, start_date=args.start, duration=args.duration
            )

        elif args.data_type == "hourly-load":
            # Load types: estimated, metered, preliminary
            load_type = getattr(args, "load_type", "metered")
            logger.info(f"Downloading PJM {load_type} hourly load...")

            success = client.get_hourly_load(
                load_type=load_type, start_date=args.start, duration=args.duration
            )

        elif args.data_type == "renewable":
            # Renewable types: solar, wind
            renewable_type = getattr(args, "renewable_type", "wind")
            logger.info(f"Downloading PJM {renewable_type} generation...")

            success = client.get_renewable_generation(
                renewable_type=renewable_type, start_date=args.start, duration=args.duration
            )

        elif args.data_type == "ancillary-services":
            # AS types: hourly, 5min, reserve_market
            as_type = getattr(args, "as_type", "hourly")
            logger.info(f"Downloading PJM {as_type} ancillary services...")

            success = client.get_ancillary_services(
                as_type=as_type, start_date=args.start, duration=args.duration
            )

        elif args.data_type == "outages":
            logger.info("Downloading PJM generation outages...")
            success = client.get_outages_and_limits(
                data_type="outages", start_date=args.start, duration=args.duration
            )

        elif args.data_type == "transfer-limits":
            logger.info("Downloading PJM RTO transfer limits and flows...")
            success = client.get_outages_and_limits(
                data_type="transfer_limits", start_date=args.start, duration=args.duration
            )

        else:
            logger.error(f"Unknown PJM data type: {args.data_type}")
            logger.info(
                "Available types: lmp, load-forecast, hourly-load, renewable, "
                "ancillary-services, outages, transfer-limits"
            )
            return False

        if success:
            logger.info(f"✅ PJM data downloaded successfully to data/PJM/")
        else:
            logger.error("❌ PJM data download failed")

        return success

    except Exception as e:
        logger.error(f"Error downloading PJM data: {e}", exc_info=True)
        return False

    finally:
        client.cleanup()


def handle_isone(args):
    """Handle ISO-NE-specific data download logic (updated for new ISONEClient)."""
    from lib.iso.isone import ISONEClient

    logger.info(f"Processing ISO-NE data request: {args.data_type}")

    client = ISONEClient()
    start = args.start
    end_excl = start + timedelta(days=args.duration)
    success = False

    def _yyyymmdd(d: date) -> str:
        return d.strftime("%Y%m%d")

    def _download_fivemin_lmp(location_id=None):
        """Download 5-minute RT LMPs via REST (/fiveminutelmp). Saves one JSON per day."""
        out_paths = []
        for d in (start + timedelta(days=i) for i in range(args.duration)):
            day_str = _yyyymmdd(d)
            loc = int(location_id) if location_id is not None else 4000  # ISO-NE Internal Hub
            path = f"fiveminutelmp/day/{day_str}/location/{loc}"
            payload = client._request_json(path, authenticated=True)
            suffix = f"_loc{int(location_id)}" if location_id is not None else ""
            out_path = client.config.data_dir / f"fiveminutelmp_{day_str}{suffix}.json"
            client._save_json(payload, out_path)
            out_paths.append(out_path)
        return out_paths

    def _download_hourly_rcp_final():
        """Download hourly final regulation clearing prices via REST (/hourlyrcp/final)."""
        out_paths = []
        for d in (start + timedelta(days=i) for i in range(args.duration)):
            day_str = _yyyymmdd(d)
            path = f"hourlyrcp/final/day/{day_str}"
            payload = client._request_json(path, authenticated=True)
            out_path = client.config.data_dir / f"hourlyrcp_final_{day_str}.json"
            client._save_json(payload, out_path)
            out_paths.append(out_path)
        return out_paths

    try:
        if args.data_type == "lmp":
            # LMP types: da_hourly, rt_5min
            lmp_type = getattr(args, "lmp_type", "da_hourly")

            if lmp_type == "da_hourly":
                logger.info("Downloading ISO-NE Day-Ahead Hourly LMP (REST)...")
                paths = client.get_hourly_lmp(start, end_excl, market="da", report="final")
                success = bool(paths)

            elif lmp_type == "rt_5min":
                logger.info("Downloading ISO-NE Real-Time 5-Minute LMP (REST)...")
                location_id = getattr(args, "location_id", None)
                paths = _download_fivemin_lmp(location_id=location_id)
                success = bool(paths)

            else:
                logger.error(f"Invalid LMP type: {lmp_type}")
                return False

        elif args.data_type == "ancillary":
            # Ancillary types: 5min_reg, hourly_reg, 5min_reserves, hourly_reserves
            anc_type = getattr(args, "anc_type", "5min_reg")

            if anc_type == "5min_reg":
                logger.info("Downloading ISO-NE 5-Minute Regulation Clearing Prices (Final)...")
                paths = client.get_5min_regulation_prices(start, end_excl)
                success = bool(paths)

            elif anc_type == "hourly_reg":
                logger.info("Downloading ISO-NE Hourly Regulation Clearing Prices (Final)...")
                paths = _download_hourly_rcp_final()
                success = bool(paths)

            elif anc_type == "5min_reserves":
                # Closest supported feed in the new client: Real-Time Hourly Operating Reserve
                location_id = getattr(args, "location_id", 7000)
                logger.info(
                    f"Downloading ISO-NE Real-Time Hourly Operating Reserve (location {location_id})..."
                )
                paths = client.get_real_time_hourly_operating_reserve(
                    start, end_excl, location_id=location_id
                )
                success = bool(paths)

            elif anc_type == "hourly_reserves":
                location_id = getattr(args, "location_id", 7000)
                logger.info(
                    f"Downloading ISO-NE Day-Ahead Hourly Operating Reserve (location {location_id})..."
                )
                paths = client.get_day_ahead_hourly_operating_reserve(
                    start, end_excl, location_id=location_id
                )
                success = bool(paths)

            else:
                logger.error(f"Invalid ancillary type: {anc_type}")
                return False

        elif args.data_type == "demand":
            # Demand types: 5min, hourly_da
            demand_type = getattr(args, "demand_type", "5min")

            if demand_type == "5min":
                logger.info("Downloading ISO-NE 5-Minute System Demand (REST)...")
                paths = client.get_5min_system_demand(start, end_excl)
                success = bool(paths)

            elif demand_type == "hourly_da":
                logger.info("Downloading ISO-NE Day-Ahead Hourly Demand (REST)...")
                paths = client.get_day_ahead_hourly_demand(start, end_excl)
                success = bool(paths)

            else:
                logger.error(f"Invalid demand type: {demand_type}")
                return False

        elif args.data_type == "outages":
            # Outage types: short-term, long-term
            outage_type = getattr(args, "outage_type", "short-term")

            logger.info(f"Downloading ISO-NE {outage_type} Transmission Outage report...")
            paths = client.get_transmission_outages(start, end_excl, outage_type=outage_type)
            success = bool(paths)

        elif args.data_type == "ams":

            logger.info("Downloading ISO-NE Annual Maintenance Schedule (AMS)...")
            paths = client.get_annual_maintenance_schedule(start, end_excl)
            success = bool(paths)

        else:
            logger.error(f"Unknown ISO-NE data type: {args.data_type}")
            logger.info("Available types: lmp, ancillary, demand, outage, ams")
            return False

        if success:
            logger.info("✅ ISO-NE data downloaded successfully.")
        else:
            logger.error("❌ Failed to download ISO-NE data.")

        return success

    except Exception as e:
        logger.error(f"Error processing ISO-NE data: {e}", exc_info=True)
        return False


def handle_weather(args):
    """Handle weather data download logic."""
    from lib.weather.client import WeatherClient

    logger.info("Processing weather data request")

    if not args.state:
        logger.error("State code required for weather data")
        return False

    client = WeatherClient()
    success = False

    try:
        logger.info(f"Downloading weather data for {args.state}...")
        success = client.download_weather_data(
            state=args.state,
            start_date=args.start,
            duration=args.duration,
            interactive=False,  # Auto-select first station in CLI mode
        )

        if success:
            logger.info(f"✅ Weather data downloaded successfully to data/weather/")

            # Optionally download solar data
            if getattr(args, "include_solar", False):
                year = args.start.year
                logger.info(f"Downloading solar data for {year}...")
                client.download_solar_data(year=year)
        else:
            logger.error("❌ Weather data download failed")

        return success

    except Exception as e:
        logger.error(f"Error downloading weather data: {e}", exc_info=True)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="ISO-DART v2.0 - Download energy market data from ISOs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python isodart.py

  # CAISO Day-Ahead LMP
  python isodart.py --iso caiso --data-type lmp --market dam --start 2024-01-01 --duration 7

  # MISO Wind Generation
  python isodart.py --iso miso --data-type wind --start 2024-01-01 --duration 30

  # SPP Day-Ahead LMP
  python isodart.py --iso spp --data-type lmp --market dam --start 2024-01-01 --duration 7

  # SPP Market Clearing Prices
  python isodart.py --iso spp --data-type mcp --market rtbm --start 2024-01-01 --duration 7

  # SPP Operating Reserves
  python isodart.py --iso spp --data-type operating-reserves --start 2024-01-01 --duration 7

  # BPA Load Data
  python isodart.py --iso bpa --data-type load --start 2024-01-01 --duration 7

  # Weather data
  python isodart.py --data-type weather --state CA --start 2024-01-01 --duration 30
        """,
    )

    parser.add_argument(
        "--iso",
        choices=["caiso", "miso", "nyiso", "bpa", "spp", "pjm", "isone"],
        help="Independent System Operator",
    )

    parser.add_argument(
        "--data-type",
        help="Type of data to download (lmp, load, weather, etc.)",
    )

    parser.add_argument(
        "--market",
        choices=["dam", "rtm", "rtbm", "hasp", "rtpd", "ruc"],
        help="Energy market type (rtbm = Real-Time Balancing Market for SPP)",
    )

    parser.add_argument(
        "--start",
        type=validate_date,
        help="Start date (YYYY-MM-DD)",
    )

    parser.add_argument(
        "--duration",
        type=int,
        help="Duration in days",
    )

    parser.add_argument(
        "--state",
        help="US state 2-letter code (for weather data)",
    )

    parser.add_argument(
        "--caiso-report-kind",
        choices=["am", "prior", "both"],
        default="both",
        help="For CAISO curtailed-nonop: which report flavor to download",
    )

    parser.add_argument(
        "--by-bus",
        action="store_true",
        help="For SPP LMP: Get data by bus instead of by settlement location (default: settlement location)",
    )

    parser.add_argument(
        "--lmp-type",
        choices=[
            "da_exante",
            "da_expost",
            "rt_exante",
            "rt_expost",
            "da_hourly",
            "rt_5min",
            "rt_hourly",
        ],
        help="For MISO, PJM, and ISO-NE LMP: type of LMP data to download",
    )

    parser.add_argument(
        "--mcp-type",
        choices=[
            "asm_da_exante",
            "asm_da_expost",
            "asm_rt_exante",
            "asm_rt_expost",
            "asm_rt_summary",
        ],
        default="asm_da_exante",
        help="For MISO MCP: type of MCP data to download",
    )

    parser.add_argument(
        "--load-type",
        choices=[
            "da_demand",
            "rt_forecast",
            "rt_actual",
            "rt_state_estimator",
            "actual",
            "iso_forecast",
            "zonal_bid",
            "weather_forecast",
            "estimated",
            "metered",
            "preliminary",
        ],
        help="For MISO, NYISO, PJM Load: type of load data to download",
    )

    parser.add_argument(
        "--gen-type",
        choices=[
            "da_cleared_physical",
            "da_cleared_virtual",
            "da_fuel_type",
            "da_offered_ecomax",
            "da_offered_ecomin",
            "rt_cleared",
            "rt_committed_ecomax",
            "rt_fuel_margin",
            "rt_fuel_type",
            "rt_offered_ecomax",
        ],
        default="rt_fuel_type",
        help="For MISO Generation: type of generation data to download",
    )

    parser.add_argument(
        "--interchange-type",
        choices=["da_net_scheduled", "rt_net_actual", "rt_net_scheduled", "historical"],
        default="rt_net_actual",
        help="For MISO Interchange: type of interchange data to download",
    )

    parser.add_argument(
        "--outage-type",
        choices=[
            "forecast",
            "rt_outage",
            "scheduled",
            "actual",
            "gen-maint",
            "outage-schedule",
            "short-term",
            "long-term",
        ],
        help="For MISO, NYISO and ISO-NE Outage: type of outage data to download",
    )

    parser.add_argument(
        "--level",
        choices=["zonal", "generator"],
        default="zonal",
        help="For NYISO LBMP: level of LBMP data to download",
    )

    parser.add_argument(
        "--bid-type",
        choices=["generator", "load", "transaction", "commitment"],
        help="For NYISO Bid: type of bid data to download",
    )

    parser.add_argument(
        "--pnode-id",
        type=int,
        help="For PJM LMP: Pricing node ID (optional, downloads all nodes if not specified)",
    )

    parser.add_argument(
        "--forecast-type",
        choices=["5min", "historical", "7day"],
        default="historical",
        help="For PJM Load Forecast: type of forecast",
    )

    parser.add_argument(
        "--renewable-type",
        choices=["solar", "wind"],
        help="For PJM Renewable: type of renewable generation",
    )

    parser.add_argument(
        "--as-type",
        choices=["hourly", "5min", "reserve_market"],
        help="For PJM Ancillary Services: type of AS data",
    )

    parser.add_argument(
        "--anc-type",
        choices=["5min_reg", "hourly_reg", "5min_reserves", "hourly_reserves"],
        help="For ISO-NE Ancillary Services: type of AS data",
    )

    parser.add_argument(
        "--demand-type",
        choices=["5min", "hourly_da"],
        help="For ISO-NE Demand data: type of demand data",
    )

    parser.add_argument(
        "--location-id",
        type=int,
        help="For ISO-NE location ID: Needed for full day 5min data",
    )

    # BPA Transmission Paths (Flowgates/Interties)
    parser.add_argument(
        "--path-kind",
        choices=["flowgate", "intertie"],
        help="For BPA transmission_paths: whether the report is a Flowgate or Intertie",
    )
    parser.add_argument(
        "--path-id",
        help="For BPA transmission_paths: BPA ReportID (e.g., ColumbiaInjection, AC, BC, etc.)",
    )
    parser.add_argument(
        "--list-bpa-paths",
        action="store_true",
        help="List available BPA transmission path ReportIDs (scraped from BPA PathFileLocations page) and exit",
    )

    parser.add_argument(
        "--include-solar",
        action="store_true",
        help="Include solar data with weather download",
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        default=False,
        help="Run in interactive mode (default if no args provided)",
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Setup directories
    setup_directories()

    # If no arguments provided, run in interactive mode
    if len(sys.argv) == 1 or args.interactive:
        from lib.interactive import run_interactive_mode

        run_interactive_mode()
        return

    # Validate required arguments for command-line mode
    if args.data_type == "weather":
        if not args.state or not args.start or not args.duration:
            parser.error("Weather data requires --state, --start, and --duration")
        return handle_weather(args)

    if not args.iso:
        parser.error("--iso is required (or use --interactive mode)")

    if not args.data_type:
        parser.error("--data-type is required")

    # Some actions are informational and don't require a date range (e.g., BPA path listing)
    needs_date_range = not (
        args.iso == "bpa"
        and args.data_type == "transmission_paths"
        and getattr(args, "list_bpa_paths", False)
    )

    if needs_date_range and (not args.start or not args.duration):
        parser.error("--start and --duration are required")

    # Route to appropriate handler
    handlers = {
        "caiso": handle_caiso,
        "miso": handle_miso,
        "nyiso": handle_nyiso,
        "bpa": handle_bpa,
        "spp": handle_spp,
        "pjm": handle_pjm,
        "isone": handle_isone,
    }

    handler = handlers.get(args.iso)
    if handler:
        success = handler(args)
        sys.exit(0 if success else 1)
    else:
        logger.error(f"Unknown ISO: {args.iso}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
