from botApiClient import BotApiClient
from keypad import Keypad
import time
import traceback
from rubikaMessageParser import CallbackQuery, RubikaParser, Chat, Message
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
mode = os.environ.get('BOT_MODE', 'periodic')   # 'online', 'offline', 'periodic'
interval = int(os.environ.get('SYNC_INTERVAL_HOURS', 2))

sync_mgr = SyncManager(mode=mode, sync_interval_hours=interval, pull_on_start=True)
sync_mgr.start_periodic_sync()   # only does something in 'periodic' mode
user_mgr = UserManager(sync_mgr)

chat_cache = {}   # simple cache to avoid repeated API calls
CODE_INVITATION_NUMBER = 5

#payment manager
from payment_manager import PaymentManager
from models.payment import Payment
send_message_func = lambda chat_id, text: apiClient.send_message(chat_id, text)  # adapt to your send method
payment_mgr = PaymentManager(sync_mgr, user_mgr, send_message_func)

# Build reverse mapping: display_name -> product_id (once, outside the loop)
# Build reverse mapping: button_label -> product_id
PRODUCT_BUTTON_TO_ID = {}
for pid, info in PaymentManager.PRODUCTS.items():
    button_label = f"{info['name']} - {info['amount']:,} تومان"
    PRODUCT_BUTTON_TO_ID[button_label] = pid


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

def message_handler(parsed_response: list[Message]):
    global user_language
    for item in parsed_response:
        handle_one_message(item)

