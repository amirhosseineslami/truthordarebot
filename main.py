from botApiClient import BotApiClient
from keypad import Keypad
import time
import traceback
from rubikaMessageParser import RubikaMessageParser
from rubikaMessageParser import Message
from language import lang
from models.offset import Offset
from connection_manager import ConnectionManager
import json
from models.user import User
LOCAL_SAVE_NAME = "offset.json"
OFFSET_STORE_KEY = "offset"

# Init components
apiClient = BotApiClient()
keypad = Keypad()
message_update_offset_id = "69e788f62008759a9b5eed0a"
parser = RubikaMessageParser()

searching_girls:list[Message] = []
searching_boys:list[Message] = []
searching_allusers:list[Message] = []

connection_between_players  = ConnectionManager()
user_language = "fa"

def main():


    # Bot is running
    bot_running = True
    print("bot is running")


    # Get the last message update offset id
    global message_update_offset_id
    file = load_from_local_storage()
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
            parsed = parser.parse_response(messages)
            parsedMessages = parsed.updates

            # Process each messages
            message_handler(parsedMessages)

            # Update offset for the next operation
            if parsed.message_count:
                print(parsed.message_count)

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
        time.sleep(0.3)

def message_handler(parsedMessages: list[Message]):
    global user_language

    for msg in parsedMessages:
        print(f"{msg.sender_id} in {msg.chat_id}: {msg.text} is being checked!")
        keydata = None

        if msg.text == "/start":
            # welcome message
            message_to_send = lang.get_text("welcome",user_language)
            keydata = get_main_page_keydata()

            this_user , created = User().get_or_create_user(msg.sender_id,msg.chat_id)
            

        elif msg.text.strip().lower().startswith(lang.get_text("play_with_stranger", user_language).lower()):

            # Play
            play_with_stranger(msg)

        elif msg.text == lang.get_text("cancel_the_search", user_language):
            # canceled the search
            message_to_send = lang.get_text("search_is_canceled_by_user", user_language)
            keydata = get_main_page_keydata()

        elif msg.text == lang.get_text("disconnect_the_connection", user_language):

            # Notify the current user about disconnection
            message_to_send = lang.get_text("your_disconnect_request_is_accepted", user_language)
            keydata = get_main_page_keydata()

            # Notify the opposite user about disconnection status
            keypad.send_message_with_keypad(connection_between_players.forward_message(msg.chat_id, ""), lang.get_text("other_user_disconnected"),get_main_page_keydata())

            # Remove the connection between these 2 players
            connection_between_players.disconnect(msg.chat_id)


        
        # Forward the message if there's any connection for this user
        elif connection_between_players.is_connected(msg.chat_id):
            forward_message_to_connected_player(msg)


        # Check if there is any keypad to send
        if keydata != None and message_to_send:
            keypad.send_message_with_keypad(msg.chat_id, message_to_send, keydata)
            keydata = None

        


def play_with_stranger(msg:Message):

    # remove this user from waiting queue if it's already in
    if (connection_between_players.is_in_queue(msg.chat_id)):
        connection_between_players.remove_from_waiting_queue(msg.chat_id)
        print(msg.chat_id," removed from queue")
        print("size of queue after remove:",connection_between_players.get_queue_size())

    if(connection_between_players.get_queue_size() < 1):

        # Add if it's not already in the queue
        if not connection_between_players.is_in_queue(msg.chat_id):
            connection_between_players.add_to_waiting_queue(msg.chat_id,msg.sender_id)
            print(msg.chat_id, "Added to queue!")
            keypad.send_message_with_keypad(msg.chat_id, lang.get_text("stranger"), get_cancel_the_search_keydata())

        # Add the user to the searching list
        print(connection_between_players.get_queue_size(),"This is the new queue size")
    
    else:

        random_pair = connection_between_players.pair_random(msg.chat_id, msg.sender_id)
        # Connect the user to another waiting player
        if random_pair != None:
            connected_player_chat_id, connected_player_username = random_pair

            # Send message to both connected players that they're connected now!
            keypad.send_message_with_keypad(connected_player_chat_id, lang.get_text("you_are_now_connected_to_somebody"),get_keydata_player_connected())            
            keypad.send_message_with_keypad(msg.chat_id, lang.get_text("you_are_now_connected_to_somebody"),get_keydata_player_connected())            

def get_main_page_keydata():
    key_play_with_stranger = keypad.create_simple_button(1, lang.get_text("play_with_stranger",user_language))
    key_play_with_friend = keypad.create_simple_button(2, lang.get_text("play_with_friend",user_language))
    key_get_coin = keypad.create_simple_button(3, lang.get_text("get_coin"))
    row1 = keypad.create_keypad_row([key_play_with_stranger, key_play_with_friend])
    row2 = keypad.create_keypad_row([key_get_coin])
    keydata = keypad.build_keypad([row1,row2])
    return keydata

def get_keydata_player_connected():
    key_disconnect_the_connection = keypad.create_simple_button(1, lang.get_text("disconnect_the_connection", user_language))
    row1 = keypad.create_keypad_row([key_disconnect_the_connection])
    keydata = keypad.build_keypad([row1])
    return keydata

def get_cancel_the_search_keydata():
    key_cancel_the_search = keypad.create_simple_button(1, lang.get_text("cancel_the_search", user_language))
    row1 = keypad.create_keypad_row([key_cancel_the_search])
    keydata = keypad.build_keypad([row1])
    return keydata

def forward_message_to_connected_player(msg:Message, user_language = "fa"):
    # if msg.text == lang.get_text("play_with_stranger",user_language):
    #     # Return because this message is a command and should not be sent to the other player
    #     return
    apiClient.send_message(connection_between_players.forward_message(msg.chat_id, msg.text), msg.text)
    

def load_from_local_storage() -> dict:
    try:
        with open(LOCAL_SAVE_NAME, 'r') as f:
            return json.load(f)
    except Exception as e:
        traceback.print_exc()
        return None
    


if __name__ == "__main__" :
    main()