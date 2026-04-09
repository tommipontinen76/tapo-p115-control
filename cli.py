import asyncio
import argparse
import logging
import sys
import aiohttp
from datetime import datetime
from plugp100.new.device_factory import connect, DeviceConnectConfiguration
from plugp100.common.credentials import AuthCredential
from plugp100.new.components.energy_component import EnergyComponent

# Default Finnish values
DEFAULT_VAT = 25.5
DEFAULT_ELEC_TAX_EXCL_VAT = 1.795217

async def fetch_spot_price():
    """Fetch current electricity spot price for Finland."""
    try:
        url = "https://api.porssisahko.net/v1/latest-prices.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    prices = data.get("prices", [])
                    
                    now_utc = datetime.now()
                    # We can use local time if it matches the start/end dates.
                    # Usually prices from porssisahko are in ISO format with UTC offset or Z.
                    for p in prices:
                        try:
                            start = datetime.fromisoformat(p["startDate"].replace("Z", "+00:00"))
                            end = datetime.fromisoformat(p["endDate"].replace("Z", "+00:00"))
                            
                            # Use timezone aware now
                            import datetime as dt
                            now = dt.datetime.now(dt.timezone.utc)
                            
                            if start <= now < end:
                                return p["price"]
                        except (ValueError, KeyError):
                            continue
    except Exception as e:
        logging.error(f"Error fetching spot price: {e}")
    return None

def calculate_cost(energy_kwh, base_price_cents, margin=0.0, distribution=0.0, elec_tax_excl_vat=DEFAULT_ELEC_TAX_EXCL_VAT, vat_rate=DEFAULT_VAT):
    """Calculate cost in Euros."""
    total_price_per_kwh_cents = (base_price_cents + margin + distribution + elec_tax_excl_vat) * (1 + vat_rate / 100.0)
    return energy_kwh * (total_price_per_kwh_cents / 100.0)

async def main():
    parser = argparse.ArgumentParser(description="Tapo P115 CLI Control")
    parser.add_argument("--ip", required=True, help="Device IP address")
    parser.add_argument("--email", required=True, help="Tapo account email")
    parser.add_argument("--password", required=True, help="Tapo account password")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show device status")
    status_parser.add_argument("--price", type=float, help="Manual price per kWh (cents)")
    status_parser.add_argument("--margin", type=float, default=0.0, help="Margin (cents/kWh)")
    status_parser.add_argument("--dist", type=float, default=0.0, help="Distribution (cents/kWh)")
    status_parser.add_argument("--spot", action="store_true", help="Use current spot price")
    
    # On command
    subparsers.add_parser("on", help="Turn device ON")
    
    # Off command
    subparsers.add_parser("off", help="Turn device OFF")
    
    # Toggle command
    subparsers.add_parser("toggle", help="Toggle device power")

    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return

    try:
        config = DeviceConnectConfiguration(host=args.ip, credentials=AuthCredential(args.email, args.password))
        device = await connect(config)
        await device.update()
        
        if args.command == "status":
            is_on = device.is_on
            print(f"Device Status: {'ON' if is_on else 'OFF'}")
            
            energy_comp = device.get_component(EnergyComponent)
            if energy_comp and energy_comp.energy_info:
                power_w = energy_comp.energy_info.current_power or 0
                today_energy_kwh = (energy_comp.energy_info.today_energy or 0) / 1000.0
                month_energy_kwh = (energy_comp.energy_info.month_energy or 0) / 1000.0
                
                print(f"Current Power: {power_w / 1000.0:.3f} kW")
                print(f"Today's Energy: {today_energy_kwh:.2f} kWh")
                print(f"Month Energy: {month_energy_kwh:.2f} kWh")
                
                base_price = 0.0
                if args.spot:
                    spot = await fetch_spot_price()
                    if spot is not None:
                        base_price = spot
                        print(f"Using Spot Price: {base_price:.2f} c/kWh")
                    else:
                        print("Warning: Could not fetch spot price, using 0.0")
                elif args.price is not None:
                    base_price = args.price
                    print(f"Using Manual Price: {base_price:.2f} c/kWh")
                
                cost = calculate_cost(today_energy_kwh, base_price, args.margin, args.dist)
                print(f"Today's Estimated Cost: {cost:.2f} €")
            else:
                print("Energy information not available.")

        elif args.command == "on":
            await device.turn_on()
            print("Device turned ON")
            
        elif args.command == "off":
            await device.turn_off()
            print("Device turned OFF")
            
        elif args.command == "toggle":
            if device.is_on:
                await device.turn_off()
                print("Device turned OFF")
            else:
                await device.turn_on()
                print("Device turned ON")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