def handle_one_message(msg: Message):
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



    if msg.text == lang.get_text("iam_girl", user_language):
        print("it's a girl")
        if user == None:
            # If the user does not exist
            user = user_mgr.get_or_create(msg.sender_id,msg.chat_id)
            print("created:",msg.sender_full_name)

            user = user_mgr.get_or_create(msg.sender_id, msg.chat_id,username=msg.sender_username, first_name=msg.sender_first_name, last_name=msg.sender_last_name)
            user_mgr.set_sex(user, 2)
            user_mgr.set_first_name(user,msg.sender_first_name)
            user_mgr.set_last_name(user,msg.sender_last_name)
            user_mgr.set_username(user,msg.sender_username)
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
            user_mgr.set_first_name(user,msg.sender_first_name)
            user_mgr.set_last_name(user,msg.sender_last_name)
            user_mgr.set_username(user,msg.sender_username)
            user_mgr.set_age(user,-1)
            user_mgr.set_language(user, "fa")
            apiClient.send_message(msg.chat_id, lang.get_text("please_select_your_age", user.language))

    elif msg.text == "/start" or user == None:
        
        if user == None:
            # The user does not exist
            send_sex_selection_keyboard(msg.chat_id)
            print("user not found and should create it")

        else:
            print("user found ",msg.sender_full_name,sync_mgr.get_user(msg.sender_id,msg.chat_id).sex)
            # The user already exists, so we just send the main page
            message_to_send = lang.get_text("welcome",user_language)
            keydata = get_main_page_keydata()


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
        play_with_stranger(msg, user)

    elif msg.text == lang.get_text("play_with_girl"):
        play_with_stranger(msg, user, 2)

    elif msg.text == lang.get_text("play_with_boy"):
        play_with_stranger(msg, user, 1)

    elif msg.text == lang.get_text("cancel_the_search", user_language):
        # canceled the search
        message_to_send = lang.get_text("search_is_canceled_by_user", user_language)
        connection_between_players.remove_from_waiting_queue(msg.chat_id)
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

    elif msg.text == lang.get_text("back_to_main_menu",user_language):
        message_to_send = lang.get_text("welcome_back_to_main_menu", user_language)
        keypad.send_message_with_keypad(msg.chat_id, message_to_send, get_main_page_keydata())


    elif msg.text in [lang.get_text("key_answered_the_question", user_language), lang.get_text("key_did_the_task", user_language)]:
        # Now it's the other player's turn to choose truth or dare, so we just send the main options again
        send_keypad_with_message_to_other_player(msg)
        keydata = get_keydata_player_connected()
        message_to_send = lang.get_text("you_answered_the_question_now_its_other_players_turn", user_language)

    elif msg.text == lang.get_text("get_coin", user_language):
        coin_status_pressed(msg, user)

    elif msg.text == lang.get_text("buy_premium_account", user_language):
        message_to_send = lang.get_text("premium_account_benefits_are_this", user_language) + "\n" + lang.get_text("premium_account_benefits_list", user_language)
        message_to_send += "\n" + lang.get_text("to_buy_premium_account_press_the_button_below", user.language)
        buy_premium_account_keydata(msg,user)
    
    # Forward the message if there's any connection for this user
    elif connection_between_players.is_connected(msg.chat_id):
        forward_message_to_connected_player(msg)


    # Inside message handler
    elif msg.text == "/buy":
        products_kb = get_products_keypad()
        keypad.send_message_with_keypad(msg.chat_id, "🛒 محصولات:", products_kb)

    # Inside message handler:
    elif msg.text in PRODUCT_BUTTON_TO_ID:
        product_id = PRODUCT_BUTTON_TO_ID[msg.text]
        print("Creating purchase for product:", product_id)
        user = user_mgr.get_or_create(msg.sender_id, msg.chat_id)
        result = payment_mgr.create_purchase(user, msg.chat_id, product_id)
        if result['success']:
            apiClient.send_message(msg.chat_id, f"💰 مبلغ {result['amount']:,} تومان\n🔗 برای پرداخت کلیک کنید:\n{result['payment_link']}\n\n⏳ لینک ۳۰ دقیقه معتبر است.\nبعد از پرداخت /check را بزنید یا منتظر بمانید.")
        else:
            apiClient.send_message(msg.chat_id, f"❌ خطا: {result.get('error')}")
        # Check if there is any keypad to send
        if keydata != None and message_to_send:
            keypad.send_message_with_keypad(msg.chat_id, message_to_send, keydata)
            keydata = None


    elif msg.text == "/check":
        try:
            res = payment_mgr.manual_check(msg.sender_id)
            if res.get('success'):
                if res.get('already_paid'):
                    apiClient.send_message(msg.chat_id, "✅ پرداخت قبلاً تأیید شده است.")
                else:
                    apiClient.send_message(msg.chat_id, "✅ پرداخت با موفقیت تأیید شد! از سرویس استفاده کنید.")
            else:
                error = res.get('error', 'خطای ناشناخته')
                apiClient.send_message(msg.chat_id, f"❌ {error}\nلطفاً بعد از انجام پرداخت دوباره /check را بزنید.")
        except Exception as e:
            print(f"Error in /check: {traceback.format_exception(e)}")
            apiClient.send_message(msg.chat_id, "❌ خطایی رخ داد. لطفاً بعداً تلاش کنید.")

    elif msg.text.startswith("invite"):
        if user.level != 1:
            # The user is invited before!
            apiClient.send_message(msg.chat_id, lang.get_text("you_are_invited_one_time_before", user.language))
            return
        
        invite_code = msg.text.replace("invite", "").strip()
        if invite_code:
            inviter_user = user_mgr.get(chat_id=invite_code)
            if inviter_user and invite_code != msg.chat_id:
                # Add coins to both inviter and invitee
                user_mgr.add_coins(inviter_user, 5)
                user_mgr.add_coins(user, 5)
                user_mgr.set_level(user, user.level+1)  # Mark the user as having been invited
                apiClient.send_message(msg.chat_id, f"🎉 شما با موفقیت دعوت شدید! 5 سکه به شما و دعوت‌کننده اضافه شد.")
                apiClient.send_message(inviter_user.chat_id, f"🎉 کاربر جدیدی با کد دعوت شما ثبت‌نام کرد! 5 سکه به شما اضافه شد.")
            else:
                apiClient.send_message(msg.chat_id, "❌ کد دعوت نامعتبر است.")
        else:
            apiClient.send_message(msg.chat_id, "❌ لطفاً یک کد دعوت معتبر وارد کنید.")

    if message_to_send != None and keydata != None:
        keypad.send_message_with_keypad(msg.chat_id,message_to_send,keydata)
        message_to_send = None
        keydata = None
        

# def manual_check(self, user_id: str) -> dict:
#     """Called when user types /check"""
#     # Find the most recent pending payment for this user
#     try:
#         from models.payment import Payment
#         payment = Payment.select().where(
#             (Payment.user_id == user_id) & (Payment.status == 'pending')
#         ).order_by(Payment.created_at.desc()).first()
#     except Exception as e:
#         return {'success': False, 'error': f'Database error: {e}'}

#     if not payment:
#         return {'success': False, 'error': 'No pending payment found'}

#     result = Payment.verify_payment(payment.track_id)
#     if result.get('success') and not result.get('already_paid'):
#         # Grant the purchased items
#         self._grant_purchase(payment)
#         self._stop_polling_for_user(user_id)
#     return result

# def play_with_stranger(msg:Message, user:LocalUser, gender_filter:int = -1):
#     is_pro = True if gender_filter != -1 else False

