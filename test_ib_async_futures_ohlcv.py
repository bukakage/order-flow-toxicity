#%%
import asyncio
import random
from datetime import datetime, timedelta
from ib_async import *
import logging
import csv
import pytz
#%%
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SOCKET = {
    'HOST': '127.0.0.1',
    'PORT': 7497
}

class MarketDataApp:
    def __init__(self):
        self.ib = IB()

    async def connect(self):
        try:
            await self.ib.connectAsync(SOCKET['HOST'], SOCKET['PORT'], clientId=random.randint(1, 9999))
            self.ib.reqMarketDataType(3)
            return True
        except Exception as e:
            logger.error(f"Connection to IB failed: {e}")
            return False

    async def get_historical_data(self, contract, start_date, end_date, bar_size='1 min'):
        try:
            all_bars = []
            current_end_date = end_date
            
            while current_end_date > start_date:
                bars = await self.ib.reqHistoricalDataAsync(
                    contract,
                    endDateTime=current_end_date.strftime('%Y%m%d %H:%M:%S'),
                    durationStr='1 M',
                    barSizeSetting=bar_size,
                    whatToShow='TRADES',
                    useRTH=True,
                    formatDate=2
                )
                
                if not bars:
                    break
                
                all_bars = bars + all_bars
                current_end_date = bars[0].date - timedelta(minutes=1)
                
                if current_end_date <= start_date:
                    break
            
            return [bar for bar in all_bars if bar.date >= start_date]
        except Exception as e:
            logger.error(f"Historical data request failed: {e}")
            return None

    async def find_valid_contract(self, symbol, exchange, currency):
        current_date = datetime.now()
        for i in range(12): 
            contract_date = current_date + timedelta(days=30*i)
            contract_month = contract_date.strftime("%Y%m")
            contract = Future(symbol=symbol, lastTradeDateOrContractMonth=contract_month, exchange=exchange, currency=currency)
            try:
                details = await self.ib.reqContractDetailsAsync(contract)
                if details:
                    return details[0].contract
            except:
                pass
        return None

async def process_future(app, symbol, exchange, currency, start_date, end_date):
    valid_contract = await app.find_valid_contract(symbol, exchange, currency)
    if not valid_contract:
        logger.error(f"No valid contract found for {symbol}. Please check your market data permissions.")
        return

    logger.info(f"Valid contract found for {symbol}: {valid_contract}")

    # Request historical data from start_date to end_date
    bars = await app.get_historical_data(valid_contract, start_date, end_date, bar_size='1 min')
    if bars:
        # Save to CSV
        filename = f"{symbol}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}_1min.csv"
        with open(filename, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
            for bar in bars:
                csvwriter.writerow([bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume])
        logger.info(f"Data for {symbol} saved to {filename}")
    else:
        logger.error(f"No historical data retrieved for {symbol}")

async def async_futures():
    app = MarketDataApp()
    if not await app.connect():
        return

    try:
        start_date = datetime(2024, 8, 6, tzinfo=pytz.timezone('US/Eastern'))
        end_date = datetime.now(pytz.timezone('US/Eastern'))

        # Process ES futures
        await process_future(app, 'ES', 'CME', 'USD', start_date, end_date)
        
        # Process NKD futures
        #await process_future(app, 'NKD', 'CME', 'USD', start_date, end_date)

    except Exception as e:
        logger.error(f"An error occurred: {e}")

    finally:
        app.ib.disconnect()
# %%
async def main():
    await async_futures()
# await async_futures()
# %%
