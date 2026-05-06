from bot.core.apiClient import BotApiClient
import time
import traceback
from bot.handlers.rubikaMessageParser import RubikaParser, Message
import json
import traceback
import asyncio


LOCAL_SAVE_NAME = "offset.json"
OFFSET_STORE_KEY = "offset"

import concurrent.futures
import threading
from typing import List

# Create a thread pool (adjust max_workers based on your needs)
# 4-10 workers is usually good for I/O-bound bot operations
_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=10, thread_name_prefix="BotWorker")
_thread_local = threading.local()

from bot.handlers.MessageResponseHandler import MessageResponseHandler  # Import the message handler function
message_handler_lock = threading.Lock()  # Lock to ensure thread safety in message handling
parser = RubikaParser()  # Initialize the parser (if needed)
apiClient = BotApiClient()  # Initialize the API client (if needed)
message_response_handler = MessageResponseHandler(apiClient=apiClient)


async def main():
    while True:
        await do_polling()
        await asyncio.sleep(0.5)


async def do_polling():

    # Bot is running
    bot_running = True
    print("bot is running")


    # Get the last message update offset id
    global message_update_offset_id
    file = message_response_handler.load_from_local_storage()
    if file:
        message_update_offset_id = file.get(OFFSET_STORE_KEY)


    new_message_update_offset_id = None

    # while True:
    #     try:
    #         new_message_update_offset_id = Offset.get()
    #     except Exception as e:
    #         traceback.print_exc()
    #     if new_message_update_offset_id:break

    # if new_message_update_offset_id:
    #     if new_message_update_offset_id != "0":
    #         message_update_offset_id = new_message_update_offset_id
    #         print("##############"+message_update_offset_id)

    # Main loop
    while bot_running:

        # Get message updates

        try:

            # Fetch updates from API
            messages = apiClient.get_updates(message_update_offset_id)

            # Parse the messy response into clean objects
            parsed = parser.parse_updates(messages)
            parsedMessages = parsed.updates

            # Process each messages
            message_handler(parsedMessages)

            if parsed.next_offset_id:
                print(parsed.next_offset_id)
                print("Let's save the new offfffffffffseeeetttttttttttttttt")
                message_update_offset_id = parsed.next_offset_id
                # Offset.store(message_update_offset_id)

                # Save offset as file in storage
                my_offset_dict = {
                    OFFSET_STORE_KEY : message_update_offset_id
                }
                with open(LOCAL_SAVE_NAME,'w') as f:
                    json.dump(my_offset_dict, f)
                
        except Exception as e:
            traceback.print_exc()
        print(time.time())
        time.sleep(0.5)

def message_handler(parsed_response: List[Message]):
    """
    Handle multiple messages concurrently using ThreadPoolExecutor.
    """
    if not parsed_response:
        return
    
    # Submit all messages to the thread pool
    futures = []
    for item in parsed_response:
        future = _EXECUTOR.submit(handle_one_message_threadsafe, item)
        futures.append(future)
    
    # Optional: Wait for all tasks to complete (with timeout)
    # This ensures all messages are processed before next iteration
    for future in concurrent.futures.as_completed(futures, timeout=30):
        try:
            future.result()  # Will raise any exception that occurred
        except Exception as e:
            print(f"Error processing message in thread: {e}")

def handle_one_message_threadsafe(msg: Message):
    """
    Thread-safe wrapper for message handling.
    Each thread gets its own context.
    """
    # Get or create thread-local resources
    if not hasattr(_thread_local, 'user_mgr'):
        # Initialize thread-local instances (if your managers are thread-safe)
        _thread_local.api_client = apiClient
    
    try:
        # Call the original handler with thread-local resources
        message_response_handler.handle_one_message(
            msg
        )
    except Exception as e:
        error_message = f"Error in thread for message {msg.message_id}: {traceback.format_exception(e).__str__()}"
        print(error_message)
        message_response_handler.send_message_to_admin(error_message)
        traceback.print_exc()



if __name__ == "__main__" :  
    asyncio.run(main())