#     # remove this user from waiting queue if it's already in
#     if (connection_between_players.is_in_queue(msg.chat_id)):
#         connection_between_players.remove_from_waiting_queue(msg.chat_id)
#         print(msg.chat_id," removed from queue")
#         print("size of queue after remove:",connection_between_players.get_queue_size())

#     if(connection_between_players.get_queue_size() < 1):

#         # Add if it's not already in the queue
#         if not connection_between_players.is_in_queue(msg.chat_id):
#             connection_between_players.set_user_preferences(msg.chat_id, user.sex, gender_filter, is_pro)
#             connection_between_players.add_to_waiting_queue(msg.chat_id,msg.sender_id)
#             print(msg.chat_id, "Added to queue!")
#             keypad.send_message_with_keypad(msg.chat_id, lang.get_text("stranger"), get_cancel_the_search_keydata())

#         # Add the user to the searching list
#         print(connection_between_players.get_queue_size(),"This is the new queue size")
    
#     else:
#         connection_between_players.set_user_preferences(user.chat_id, user.sex, gender_filter, is_pro)
#         random_pair = connection_between_players.pair_random(msg.chat_id, msg.sender_id)
#         # Connect the user to another waiting player
#         if random_pair != None:
#             connected_player_chat_id, connected_player_username = random_pair

#             # Send message to both connected players that they're connected now!
#             keypad.send_message_with_keypad(connected_player_chat_id, lang.get_text("you_were_in_queue_and_now_connected_to_somebody"),get_keydata_player_connected())            
#             keypad.send_message_with_keypad(msg.chat_id, lang.get_text("you_are_now_connected_to_somebody"),get_keydata_player_connected_with_truth_dare())        
#         else:
#             connection_between_players.add_to_waiting_queue(user.chat_id, user.username, user.sex, gender_filter, is_pro)    
#             print(msg.chat_id, "Added to queue!")
#             keypad.send_message_with_keypad(msg.chat_id, lang.get_text("stranger"), get_cancel_the_search_keydata())

def play_with_stranger(msg: Message, user: LocalUser, preferred_gender: int = -1):
    """
    Initiate a stranger pairing request with priority matching.
    
    Args:
        msg: The message object from the user
        user: The LocalUser object (from sync_manager)
        preferred_gender: -1 (any), 1 (male), 2 (female)
    """
    chat_id = msg.chat_id
    username = msg.sender_id or msg.sender_display_name

    # ✅ CORRECT: Pro status from user's actual subscription, NOT from gender filter
    is_pro = True if preferred_gender != 0 else False  # This should be a property of LocalUser

    # ✅ Set/update user preferences BEFORE any queue operations
    connection_between_players.set_user_preferences(
        chat_id=chat_id,
        gender=user.sex,
        preferred_gender=preferred_gender,
        is_pro=is_pro
    )

    # Check if already in a connection
    if connection_between_players.is_connected(chat_id):
        keypad.send_message_with_keypad(
            chat_id, 
            lang.get_text("already_connected", user.language), 
            get_keydata_player_connected()
        )
        return

    # Check if already waiting
    if connection_between_players.is_in_queue(chat_id):
        keypad.send_message_with_keypad(
            chat_id, 
            lang.get_text("already_waiting", user.language), 
            get_cancel_the_search_keydata()
        )
        return
    
    if(preferred_gender == -1):
        # User is using normal search
        pass

    elif(user.coin > 0):
        # User has coin and using gender filter
        user_mgr.remove_coins(user, 1)

    else:
        # User does not have enough coin
        keypad.send_message_with_keypad(
            chat_id, 
            lang.get_text("not_enough_coin", user.language), 
            get_main_page_keydata()
        )
        return

    # Try to pair with the best waiting partner
    # The pair_random method now handles:
    # - Searching pro queue first
    # - Gender compatibility checking
    # - Fallback to regular queue
    matched = connection_between_players.pair_random(chat_id, username)
    is_connected = connection_between_players.is_connected(chat_id)

    if is_connected:
        # Successfully paired!
        other_chat_id, other_username = matched
        
        # Get other user's info for better messaging
        other_user = user_mgr.get(chat_id=other_chat_id)
        other_display_name = other_user.first_name if other_user else other_username
        
        # Notify both users about successful connection
        keypad.send_message_with_keypad(
            other_chat_id,
            lang.get_text("you_were_in_queue_and_now_connected_to_somebody"),
            get_keydata_player_connected()
        )
        
        keypad.send_message_with_keypad(
            chat_id,
            lang.get_text("you_are_now_connected_to_somebody"),
            get_keydata_player_connected_with_truth_dare()
        )
        
        # Optional: Send a welcome message with each other's names
        message_to_send_current_player=lang.get_text("connected_with", user_language=user.language).format(name=other_display_name)
        keypad.send_message_with_keypad(
            chat_id,
            message_to_send_current_player,
            get_keydata_player_connected_with_truth_dare()
        )

        # Optional: Send a welcome message with current player's names
        message_to_send_oponent_player=lang.get_text("connected_with", user_language=other_user.language).format(name=user.first_name)
        keypad.send_message_with_keypad(
            other_chat_id,
            message_to_send_oponent_player,
            get_keydata_player_connected()
        )
        
        
        print(f"✅ Paired: {chat_id} <-> {other_chat_id}")
        
    else:
        # No partner available – add to waiting queue
        # The add_to_waiting_queue will automatically place user in pro or regular queue
        connection_between_players.add_to_waiting_queue(chat_id, username)
        
        # Get queue stats for better feedback
        queue_stats = connection_between_players.get_queue_stats()
        
        # Send appropriate message based on queue position
        position = connection_between_players.get_queue_position(chat_id)
        
        if queue_stats['pro_waiting'] > 0 and is_pro:
            position_msg = lang.get_text("queue_position_pro", user.language, position=position)
        else:
            position_msg = lang.get_text("queue_position", user.language, position=position)
        
        keypad.send_message_with_keypad(
            chat_id, 
            lang.get_text("stranger"), 
            get_cancel_the_search_keydata()
        )
        
        print(f"➕ {chat_id} added to queue. Position: {position}. "
              f"Pro queue: {queue_stats['pro_waiting']}, "
              f"Regular queue: {queue_stats['regular_waiting']}")
        


