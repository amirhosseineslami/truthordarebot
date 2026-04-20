from botApiClient import BotApiClient
from keypad import Keypad
import time
import traceback
from rubikaMessageParser import RubikaMessageParser
from rubikaMessageParser import Message
from language import lang
from models.offset import Offset

# Init components
apiClient = BotApiClient()
keypad = Keypad()
message_update_offset_id ="69e600ad7c391e142a2e4c6a"
parser = RubikaMessageParser()

def main():


    # Bot is running
    bot_running = True
    print("bot is running")


    # Get the last message update offset id
    global message_update_offset_id
    new_message_update_offset_id = Offset.get()
    if new_message_update_offset_id:
        if new_message_update_offset_id != "0":
            message_update_offset_id = new_message_update_offset_id
            print("##############"+message_update_offset_id)

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
                Offset.store(message_update_offset_id)
                
            

        except Exception as e:
            traceback.print_exc()
        print(time.time())
        time.sleep(1)

def message_handler(parsedMessages: list[Message]):
    user_language = 'fa'

    for msg in parsedMessages:
        print(f"{msg.sender_id} in {msg.chat_id}: {msg.text} is being checked!")
        keydata = None

        if msg.text == "/start":
            # welcome message
            message_to_send = lang.get_text("welcome",user_language)
            key_play_with_stranger = keypad.create_simple_button(1, lang.get_text("play_with_stranger",user_language))
            key_play_with_friend = keypad.create_simple_button(2, lang.get_text("play_with_firend",user_language))
            key_get_coin = keypad.create_simple_button(3, lang.get_text("get_coin"))
            row1 = keypad.create_keypad_row([key_play_with_stranger, key_play_with_friend])
            row2 = keypad.create_keypad_row([key_get_coin])
            keydata = keypad.build_keypad([row1,row2])

        elif msg.text == lang.get_text("play_with_stranger", user_language):
            # stranger game
            message_to_send = lang.get_text("stranger")
            key_cancel_the_search = keypad.create_simple_button(4, lang.get_text("cancel_the_search", user_language))
            row1 = keypad.create_keypad_row([key_cancel_the_search])
            keydata = keypad.build_keypad([row1])


        if keydata != None and message_to_send:
            keypad.send_message_with_keypad(msg.chat_id, message_to_send, keydata)
            keydata = None

    
if __name__ == "__main__" :
    main()