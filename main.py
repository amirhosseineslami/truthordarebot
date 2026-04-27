from botApiClient import BotApiClient
from keypad import Keypad
import time
import traceback
from rubikaMessageParser import RubikaParser, Chat, Message
from language import lang
from models.offset import Offset
from connection_manager import ConnectionManager
import json
from models.sync_manager import SyncManager, UserManager,LocalUser

import random


LOCAL_SAVE_NAME = "offset.json"
OFFSET_STORE_KEY = "offset"

# Init components
apiClient = BotApiClient()
keypad = Keypad()
message_update_offset_id = "69e788f62008759a9b5eed0a"
parser = RubikaParser()

searching_girls:list[Message] = []
searching_boys:list[Message] = []
searching_allusers:list[Message] = []

connection_between_players  = ConnectionManager()
user_language = "fa"

# At startup, choose mode (e.g., via environment variable)
import os
mode = os.environ.get('BOT_MODE', 'offline')   # 'online', 'offline', 'periodic'
interval = int(os.environ.get('SYNC_INTERVAL_HOURS', 2))

sync_mgr = SyncManager(mode=mode, sync_interval_hours=interval, pull_on_start=True)
sync_mgr.start_periodic_sync()   # only does something in 'periodic' mode
user_mgr = UserManager(sync_mgr)

chat_cache = {}   # simple cache to avoid repeated API calls

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
        time.sleep(0.3)

