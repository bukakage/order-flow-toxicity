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

    async def get_time_and_sales_chunk(self, contract, start_time, end_time, max_retries=3):
        for attempt in range(max_retries):
            try:
                trades = await self.ib.reqHistoricalTicksAsync(
                    contract,
                    start_time,
                    end_time,
                    1000,
                    'TRADES',
                    useRth=False,
                    ignoreSize=False
                )
                return trades
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt+1} failed: {e}. Retrying...")
                    await asyncio.sleep(1) 
                else:
                    logger.error(f"Failed to get data after {max_retries} attempts: {e}")
                    return []

    async def get_time_and_sales(self, contract, start_date, end_date):
        all_trades = []
        current_time = start_date
        chunk_size = timedelta(hours=1)

        while current_time < end_date:
            chunk_end = min(current_time + chunk_size, end_date)
            logger.info(f"Requesting data for {contract.symbol} from {current_time} to {chunk_end}")
            
            trades = await self.get_time_and_sales_chunk(contract, current_time, chunk_end)
            
            if trades:
                all_trades.extend(trades)
                current_time = chunk_end
            else:
                chunk_size = max(chunk_size / 2, timedelta(minutes=5))
                logger.info(f"Reduced chunk size to {chunk_size}")
            
            await asyncio.sleep(0.1)

        return all_trades

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

    # Request Time & Sales data from start_date to end_date
    trades = await app.get_time_and_sales(valid_contract, start_date, end_date)
    if trades:
        filename = f"{symbol}_TEG_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
        with open(filename, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['DateTime', 'Price', 'Volume'])
            for trade in trades:
                csvwriter.writerow([trade.time, trade.price, trade.size])
        logger.info(f"Time & Sales data for {symbol} saved to {filename}")
    else:
        logger.error(f"No Time & Sales data retrieved for {symbol}")

async def main():
    app = MarketDataApp()
    if not await app.connect():
        return

    try:
        start_date = datetime(2024, 8, 6, tzinfo=pytz.timezone('US/Eastern'))
        end_date = datetime.now(pytz.timezone('US/Eastern'))

        # Process ES futures
        # await process_future(app, 'ES', 'CME', 'USD', start_date, end_date)
        
        # Process NKD futures
        await process_future(app, 'NKD', 'CME', 'USD', start_date, end_date)

    except Exception as e:
        logger.error(f"An error occurred: {e}")

    finally:
        app.ib.disconnect()

if __name__ == "__main__":
    # asyncio.run(main())
    await main()