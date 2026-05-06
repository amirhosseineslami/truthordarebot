import time
import traceback
import json
from typing import List, Optional
from functools import partial
from bot.models.user import User
from bot.models.sync_manager import SyncManager, UserManager
from bot.core.apiClient import BotApiClient
from email import message
from matplotlib import text
from bot.core.apiClient import BotApiClient
from bot.handlers.keypad import Keypad
import time
import traceback
from bot.handlers.rubikaMessageParser import CallbackQuery, RubikaParser, Chat, Message
from bot.managers.languageManager import lang
from bot.models.offset import Offset
from bot.managers.connection_manager import ConnectionManager
import json
from bot.models.sync_manager import SyncManager, UserManager,LocalUser
from bot.managers.flood_manager import flood_manager
import random
import traceback
from bot.models.database import init_db
import asyncio
# After initializing apiClient, user_mgr, and keypad
from bot.managers.group_game_manager_truth_dare import init_group_game_manager
from bot.managers.languageManager import LanguageManager



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

user_language = "fa"

# At startup, choose mode (e.g., via environment variable)
import os
mode = os.environ.get('BOT_MODE', 'periodic')   # 'online', 'offline', 'periodic'
interval = int(os.environ.get('SYNC_INTERVAL_HOURS', 1))

sync_mgr = SyncManager(mode=mode, sync_interval_hours=interval, pull_on_start=True)
sync_mgr.start_periodic_sync()   # only does something in 'periodic' mode
user_mgr = UserManager(sync_mgr)

chat_cache = {}   # simple cache to avoid repeated API calls
COIN_INVITATION_NUMBER = 3
CHAT_ID_ADMIN = os.environ.get('CHAT_ID_ADMIN', None)

ADVERTISMENT_TIME_THRESHOLD = float(os.environ.get('ADVERTISMENT_TIME_THRESHOLD', 300))
CHAT_ID_GROUP = os.environ.get('CHAT_ID_GROUP')


CHANNEL_INFORM_ADMIN = os.environ.get("CHANNEL_INFORM_ADMIN")



AUTHORIZE_GROUP_LINK = os.environ.get("GROUP_LINK_MOSHAVERE")
AUTHORIZE_GROUP_CHAT_ID = os.environ.get("GROUP_CHAT_ID_MOSHAVERE")
ADVERTISMENT_THRESHOLD = int(os.environ.get("ADVERTISMENT_THRESHOLD", 30))

#payment manager
from bot.managers.payment_manager import PaymentManager
from bot.models.payment import Payment
send_message_func = lambda chat_id, text: apiClient.send_message(chat_id, text)  # adapt to your send method
payment_mgr = PaymentManager(sync_mgr, user_mgr, send_message_func)

# Build reverse mapping: display_name -> product_id (once, outside the loop)
# Build reverse mapping: button_label -> product_id
PRODUCT_BUTTON_TO_ID = {}
for pid, info in PaymentManager.PRODUCTS.items():
    button_label = f"{info['name']} - {info['amount']:,} تومان"
    PRODUCT_BUTTON_TO_ID[button_label] = pid


group_game_manager = init_group_game_manager(apiClient, user_mgr)
advertisment_counter = {}
lang = LanguageManager()  # Initialize language manager (if needed)


