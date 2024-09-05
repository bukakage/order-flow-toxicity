

import asyncio
import os 
from telegram import Bot

async def send_telegram_message(symbol, image = ""):
    
    token_file_path = 'data/token/bot_token.txt'
    
    if not os.path.exists(token_file_path):
        raise FileNotFoundError(f"Token file {token_file_path} does not exist!")
    
    try:
        with open(token_file_path, 'r') as file:
            bot_token = file.readline().strip()
    except Exception as e:
        raise RuntimeError(f"Failed to read token file: {e}")
    
    channel_id_path = 'data/token/channel_token.txt'
    
    if not os.path.exists(channel_id_path):
        raise FileNotFoundError(f"Channel file {channel_id_path} does not exist!")
    
    try:
        with open(channel_id_path, 'r') as file:
            chat_id = file.readline().strip()
    except Exception as e:
        raise RuntimeError(f"Failed to read Channel file: {e}")
    #bot_token = '7316386678:AAEQbenWg2xxuLCOjhuGSvht67k5mPOIxrk'
    #chat_id = '@order_flow_toxicity'
    
    message = f"Alert!! {symbol} Order flow toxicity raised above 80"
    
    image_path = 'data/picture/signal.png'
    print(bot_token , chat_id)
    
    bot = Bot(token=bot_token)
    

    # await bot.send_message(chat_id=chat_id, text=message)
# Send the picture
    try:
        # Send the picture
        if image:  # If image path is provided, use it
            with open(image, 'rb') as photo:
                await bot.send_photo(chat_id=chat_id, photo=photo, caption=message)
        
        print("Alert sent successfully!")
        
        # After usage, delete the file
        # if os.path.exists(image):
        #     os.remove(image)
        #     print(f"Temporary file {image} has been deleted.")
            
        print("Alert sent successfully!")
        
    except Exception as e:
        print(f"Failed to send alert: {e}")
# Run the async function
# asyncio.run(send_telegram_message(symbol))
# %%