def message_handler(parsedMessages: list[Message]):
    global user_language

    for msg in parsedMessages:
        print(apiClient.get_chat_info(msg.chat_id),"is being checked!")
        keydata = None
        message_to_send:str = None
            # Optionally enrich with chat info (first time only)
        if not msg._chat_info:
            msg = parser.enrich_message_with_chat(apiClient, msg, chat_cache)

            print(f"📨 From: {msg.sender_display_name} ({msg.chat_id})")
            print(f"   Text: {msg.text}")
            print(f"   Type: {'Private' if msg.is_private else 'Group'}")
            print(f"   Username: {msg.sender_username}")
        
        user = user_mgr.get(msg.sender_id, msg.chat_id)


        if msg.text == "/start":
            
            if not sync_mgr.user_exists(msg.sender_id, msg.chat_id):
                # The user does not exist
                send_sex_selection_keyboard(msg.chat_id)
                print("user not found and should create it")

            else:
                print("user found ",msg.sender_full_name,sync_mgr.get_user(msg.sender_id,msg.chat_id).sex)
                # The user already exists, so we just send the main page
                message_to_send = lang.get_text("welcome",user_language)
                keydata = get_main_page_keydata()
        
        elif msg.text == lang.get_text("iam_girl", user_language):
            print("it's a girl")
            if user == None:
                # If the user does not exist
                user = user_mgr.get_or_create(msg.sender_id,msg.chat_id)
                print("created:",msg.sender_full_name)

                user = user_mgr.get_or_create(msg.sender_id, msg.chat_id,username=msg.sender_username, first_name=msg.sender_first_name, last_name=msg.sender_last_name)
                user_mgr.set_sex(user, 2)
                user_mgr.set_age(user, -1)
                user_mgr.set_language(user, "fa")
                apiClient.send_message(msg.chat_id,lang.get_text("please_select_your_age", user.language))




        elif msg.text == lang.get_text("iam_boy", user_language):
            print("it's a boy")
            if user == None:
                # If the user does not exist
                user = user_mgr.get_or_create(msg.sender_id,msg.chat_id)
                print("created:",apiClient.get_chat_info(msg.chat_id))

                user_mgr.set_sex(user, 1)
                user_mgr.set_age(user,-1)
                user_mgr.set_language(user, "fa")
                apiClient.send_message(msg.chat_id, lang.get_text("please_select_your_age", user.language))

        elif user.age == -1:
            # User's age is invalid
            age_number = -1
            try:
                age_number = int(msg.text.strip())
            except Exception as e:
                traceback.print_exc()
                
            if age_number<10 or age_number > 99:
                # age is invalid
                apiClient.send_message(msg.chat_id, lang.get_text("please_input_a_valid_age",user.language))

            else:
                # age is valid
                user_mgr.set_age(user,age_number)
                message_to_send = lang.get_text("your_age_is_set_now_you_can_play", user.language)
                keydata = get_main_page_keydata()

        
        elif msg.text.startswith(lang.get_text("my_age_is", user_language)):
            age = int(msg.text.replace(lang.get_text("my_age_is", user_language), ""))
            user = sync_mgr.get_user(msg.sender_id, msg.chat_id)
            
            if user:
                user_mgr.set_age(user, age)
                message_to_send = lang.get_text("your_age_is_set_now_you_can_play", user.language)
                keydata = get_main_page_keydata()
            else:
                print("user not found when setting age, this should not happen!")


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

        elif msg.text == lang.get_text("key_truth"):
            keydata = get_keydata_truth_selected()
            message_to_send = lang.get_text("you_selected_truth", user_language)
            random_truth_question = lang.get_text("truth_questions")
            message_to_send += "\n" + random_truth_question
            message_to_send_to_oponent = lang.get_text("other_player_question_is_this") + random_truth_question
            apiClient.send_message(connection_between_players.forward_message(msg.chat_id,""),message_to_send_to_oponent)

        elif msg.text == lang.get_text("key_dare"):
            keydata = get_keydata_dare_selected()
            message_to_send = lang.get_text("you_selected_dare", user_language)
            random_dare_task = lang.get_text("dare_tasks", user_language)
            message_to_send = "\n" + random_dare_task
            message_to_send_to_oponent = lang.get_text("other_player_task_is_this") + random_dare_task
            apiClient.send_message(connection_between_players.forward_message(msg.chat_id,""),message_to_send_to_oponent)



        elif msg.text == lang.get_text("key_skip_the_question", user_language):
            # Just send a new question or task without changing the type (truth or dare)
            if connection_between_players.is_connected(msg.chat_id):
                # Check the type of the current question (truth or dare) and send a new one of the same type
                message_to_send = lang.get_text("you_selected_truth", user_language)
                random_truth_question = lang.get_text("truth_questions")
                message_to_send += "\n" + random_truth_question
                message_to_send_to_oponent = lang.get_text("other_player_skipped_new_question_is_this") + random_truth_question
                apiClient.send_message(connection_between_players.forward_message(msg.chat_id,""),message_to_send_to_oponent)
                keydata = get_keydata_truth_selected()
        
        elif msg.text == lang.get_text("key_skip_the_task", user_language):
            # Just send a new question or task without changing the type (truth or dare)
            if connection_between_players.is_connected(msg.chat_id):
                # Check the type of the current question (truth or dare) and send a new one of the same type
                message_to_send = lang.get_text("you_selected_dare", user_language)
                random_dare_task = lang.get_text("dare_tasks", user_language)
                message_to_send = "\n" + random_dare_task
                message_to_send_to_oponent = lang.get_text("other_player_skipped_new_task_is_this") + random_dare_task
                apiClient.send_message(connection_between_players.forward_message(msg.chat_id,""),message_to_send_to_oponent)

                keydata = get_keydata_dare_selected()


        elif msg.text in [lang.get_text("key_answered_the_question", user_language), lang.get_text("key_did_the_task", user_language)]:
            # Now it's the other player's turn to choose truth or dare, so we just send the main options again
            send_keypad_with_message_to_other_player(msg)
            keydata = get_keydata_player_connected()
            message_to_send = lang.get_text("you_answered_the_question_now_its_other_players_turn", user_language)

        
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
            keypad.send_message_with_keypad(connected_player_chat_id, lang.get_text("you_were_in_queue_and_now_connected_to_somebody"),get_keydata_player_connected())            
            keypad.send_message_with_keypad(msg.chat_id, lang.get_text("you_are_now_connected_to_somebody"),get_keydata_player_connected_with_truth_dare())            

def get_main_page_keydata():
    key_play_with_stranger = keypad.create_simple_button(1, lang.get_text("play_with_stranger",user_language))
    key_play_with_girl = keypad.create_simple_button(2, lang.get_text("play_with_girl", user_language))
    key_play_with_boy = keypad.create_simple_button(3, lang.get_text("play_with_boy", user_language))
    key_play_with_friend = keypad.create_simple_button(5, lang.get_text("play_with_friend",user_language))
    key_get_coin = keypad.create_simple_button(4, lang.get_text("get_coin"))
    row1 = keypad.create_keypad_row([key_play_with_stranger])
    row2 = keypad.create_keypad_row([key_play_with_girl, key_play_with_boy])
    row3 = keypad.create_keypad_row([key_get_coin])
    keydata = keypad.build_keypad([row1,row2, row3])
    return keydata