class MessageResponseHandler:


    def __init__(self, apiClient: BotApiClient):
        self.connection_between_players = ConnectionManager()
        self.keypad = keypad
        self.apiClient = apiClient
        self.lang = lang
        self.user_language = user_language
        self.user_mgr = user_mgr
        self.sync_mgr = sync_mgr
        self.parser = parser

    def handle_one_message(self, msg: Message):
        
        # Flood manager
        user_id = msg.sender_id
        chat_id = msg.chat_id
        user = None
        user_language = 'fa'


        keydata = None
        message_to_send:str = None
            # Optionally enrich with chat info (first time only)

        if not msg._chat_info:
            msg = parser.enrich_message_with_chat(apiClient, msg, chat_cache)
            print(f"📨 From: {msg.sender_display_name} ({msg._chat_info.title}) {msg.sender_username}:{msg.chat_id}")
            print(f"   Text: {msg.text}")
            print(f"   Type: {msg.get_chat_type()}")
            print(f"   Username: {msg.sender_username}")
            print(f"   Time: {time.ctime(msg.time)}")


        # 1. Get user from DB (to check if already banned)
        if user_id or chat_id:
            try:
                user = user_mgr.get(user_id=user_id, chat_id=chat_id)  # returns LocalUser or None
                if user:
                    user_language = user.language   
                    print(f"   Name: {user.display_name()}({user.username})")

            except Exception as e:
                print("User is not available:", user_id, chat_id)
        

        if user and user.is_banned:
            # User is blocked – ignore completely
            print(f"Blocked user {user_id} tried to send a message. Ignoring.")
            return

        
        if not (msg.is_group or msg.is_channel):
                
            # ----- Anti‑flood check -----
            # 2. Flood detection
            is_flood, should_warn, strike = flood_manager.check_and_record(user_id)

            if is_flood:
                if should_warn:
                    # First warning
                    apiClient.send_message(chat_id,
                        "⚠️ شما بیش از حد مجاز پیام ارسال می‌کنید.\n"
                        "در صورت ادامه، حساب شما مسدود و به پلتفرم گزارش خواهد شد.")
                elif strike >= flood_manager.max_strikes:
                    # Block the user permanently
                    if user:
                        user.is_banned = True
                        user_mgr.sync.update_user(user)   # sync to local & remote
                    else:
                        # Create user record just to ban them
                        user = user_mgr.get_or_create(user_id, chat_id, is_banned=True)
                        user.is_banned = True
                        user_mgr.sync.update_user(user)

                    # Optional: report to Rubika (admin or log)
                    self.report_to_rubika(user_id, chat_id)   # see function below

                    apiClient.send_message(chat_id,
                        "🚫 شما به دلیل ارسال بیش از حد مجاز پیام مسدود شدید.\n"
                        "دیگر نمی‌توانید از ربات استفاده کنید.")
                    return   # Stop further processing

                # If flood but not yet blocked, we drop the message (don't process commands)
                return

            # ----- Normal message processing (continue with your existing logic) -----
            # ... rest of your handler (commands, pairing, etc.)


        if msg.is_group:

            if msg.chat_id == AUTHORIZE_GROUP_CHAT_ID and msg.text == (lang.get_text("/active" or lang.get_text("/activate"))):

                if user == None:
                    apiClient.send_message(msg.chat_id, lang.get_text("you_are_not_a_user_first_sign_up_in_the_bot"), reply_to_message_id= msg.message_id)
                    return
                
                #This group is our group for authorization
                self.do_user_authorization_process(user,chat_id, msg)

            else:
                #This is a normal message
                self.handle_one_message_in_the_group(user, msg)

        
        elif msg.is_channel:
            if msg.chat_id == CHANNEL_INFORM_ADMIN:
                for user in user_mgr.get_all_users():
                    user:LocalUser = user
                    if user.chat_id != CHAT_ID_ADMIN:
                        continue

                    try:
                        apiClient.send_message(user.chat_id, msg.text)
                    except Exception as e:
                        self.send_message_to_admin(f"{user.user_id}, {user.chat_id}")
            

        elif msg.text == lang.get_text("iam_girl", user_language):
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
                user_mgr.deactivate_user(user)
                self.apiClient.send_message(msg.chat_id,lang.get_text("please_select_your_age", user.language))

        elif msg.text == lang.get_text("iam_boy", user_language):
            print("it's a boy")
            if user == None:
                # If the user does not exist
                user = user_mgr.get_or_create(msg.sender_id,msg.chat_id)
                user_mgr.set_sex(user, 1)
                user_mgr.set_first_name(user,msg.sender_first_name)
                user_mgr.set_last_name(user,msg.sender_last_name)
                user_mgr.set_username(user,msg.sender_username)
                user_mgr.set_age(user,-1)
                user_mgr.set_language(user, "fa")
                user_mgr.deactivate_user(user)
                apiClient.send_message(msg.chat_id, lang.get_text("please_select_your_age", user.language))

        elif msg.text == lang.get_text("/start",user_language) or user == None:
            
            if user == None:
                # The user does not exist
                send_sex_selection_keyboard(msg.chat_id)
                print("user not found and should create it")

            else:
                print("user found ",msg.sender_full_name,sync_mgr.get_user(msg.sender_id,msg.chat_id).sex)
                # The user already exists, so we just send the main page
                message_to_send = lang.get_text("welcome",user_language)
                keydata = self.get_main_page_keydata()


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
                self.keypad.send_message_with_keypad(msg.chat_id, message_to_send, self.get_main_page_keydata())


        elif not user.is_active:
            message_to_send = lang.get_text("you_must_join_the_group_and_send_a_message_to_activate_the_bot", user.language).format(GROUP_LINK = AUTHORIZE_GROUP_LINK)
            self.apiClient.send_message(msg.chat_id, message_to_send)

        
        elif msg.text.startswith(lang.get_text("my_age_is", user_language)):
            age = int(msg.text.replace(lang.get_text("my_age_is", user_language), ""))
            user = self.sync_mgr.get_user(msg.sender_id, msg.chat_id)
            
            if user:
                user_mgr.set_age(user, age)
                message_to_send = lang.get_text("your_age_is_set_now_you_can_play", user.language)
                keydata = self.get_main_page_keydata()
            else:
                print("user not found when setting age, this should not happen!")


        elif msg.text.strip().lower().startswith(lang.get_text("play_with_stranger", user_language).lower()):
            # Play
            self.play_with_stranger(msg, user)

        elif msg.text == lang.get_text("play_with_girl", user.language):
            self.play_with_stranger(msg, user, 2)

        elif msg.text == lang.get_text("play_with_boy", user.language):
            self.play_with_stranger(msg, user, 1)

        elif msg.text == lang.get_text("cancel_the_search", user_language):
            # canceled the search
            message_to_send = lang.get_text("search_is_canceled_by_user", user_language)
            self.connection_between_players.remove_from_waiting_queue(msg.chat_id)
            keydata = self.get_main_page_keydata()

        elif msg.text == lang.get_text("disconnect_the_connection", user_language):

            # Notify the current user about disconnection
            message_to_send = lang.get_text("your_disconnect_request_is_accepted", user_language)
            keydata = self.get_main_page_keydata()

            # Notify the opposite user about disconnection status
            keypad.send_message_with_keypad(self.connection_between_players.forward_message(msg.chat_id, ""), lang.get_text("other_user_disconnected"),self.get_main_page_keydata())

            # Remove the connection between these 2 players
            self.connection_between_players.disconnect(msg.chat_id)

        elif msg.text == lang.get_text("key_truth"):
            keydata = self.get_keydata_truth_selected()
            message_to_send = lang.get_text("you_selected_truth", user_language)
            random_truth_question = lang.get_text("truth_questions")
            message_to_send += "\n" + random_truth_question
            message_to_send_to_oponent = lang.get_text("other_player_question_is_this") + random_truth_question
            self.apiClient.send_message(self.connection_between_players.forward_message(msg.chat_id,""),message_to_send_to_oponent)

        elif msg.text == lang.get_text("key_dare"):
            keydata = self.get_keydata_dare_selected()
            message_to_send = lang.get_text("you_selected_dare", user_language)
            random_dare_task = lang.get_text("dare_tasks", user_language)
            message_to_send = "\n" + random_dare_task
            message_to_send_to_oponent = lang.get_text("other_player_task_is_this") + random_dare_task
            self.apiClient.send_message(self.connection_between_players.forward_message(msg.chat_id,""),message_to_send_to_oponent)



        elif msg.text == lang.get_text("key_skip_the_question", user_language):
            # Just send a new question or task without changing the type (truth or dare)
            if self.connection_between_players.is_connected(msg.chat_id):
                # Check the type of the current question (truth or dare) and send a new one of the same type
                message_to_send = lang.get_text("you_selected_truth", user_language)
                random_truth_question = lang.get_text("truth_questions")
                message_to_send += "\n" + random_truth_question
                message_to_send_to_oponent = lang.get_text("other_player_skipped_new_question_is_this") + random_truth_question
                self.apiClient.send_message(self.connection_between_players.forward_message(msg.chat_id,""),message_to_send_to_oponent)
                keydata = self.get_keydata_truth_selected()
        
        elif msg.text == lang.get_text("key_skip_the_task", user_language):
            # Just send a new question or task without changing the type (truth or dare)
            if self.connection_between_players.is_connected(msg.chat_id):
                # Check the type of the current question (truth or dare) and send a new one of the same type
                message_to_send = lang.get_text("you_selected_dare", user_language)
                random_dare_task = lang.get_text("dare_tasks", user_language)
                message_to_send = "\n" + random_dare_task
                message_to_send_to_oponent = lang.get_text("other_player_skipped_new_task_is_this") + random_dare_task
                self.apiClient.send_message(self.connection_between_players.forward_message(msg.chat_id,""),message_to_send_to_oponent)

                keydata = self.get_keydata_dare_selected()

        elif msg.text == lang.get_text("back_to_main_menu",user_language):
            message_to_send = lang.get_text("welcome_back_to_main_menu", user_language)
            self.keypad.send_message_with_keypad(msg.chat_id, message_to_send, self.get_main_page_keydata())


        elif msg.text in [lang.get_text("key_answered_the_question", user_language), lang.get_text("key_did_the_task", user_language)]:
            # Now it's the other player's turn to choose truth or dare, so we just send the main options again
            self.send_keypad_with_message_to_other_player(msg)
            keydata = self.get_keydata_player_connected()
            message_to_send = lang.get_text("you_answered_the_question_now_its_other_players_turn", user_language)

        elif msg.text == lang.get_text("get_coin", user_language):
            self.send_keypad_coin_status_pressed(msg, user)

        elif msg.text == lang.get_text("buy_premium_account", user_language):
            message_to_send = lang.get_text("premium_account_benefits_are_this", user_language) + "\n" + lang.get_text("premium_account_benefits_list", user_language)
            message_to_send += "\n" + lang.get_text("to_buy_premium_account_press_the_button_below", user.language)
            self.buy_premium_account_keydata(msg,user)
        
        # Forward the message if there's any connection for this user
        elif self.connection_between_players.is_connected(msg.chat_id):
            self.forward_message_to_connected_player(msg)


        # Inside message handler
        elif msg.text == "/buy":
            products_kb = self.get_products_keypad()
            self.keypad.send_message_with_keypad(msg.chat_id, "🛒 محصولات:", products_kb)

        elif msg.text == lang.get_text("/play_in_group", user_language):
            message_to_send = lang.get_text("to_play_in_group_join_a_group_make_the_bot_admin_and_send_command_/game", user_language)
            keydata = self.get_main_page_keydata()

        # Inside message handler:
        elif msg.text in PRODUCT_BUTTON_TO_ID:
            product_id = PRODUCT_BUTTON_TO_ID[msg.text]
            print("Creating purchase for product:", product_id)
            user = user_mgr.get_or_create(msg.sender_id, msg.chat_id)
            result = payment_mgr.create_purchase(user, msg.chat_id, product_id)
            if result['success']:
                self.keypad.send_message_with_keypad(msg.chat_id, f"💰 مبلغ {result['amount']:,} تومان\n🔗 برای پرداخت کلیک کنید:\n{result['payment_link']}\n\n⏳ لینک ۳۰ دقیقه معتبر است.\nبعد از پرداخت /check را بزنید یا منتظر بمانید.", self.get_check_purchase_keydata(user))
            else:
                self.send_message_to_admin(f"❌ Error creating purchase for user {user.user_id} ({user.chat_id}): {result.get('error')}")         
                self.apiClient.send_message(msg.chat_id, lang.get_text("purchase_is_not_available_now_try_later", user.language))

            # Check if there is any keypad to send
            if keydata != None and message_to_send:
                self.keypad.send_message_with_keypad(msg.chat_id, message_to_send, keydata)
                keydata = None


        elif msg.text == lang.get_text("/check",user_language):
            try:
                res = payment_mgr.manual_check(msg.sender_id)
                if res.get('success'):
                    if res.get('already_paid'):
                        self.apiClient.send_message(msg.chat_id, "✅ پرداخت قبلاً تأیید شده است.")
                    else:
                        self.apiClient.send_message(msg.chat_id, "✅ پرداخت با موفقیت تأیید شد! از سرویس استفاده کنید.")
                else:
                    error = res.get('error', 'خطای ناشناخته')
                    self.apiClient.send_message(msg.chat_id, f"❌ {error}\nلطفاً بعد از انجام پرداخت دوباره /check را بزنید.")
            except Exception as e:
                print(f"Error in /check: {traceback.format_exception(e)}")
                self.apiClient.send_message(msg.chat_id, "❌ خطایی رخ داد. لطفاً بعداً تلاش کنید.")

        elif msg.text == lang.get_text("/active", user_language):
            if not user.is_active:
                self.apiClient.send_message(msg.chat_id, lang.get_text("you_must_not_send_this_message_here_join_the_group_and_send_a_message_to_activate_the_bot", user.language).format(
                    GROUP_LINK=AUTHORIZE_GROUP_LINK
                ))
                return
            else:
                self.apiClient.send_message(msg.chat_id, lang.get_text("you_are_already_signed_up_use_the_bot", user_language))

        elif msg.text.startswith(lang.get_text("invite", user.language)):
            if user.level != 1:
                # The user is invited before!
                self.apiClient.send_message(msg.chat_id, lang.get_text("you_are_invited_one_time_before", user.language))
                return
            
            invite_code = msg.text.replace(lang.get_text("invite", user.language), "").strip()
            if invite_code:
                inviter_user = user_mgr.get(chat_id=invite_code)
                if inviter_user and invite_code != msg.chat_id:
                    # Add coins to both inviter and invitee
                    user_mgr.add_coins(inviter_user, COIN_INVITATION_NUMBER)
                    user_mgr.add_coins(user, COIN_INVITATION_NUMBER)
                    user_mgr.set_level(user, user.level+1)  # Mark the user as having been invited
                    apiClient.send_message(msg.chat_id, f"🎉 شما با موفقیت دعوت شدید! {COIN_INVITATION_NUMBER} سکه به شما و دعوت‌کننده اضافه شد.")
                    apiClient.send_message(inviter_user.chat_id, f"🎉 کاربر جدیدی با کد دعوت شما ثبت‌نام کرد! {COIN_INVITATION_NUMBER} سکه به شما اضافه شد.")
                else:
                    apiClient.send_message(msg.chat_id, "❌ کد دعوت نامعتبر است.")
            else:
                apiClient.send_message(msg.chat_id, "❌ لطفاً یک کد دعوت معتبر وارد کنید.")



        if message_to_send != None and keydata != None:
            keypad.send_message_with_keypad(msg.chat_id,message_to_send,keydata)
            message_to_send = None
            keydata = None
            
    def do_user_authorization_process(self, user:LocalUser, chat_id, msg:Message):

            
        apiClient.delete_message(chat_id,msg.message_id)

        if user:
            # activation process
            try:
                user_mgr.activate_user(user)
                keypad.send_message_with_keypad(user.chat_id, self.lang.get_text("the_activation_process_was_successful", self.user_language), self.get_main_page_keydata())
                apiClient.send_message(self.AUTHORIZE_GROUP_CHAT_ID, self.lang.get_text("the_activation_process_was_successful", self.user_language))
            except Exception as e:
                print(e.__format__(traceback))

        else:
            self.apiClient.send_message(self.AUTHORIZE_GROUP_CHAT_ID, self.lang.get_text("the_activation_process_was_not_successful_you_must_first_sign_up", self.user_language))

    def handle_one_message_in_the_group(self, user: LocalUser, msg: Message):
        """
        Handle messages in group chats - only processes game-related commands
        and ignores all other messages. Uses send_message only (no keypads).
        """

        self.advertisment_in_the_group(msg, user)

        chat_id = msg.chat_id
        
        if not group_game_manager:
            self.apiClient.send_message(AUTHORIZE_GROUP_CHAT_ID, f"❌ Group game manager is not defined. Chat: {msg.chat_id}, MsgID: {msg.message_id}")
            return
        
        text = msg.text.strip().lower() if msg.text else ""
        
        # ========================================
        # Game-related commands only
        # ========================================
        
        # List of game commands that should be processed (including new host commands)
        GAME_COMMANDS = {
            "/game", "/go", "/end", "/status", "/leave",
            "/truth", "/dare", "/ask", "/done", "/skip", "/gamehelp", "هستم",
            "/answered", "/host_skip", "/host_add_points", "/host_end", 
            "/host_next", "/host_kick", "/host_limit", "فعال", "/start", "فعالسازی", "/command"
        }
        
        # Check for commands with arguments like /answer something, /truth easy, /truth medium, /truth hard
        is_answer_command = text.startswith("/answer ")
        is_truth_with_difficulty = text.startswith("/truth ")
        is_dare_with_difficulty = text.startswith("/dare ")
        is_addq_command = text.startswith("/addq ")
        is_host_add_points = text.startswith("/host_add_points ")
        is_host_skip = text.startswith("/host_skip ")
        is_host_kick = text.startswith("/host_kick ")
        is_host_limit = text.startswith("/host_limit ")
        
        # If message is not a game command, ignore it completely
        if not (text in GAME_COMMANDS or is_answer_command or is_addq_command or 
                is_truth_with_difficulty or is_dare_with_difficulty or
                is_host_add_points or is_host_skip or is_host_kick or is_host_limit):
            # Check if user is in pending question state (after /ask) - special case
            game = group_game_manager.active_games.get(chat_id)
            if not (game and game.pending_action and game.current_turn == msg.sender_id):
                # Ignore - not a game message
                return
        
        # ========================================
        # Check if user is active (only for commands)
        # ========================================

        if user is None:
            apiClient.send_message(
                chat_id,
                lang.get_text("you_are_not_a_user_first_sign_up_in_the_bot"),
                reply_to_message_id=msg.message_id
            )
            return

        
        # Get display name using available fields
        username_part = f" @{user.username}" if user.username else ""
        display_name = f"{user.display_name()}{username_part}".strip()
        sender_id = msg.sender_id
        
        # ========================================
        # Process Game Commands
        # ========================================


        # Help command
        if  text == "/help" or text == "/gamehelp" or text == "فعال" or text == "فعالسازی" or text == "/start":
            help_text = (
                "🎮 **راهنمای بازی گروهی** 🎮\n\n"
                "📋 **دستورات عمومی:**\n"
                "• `/game` - شروع بازی جدید (میزبان)\n"
                "• `هستم` - پیوستن به بازی\n"
                "• `/go` - شروع بازی (فقط میزبان)\n"
                "• `/status` - مشاهده وضعیت بازی\n"
                "• `/leave` - خروج از بازی\n"
                "• `/end` - پایان بازی (فقط میزبان)\n\n"
                "🎲 برای دریافت همه دستورات /command را ارسال کنید.\n"
            )
            apiClient.send_message(chat_id, help_text)
            return
        
        
        # Help command
        if text.startswith("/command"):
            help_text = (
                "🎮 **راهنمای بازی گروهی** 🎮\n\n"
                "📋 **دستورات عمومی:**\n"
                "• `/game` - شروع بازی جدید (میزبان)\n"
                "• `هستم` - پیوستن به بازی\n"
                "• `/go` - شروع بازی (فقط میزبان)\n"
                "• `/status` - مشاهده وضعیت بازی\n"
                "• `/leave` - خروج از بازی\n"
                "• `/end` - پایان بازی (فقط میزبان)\n\n"
                "🎲 **دستورات نوبت:**\n"
                "• `/truth` - حقیقت معمولی (۵ امتیاز)\n"
                "• `/truth easy` - حقیقت آسان (۵ امتیاز)\n"
                "• `/truth medium` - حقیقت متوسط (۱۰ امتیاز)\n"
                "• `/truth hard` - حقیقت سخت (۱۵ امتیاز)\n"
                "• `/dare` - جرعت معمولی (۵ امتیاز)\n"
                "• `/dare easy` - جرعت آسان (۵ امتیاز)\n"
                "• `/dare medium` - جرعت متوسط (۱۰ امتیاز)\n"
                "• `/dare hard` - جرعت سخت (۱۵ امتیاز)\n"
                "• `/ask` - پرسیدن سوال از گروه\n"
                "• `/answered` - ثبت پاسخ (پس از پاسخ به سوال حقیقت)\n"
                "• `/done` - تکمیل چالش جرعت\n"
                "• `/skip` - رد کردن نوبت (کاهش ۵ امتیاز)\n\n"
                "💬 **دستورات پاسخ:**\n"
                "• `/answer <متن>` - پاسخ به سوال دیگران\n"
                "• `/addq <سوال>` - اضافه کردن سوال به بازی\n\n"
                "👑 **دستورات میزبان:**\n"
                "• `/host_skip @user` - رد کردن نوبت هر بازیکن\n"
                "• `/host_add_points @user 10` - اضافه/کم کردن امتیاز (بین -20 تا +50)\n"
                "• `/host_end` - پایان فوری بازی\n"
                "• `/host_next` - اجبار به نوبت بعدی\n"
                "• `/host_kick @user` - اخراج بازیکن از بازی\n"
                "• `/host_limit easy/medium/hard` - محدودیت سطح سختی\n\n"
                "💡 **نکات:**\n"
                "• فقط میزبان می‌تواند بازی را شروع و پایان دهد\n"
                "• حداقل ۲ بازیکن برای شروع بازی نیاز است\n"
                "• به هر پاسخ بر اساس سطح سختی امتیاز تعلق می‌گیرد\n"
                "• رد کردن نوبت ۵ امتیاز از دست می‌دهد\n"
                "• بازی گروهی فقط در گروه‌ها قابل انجام است"
            )
            apiClient.send_message(chat_id, help_text)
            return
        
        # ========================================
        # Host Management Commands
        # ========================================
        
        # Host skip player
        if text.startswith("/host_skip "):
            target = text[11:].strip()  # Remove "/host_skip "
            # Extract user_id from mention or username
            # You'll need to implement a helper to resolve @username to user_id
            # For simplicity, assume target is user_id or mention
            success, response = group_game_manager.host_skip_player(chat_id, sender_id, target)
            apiClient.send_message(chat_id, response)
            return
        
        # Host add points
        if text.startswith("/host_add_points "):
            parts = text[17:].strip().split()
            if len(parts) < 2:
                apiClient.send_message(chat_id, "❌ استفاده: `/host_add_points @user امتیاز`")
                return
            target = parts[0]
            try:
                points = int(parts[1])
            except ValueError:
                apiClient.send_message(chat_id, "❌ امتیاز باید عدد باشد!")
                return
            success, response = group_game_manager.host_add_points(chat_id, sender_id, target, points)
            apiClient.send_message(chat_id, response)
            return
        
        # Host end game immediately
        if text == "/host_end":
            success, response = group_game_manager.host_end_game_immediately(chat_id, sender_id)
            apiClient.send_message(chat_id, response)
            return
        
        # Host force next turn
        if text == "/host_next":
            success, response = group_game_manager.host_force_next_turn(chat_id, sender_id)
            apiClient.send_message(chat_id, response)
            return
        
        # Host kick player
        if text.startswith("/host_kick "):
            target = text[11:].strip()
            success, response = group_game_manager.host_remove_player(chat_id, sender_id, target)
            apiClient.send_message(chat_id, response)
            return
        
        # Host set difficulty limit
        if text.startswith("/host_limit "):
            difficulty = text[12:].strip().lower()
            success, response = group_game_manager.host_set_difficulty_limit(chat_id, sender_id, difficulty)
            apiClient.send_message(chat_id, response)
            return
        
        # ========================================
        # Player Commands
        # ========================================
        
        # Answered command (confirm answer for truth)
        if text == "/answered":
            success, response = group_game_manager.handle_answered(chat_id, sender_id)
            apiClient.send_message(chat_id, response)
            return
        
        # Start new game (host)
        if text == "/game":
            success, response = group_game_manager.create_game(chat_id, sender_id, display_name)
            apiClient.send_message(chat_id, response)
            return
        
        # Join game
        if text == "هستم":
            success, response = group_game_manager.add_player(chat_id, sender_id, msg.sender_username, display_name)
            apiClient.send_message(chat_id, response)
            return
        
        # Leave game
        if text == "/leave":
            success, response = group_game_manager.remove_player(chat_id, sender_id)
            apiClient.send_message(chat_id, response)
            return
        
        # Start the game (host only)
        if text == "/go":
            success, response = group_game_manager.start_game(chat_id, sender_id)
            apiClient.send_message(chat_id, response)
            return
        
        # End game (host only)
        if text == "/end":
            success, response = group_game_manager.end_game(chat_id, sender_id)
            apiClient.send_message(chat_id, response)
            return
        
        # Game status
        if text == "/status":
            status = group_game_manager.get_game_status(chat_id)
            apiClient.send_message(chat_id, status)
            return
        
        # Truth command with optional difficulty
        if text.startswith("/truth"):
            difficulty = None
            if len(text) > 6:  # "/truth " is 6 chars
                difficulty = text[6:].strip().lower()
                if difficulty not in ['easy', 'medium', 'hard']:
                    apiClient.send_message(chat_id, "❌ سطح نامعتبر! استفاده: `/truth easy`, `/truth medium`, `/truth hard`")
                    return
            success, response = group_game_manager.handle_truth_with_difficulty(chat_id, sender_id, difficulty)
            apiClient.send_message(chat_id, response)
            return
        
        # Dare command with optional difficulty
        if text.startswith("/dare"):
            difficulty = None
            if len(text) > 5:  # "/dare " is 5 chars
                difficulty = text[5:].strip().lower()
                if difficulty not in ['easy', 'medium', 'hard']:
                    apiClient.send_message(chat_id, "❌ سطح نامعتبر! استفاده: `/dare easy`, `/dare medium`, `/dare hard`")
                    return
            success, response = group_game_manager.handle_dare_with_difficulty(chat_id, sender_id, difficulty)
            apiClient.send_message(chat_id, response)
            return
            
            
        # Ask command (custom question to specific player or current player)
        if text == "/ask":
            # Ask the current player
            success, response = group_game_manager.handle_ask(chat_id, sender_id, None)
            apiClient.send_message(chat_id, response)
            return

        if text.startswith("/ask @"):
            # Ask a specific player (format: /ask @username)
            target_mention = text[5:].strip()  # Remove "/ask "
            # You'll need to resolve @username to user_id
            # For now, you can extract the username
            target_username = target_mention.lstrip('@')
            # Find user by username (you'll need a helper function)
            target_user = user_mgr.find_by_username(target_username)
            if target_user:
                success, response = group_game_manager.handle_ask(chat_id, sender_id, target_user.user_id)
            else:
                apiClient.send_message(chat_id, "❌ کاربر مورد نظر یافت نشد!")
            return
        
        # Done command (complete dare)
        if text == "/done":
            success, response = group_game_manager.handle_done(chat_id, sender_id)
            apiClient.send_message(chat_id, response)
            return
        
        # Skip command (skip turn)
        if text == "/skip":
            success, response = group_game_manager.handle_skip(chat_id, sender_id)
            apiClient.send_message(chat_id, response)
            return
        
        # Answer command (answer a question)
        if text.startswith("/answer "):
            answer = text[8:]  # Remove "/answer "
            if not answer.strip():
                apiClient.send_message(chat_id, "❌ لطفاً پاسخ خود را بعد از /answer بنویسید.\nمثال: `/answer پاسخ من`")
                return
            success, response = group_game_manager.handle_answer(chat_id, sender_id, answer)
            apiClient.send_message(chat_id, response)
            return
        
        # Add custom question command
        if text.startswith("/addq "):
            question = text[6:]  # Remove "/addq "
            if not question.strip():
                apiClient.send_message(chat_id, "❌ لطفاً سوال خود را بعد از /addq بنویسید.\nمثال: `/addq سوال من`")
                return
            success, response = group_game_manager.add_custom_question(chat_id, sender_id, question)
            apiClient.send_message(chat_id, response)
            return
        
        # Custom question text (after /ask)
        game = group_game_manager.active_games.get(chat_id)
        if game and game.pending_action and game.current_turn == sender_id:
            if not text.strip():
                apiClient.send_message(chat_id, "❌ لطفاً یک سوال معتبر بپرسید.")
                return
            success, response = group_game_manager.handle_custom_question(chat_id, sender_id, text)
            apiClient.send_message(chat_id, response)
            return
        

    def advertisment_in_the_group(self, msg:Message, user: LocalUser):
        # This function can be used to send periodic advertisements or messages in the group
        # For example, you can send a message every hour about the bot's features or updates
        global advertisment_counter
        if msg.chat_id in advertisment_counter:
            advertisment_counter[msg.chat_id][0] += 1
            print(f"Advertisement counter{msg._chat_info.title}:", advertisment_counter[msg.chat_id])

            if advertisment_counter[msg.chat_id][0] >= ADVERTISMENT_THRESHOLD and time.time() > advertisment_counter[msg.chat_id][1] + ADVERTISMENT_TIME_THRESHOLD:  # Adjust the threshold as needed
                self.apiClient.send_message(msg.chat_id, lang.get_text("the_activation_process_was_successful"))
                self.send_message_to_admin(f"Advertisement sent to group {msg.chat_id}{msg._chat_info.title} after {advertisment_counter} messages.")
                advertisment_counter[msg.chat_id][0] = 0
                advertisment_counter[msg.chat_id][1] = time.time()
        else:
            advertisment_counter[msg.chat_id] = [1, time.time()]
            
    def send_message_to_admin(self, text):
        self.apiClient.send_message(CHANNEL_INFORM_ADMIN, text)

    def report_to_rubika(self, user_id: str, chat_id: str):
        """
        Send a report to a dedicated admin chat or log to a file.
        Rubika does not have a public report API; you can notify your moderation team.
        """
        admin_chat_id = "admin_chat_id_here"   # Replace with your admin chat ID
        message = f"🚨 کاربر {user_id} به دلیل هرزنامه (flood) مسدود شد."
        try:
            self.send_message_to_admin(message)

        except Exception as e:
            print(f"Could not send admin report: {e}")
        # Also log to file
        with open("flood_reports.log", "a") as f:
            f.write(f"{time.time()}: Banned {user_id} (chat {chat_id})\n")

    def play_with_stranger(self, msg: Message, user: LocalUser, preferred_gender: int = -1):
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
        self.connection_between_players.set_user_preferences(
            chat_id=chat_id,
            gender=user.sex,
            preferred_gender=preferred_gender,
            is_pro=is_pro
        )

        # Check if already in a connection
        if self.connection_between_players.is_connected(chat_id):
            self.keypad.send_message_with_keypad(
                chat_id, 
                lang.get_text("already_connected", user.language), 
                self.get_keydata_player_connected()
            )
            return

        # Check if already waiting
        if self.connection_between_players.is_in_queue(chat_id):
            self.keypad.send_message_with_keypad(
                chat_id, 
                lang.get_text("already_waiting", user.language), 
                self.get_cancel_the_search_keydata()
            )
            return
        
        if(preferred_gender == -1):
            # User is using normal search
            pass

        elif(user.coin > 0):
            # User has coin and using gender filter
            self.user_mgr.remove_coins(user, 1)

        else:
            # User does not have enough coin
            self.keypad.send_message_with_keypad(
                chat_id, 
                lang.get_text("not_enough_coin", user.language), 
                self.get_main_page_keydata()
            )
            return

        # Try to pair with the best waiting partner
        # The pair_random method now handles:
        # - Searching pro queue first
        # - Gender compatibility checking
        # - Fallback to regular queue
        matched = self.connection_between_players.pair_random(chat_id, username)
        is_connected = self.connection_between_players.is_connected(chat_id)

        if is_connected:
            # Successfully paired!
            other_chat_id, other_username = matched
            
            # Get other user's info for better messaging
            other_user = user_mgr.get(chat_id=other_chat_id)
            other_display_name = other_user.first_name if other_user else other_username
            
            # Notify both users about successful connection
            self.keypad.send_message_with_keypad(
                other_chat_id,
                self.lang.get_text("you_were_in_queue_and_now_connected_to_somebody"),
                self.get_keydata_player_connected()
            )
            
            self.keypad.send_message_with_keypad(
                chat_id,
                self.lang.get_text("you_are_now_connected_to_somebody"),
                self.get_keydata_player_connected_with_truth_dare()
            )
            
            # Optional: Send a welcome message with each other's names
            message_to_send_current_player=lang.get_text("connected_with", user_language=user.language).format(name=other_display_name)
            keypad.send_message_with_keypad(
                chat_id,
                message_to_send_current_player,
                self.get_keydata_player_connected_with_truth_dare()
            )

            # Optional: Send a welcome message with current player's names
            message_to_send_oponent_player=lang.get_text("connected_with", user_language=other_user.language).format(name=user.first_name)
            keypad.send_message_with_keypad(
                other_chat_id,
                message_to_send_oponent_player,
                self.get_keydata_player_connected()
            )
            
            
            print(f"✅ Paired: {chat_id} <-> {other_chat_id}")
            
        else:
            # No partner available – add to waiting queue
            # The add_to_waiting_queue will automatically place user in pro or regular queue
            self.connection_between_players.add_to_waiting_queue(chat_id, username)
            
            # Get queue stats for better feedback
            queue_stats = self.connection_between_players.get_queue_stats()
            
            # Send appropriate message based on queue position
            position = self.connection_between_players.get_queue_position(chat_id)
            
            if queue_stats['pro_waiting'] > 0 and is_pro:
                position_msg = self.lang.get_text("queue_position_pro", self.user_language, position=position)
            else:
                position_msg = self.lang.get_text("queue_position", self.user_language, position=position)
            
            keypad.send_message_with_keypad(
                chat_id, 
                self.lang.get_text("stranger"), 
                self.get_cancel_the_search_keydata()
            )
            
            print(f"➕ {chat_id} added to queue. Position: {position}. "
                f"Pro queue: {queue_stats['pro_waiting']}, "
                f"Regular queue: {queue_stats['regular_waiting']}")
            
    def get_check_purchase_keydata(self,user):
        key_check = keypad.create_simple_button(675, self.lang.get_text("/check",self.user_language))
        key_back_to_main_menu = keypad.create_simple_button(1,self.lang.get_text("back_to_main_menu",self.user_language))
        row1 = keypad.create_keypad_row([key_check])
        row2 = keypad.create_keypad_row([key_back_to_main_menu])
        return keypad.build_keypad([row1, row2])

    def get_main_page_keydata(self):
        key_play_with_stranger = keypad.create_simple_button(1, self.lang.get_text("play_with_stranger", self.user_language))
        key_play_with_girl = keypad.create_simple_button(2, self.lang.get_text("play_with_girl", self.user_language))
        key_play_with_boy = keypad.create_simple_button(3, self.lang.get_text("play_with_boy", self.user_language))
        key_play_in_group = keypad.create_simple_button(5, self.lang.get_text("/play_in_group", self.user_language))
        key_get_coin = keypad.create_simple_button(4, self.lang.get_text("get_coin"))
        key_buy_premium_account = keypad.create_simple_button(6, self.lang.get_text("buy_premium_account"))
        row1 = keypad.create_keypad_row([key_play_with_stranger, key_play_in_group])
        row2 = keypad.create_keypad_row([key_play_with_girl, key_play_with_boy])
        row3 = keypad.create_keypad_row([key_get_coin, key_buy_premium_account])
        keydata = keypad.build_keypad([row1,row2, row3])
        return keydata

    def get_keydata_player_connected(self):
        key_disconnect_the_connection = keypad.create_simple_button(1, self.lang.get_text("disconnect_the_connection", self.user_language))
        row1 = keypad.create_keypad_row([key_disconnect_the_connection])
        keydata = keypad.build_keypad([row1])
        return keydata

    def get_keydata_player_connected_with_truth_dare(self):
        key_disconnect_the_connection = keypad.create_simple_button(1, self.lang.get_text("disconnect_the_connection", self.user_language))
        key_truth = keypad.create_simple_button(1, self.lang.get_text("key_truth", self.user_language))
        key_dare = keypad.create_simple_button(1, self.lang.get_text("key_dare", self.user_language))
        row1 = keypad.create_keypad_row([key_truth,key_dare])
        row2 = keypad.create_keypad_row([key_disconnect_the_connection])
        keydata = keypad.build_keypad([row1,row2])
        return keydata

    def get_cancel_the_search_keydata(self):
        key_cancel_the_search = keypad.create_simple_button(1, self.lang.get_text("cancel_the_search", self.user_language))
        row1 = keypad.create_keypad_row([key_cancel_the_search])
        keydata = keypad.build_keypad([row1])
        return keydata

    def get_keydata_truth_selected(self):
        key_skip_the_question = keypad.create_simple_button(1, self.lang.get_text("key_skip_the_question", self.user_language))
        key_disconnect_the_connection = keypad.create_simple_button(1, self.lang.get_text("disconnect_the_connection", self.user_language))
        key_answered_the_question = keypad.create_simple_button(1, self.lang.get_text("key_answered_the_question", self.user_language))
        row1 = keypad.create_keypad_row([key_skip_the_question, key_answered_the_question])
        row2 = keypad.create_keypad_row([key_disconnect_the_connection])
        keydata = keypad.build_keypad([row1,row2])
        return keydata

    def get_keydata_dare_selected(self):
        key_skip_the_question = keypad.create_simple_button(1, self.lang.get_text("key_skip_the_task", self.user_language))
        key_disconnect_the_connection = keypad.create_simple_button(1, self.lang.get_text("disconnect_the_connection", self.user_language))
        key_answered_the_question = keypad.create_simple_button(1, self.lang.get_text("key_did_the_task", self.user_language))
        row1 = keypad.create_keypad_row([key_skip_the_question, key_answered_the_question])
        row2 = keypad.create_keypad_row([key_disconnect_the_connection])
        keydata = keypad.build_keypad([row1,row2])
        return keydata

    def send_keypad_with_message_to_other_player(self, msg:Message):
        if self.connection_between_players.is_connected(msg.chat_id):
            # Just send the main options again (truth or dare)
            self.keypad.send_message_with_keypad(self.connection_between_players.forward_message(msg.chat_id, ""), self.lang.get_text("your_turn_to_choose", self.user_language), self.get_keydata_player_connected_with_truth_dare())

    def forward_message_to_connected_player(self, msg:Message, user_language = "fa"):
        # if msg.text == lang.get_text("play_with_stranger",user_language):
        #     # Return because this message is a command and should not be sent to the other player
        #     return
        self.apiClient.send_message(self.connection_between_players.forward_message(msg.chat_id, msg.text), msg.text)

    def send_sex_selection_keyboard(self, chat_id):
        key_iam_girl = self.keypad.create_simple_button(1, self.lang.get_text("iam_girl", self.user_language))
        key_iam_boy = self.keypad.create_simple_button(1, self.lang.get_text("iam_boy", self.user_language))
        row1 = self.keypad.create_keypad_row([key_iam_boy, key_iam_girl])
        keydata = self.keypad.build_keypad([row1],True,one_time_keyboard=True)
        self.keypad.send_message_with_keypad(chat_id, self.lang.get_text("please_select_your_sex", self.user_language), keydata)

    def buy_premium_account_keydata(self, msg, user:LocalUser):
        products_kb = self.get_products_keypad(user)
        self.keypad.send_message_with_keypad(msg.chat_id, self.lang.get_text("products", user.language), products_kb)

    def send_keypad_coin_status_pressed(self, msg:Message, user:LocalUser):
        message_to_send = self.lang.get_text("your_coin_number",user.language).format(coin=user.coin)
        message_to_send += self.lang.get_text("you_can_get_coins_by_inviting_friends_and_your_invite_code_is", user.language).format(coin_invitation_number = COIN_INVITATION_NUMBER)
        message_to_send += "\n"+self.lang.get_text("invite", user.language)+ msg.chat_id
        key_buy_premium = self.keypad.create_simple_button("1023",self.lang.get_text("buy_premium_account",user.language))
        key_back_to_main_menu = self.keypad.create_simple_button(1,self.lang.get_text("back_to_main_menu",user.language))
        row1 = self.keypad.create_keypad_row([key_buy_premium])
        row2 = self.keypad.create_keypad_row([key_back_to_main_menu])
        self.keypad.send_message_with_keypad(msg.chat_id, message_to_send, self.keypad.build_keypad([row1, row2]))

    def load_from_local_storage(self) -> dict:
        try:
            with open(LOCAL_SAVE_NAME, 'r') as f:
                return json.load(f)
        except Exception as e:
            traceback.print_exc()
            return None
        
    # Product inline keypad builder
    def get_products_keypad(self, user:LocalUser):
        kp = Keypad()
        rows = []
        for pid, info in PaymentManager.PRODUCTS.items():
            btn = kp.create_simple_button(pid, f"{info['name']} - {info['amount']:,} تومان")
            rows.append(kp.create_keypad_row([btn]))

        rows.append(kp.create_keypad_row([kp.create_simple_button(314,self.lang.get_text("back_to_main_menu",user.language))]))
        return kp.build_keypad(rows)