def get_main_page_keydata():
    key_play_with_stranger = keypad.create_simple_button(1, lang.get_text("play_with_stranger",user_language))
    key_play_with_girl = keypad.create_simple_button(2, lang.get_text("play_with_girl", user_language))
    key_play_with_boy = keypad.create_simple_button(3, lang.get_text("play_with_boy", user_language))
    key_play_with_friend = keypad.create_simple_button(5, lang.get_text("play_with_friend",user_language))
    key_get_coin = keypad.create_simple_button(4, lang.get_text("get_coin"))
    key_buy_premium_account = keypad.create_simple_button(6, lang.get_text("buy_premium_account"))
    row1 = keypad.create_keypad_row([key_play_with_stranger])
    row2 = keypad.create_keypad_row([key_play_with_girl, key_play_with_boy])
    row3 = keypad.create_keypad_row([key_get_coin, key_buy_premium_account])
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

def buy_premium_account_keydata(msg,user):
    products_kb = get_products_keypad(user)
    keypad.send_message_with_keypad(msg.chat_id, "🛒 محصولات:", products_kb)

def coin_status_pressed(msg:Message,user:LocalUser):
    message_to_send = lang.get_text("your_coin_number",user.language).format(coin=user.coin)
    message_to_send += lang.get_text("you_can_get_coins_by_inviting_friends_and_your_invite_code_is", user.language).format(coin_invitation_number = CODE_INVITATION_NUMBER)
    message_to_send += "\n invite"+ msg.chat_id
    key_buy_premium = keypad.create_simple_button("1023",lang.get_text(lang.get_text("buy_premium_account"),user.language))
    key_back_to_main_menu = keypad.create_simple_button(1,lang.get_text("back_to_main_menu",user.language))
    row1 = keypad.create_keypad_row([key_buy_premium])
    row2 = keypad.create_keypad_row([key_back_to_main_menu])
    keypad.send_message_with_keypad(msg.chat_id, message_to_send, keypad.build_keypad([row1, row2]))

def load_from_local_storage() -> dict:
    try:
        with open(LOCAL_SAVE_NAME, 'r') as f:
            return json.load(f)
    except Exception as e:
        traceback.print_exc()
        return None
    

# Product inline keypad builder
def get_products_keypad(user:LocalUser):
    kp = Keypad()
    rows = []
    for pid, info in PaymentManager.PRODUCTS.items():
        btn = kp.create_simple_button(pid, f"{info['name']} - {info['amount']:,} تومان")
        rows.append(kp.create_keypad_row([btn]))

    rows.append(kp.create_keypad_row([kp.create_simple_button(314,lang.get_text("back_to_main_menu",user.language))]))
    return kp.build_keypad(rows)



if __name__ == "__main__" :
    main()