def get_keydata_player_connected():
    key_disconnect_the_connection = keypad.create_simple_button(1, lang.get_text("disconnect_the_connection", user_language))
    row1 = keypad.create_keypad_row([key_disconnect_the_connection])
    keydata = keypad.build_keypad([row1])
    return keydata

def get_keydata_player_connected_with_truth_dare():
    key_disconnect_the_connection = keypad.create_simple_button(1, lang.get_text("disconnect_the_connection", user_language))
    key_truth = keypad.create_simple_button(1, lang.get_text("key_truth", user_language))
    key_dare = keypad.create_simple_button(1, lang.get_text("key_dare", user_language))
    row1 = keypad.create_keypad_row([key_truth,key_dare])
    row2 = keypad.create_keypad_row([key_disconnect_the_connection])
    keydata = keypad.build_keypad([row1,row2])
    return keydata

def get_cancel_the_search_keydata():
    key_cancel_the_search = keypad.create_simple_button(1, lang.get_text("cancel_the_search", user_language))
    row1 = keypad.create_keypad_row([key_cancel_the_search])
    keydata = keypad.build_keypad([row1])
    return keydata

def get_keydata_truth_selected():
    key_skip_the_question = keypad.create_simple_button(1, lang.get_text("key_skip_the_question", user_language))
    key_disconnect_the_connection = keypad.create_simple_button(1, lang.get_text("disconnect_the_connection", user_language))
    key_answered_the_question = keypad.create_simple_button(1, lang.get_text("key_answered_the_question", user_language))
    row1 = keypad.create_keypad_row([key_skip_the_question, key_answered_the_question])
    row2 = keypad.create_keypad_row([key_disconnect_the_connection])
    keydata = keypad.build_keypad([row1,row2])
    return keydata

def get_keydata_dare_selected():
    key_skip_the_question = keypad.create_simple_button(1, lang.get_text("key_skip_the_task", user_language))
    key_disconnect_the_connection = keypad.create_simple_button(1, lang.get_text("disconnect_the_connection", user_language))
    key_answered_the_question = keypad.create_simple_button(1, lang.get_text("key_did_the_task", user_language))
    row1 = keypad.create_keypad_row([key_skip_the_question, key_answered_the_question])
    row2 = keypad.create_keypad_row([key_disconnect_the_connection])
    keydata = keypad.build_keypad([row1,row2])
    return keydata


def send_keypad_with_message_to_other_player(msg:Message):
    if connection_between_players.is_connected(msg.chat_id):
        # Just send the main options again (truth or dare)
        keypad.send_message_with_keypad(connection_between_players.forward_message(msg.chat_id, ""), lang.get_text("your_turn_to_choose", user_language), get_keydata_player_connected_with_truth_dare())

def forward_message_to_connected_player(msg:Message, user_language = "fa"):
    # if msg.text == lang.get_text("play_with_stranger",user_language):
    #     # Return because this message is a command and should not be sent to the other player
    #     return
    apiClient.send_message(connection_between_players.forward_message(msg.chat_id, msg.text), msg.text)

def send_sex_selection_keyboard(chat_id):
    key_iam_girl = keypad.create_simple_button(1, lang.get_text("iam_girl", user_language))
    key_iam_boy = keypad.create_simple_button(1, lang.get_text("iam_boy", user_language))
    row1 = keypad.create_keypad_row([key_iam_boy, key_iam_girl])
    keydata = keypad.build_keypad([row1],True,one_time_keyboard=True)
    keypad.send_message_with_keypad(chat_id, lang.get_text("please_select_your_sex", user_language), keydata)

def load_from_local_storage() -> dict:
    try:
        with open(LOCAL_SAVE_NAME, 'r') as f:
            return json.load(f)
    except Exception as e:
        traceback.print_exc()
        return None
    


if __name__ == "__main__" :
    main()