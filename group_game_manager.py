import random
import time
import threading
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

# ============================================
# Enums and Constants
# ============================================

class GameState(Enum):
    WAITING_PLAYERS = "waiting_players"
    READY_TO_START = "ready_to_start"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"

class TurnAction(Enum):
    TRUTH = "truth"
    DARE = "dare"
    ASK = "ask"

# Inactivity timeout constants (in seconds)
WARNING_TIMEOUT = 180      # 3 minutes - send warning
GAME_TIMEOUT = 300         # 5 minutes - end game


@dataclass
class GamePlayer:
    # Required fields (no defaults) - MUST come first
    user_id: str
    chat_id: str
    username: str
    display_name: str
    
    # Optional fields (with defaults) - MUST come after
    first_name: str = ""
    last_name: str = ""
    joined_at: datetime = field(default_factory=datetime.now)
    score: int = 0
    has_answered: bool = False
    turn_count: int = 0
    waiting_for_answer: bool = False

    
@dataclass
class GroupGame:
    group_id: str
    host_id: str
    state: GameState
    players: Dict[str, GamePlayer] = field(default_factory=dict)
    current_turn: Optional[str] = None
    pending_action: Optional[TurnAction] = None
    pending_question: Optional[str] = None
    last_action_time: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    warning_sent: bool = False  # Track if warning message has been sent

# ============================================
# Truth & Dare Questions Database
# ============================================

TRUTH_QUESTIONS = {
    'fa': [
        "تا حالا به کسی دروغ گفته‌ای که زندگیت رو تغییر بده؟",
        "سخت‌ترین تصمیمی که گرفتی چی بوده؟",
        "بزرگترین ترس تو چیه؟",
        "بهترین خاطره دوران کودکیت چیه؟",
        "تا حالا عاشق شدی؟ اگه آره براش چه کاری کردی؟",
        "چیزی که هیچ کس ازت نمی‌دونه رو بگو",
        "آخرین باری که گریه کردی کی بود؟",
        "تا حالا به معلمت دروغ گفتی؟",
        "گران‌ترین چیزی که خریدی چی بوده؟",
        "آرزوی بزرگت چیه؟"
    ],
    'en': [
        "Have you ever told a lie that changed your life?",
        "What's the hardest decision you've made?",
        "What's your biggest fear?",
        "What's your best childhood memory?",
        "Have you ever been in love? What did you do for them?",
        "Tell something nobody knows about you",
        "When was the last time you cried?",
        "Have you ever lied to your teacher?",
        "What's the most expensive thing you've bought?",
        "What's your biggest dream?"
    ]
}

DARE_ACTIONS = {
    'fa': [
        "یک آهنگ کوتاه بخون",
        "یک رقص انجام بده و ویدیو بفرست",
        "سه نفر از گروه رو معرفی کن و بگو ازشون خوشت میاد یا نه",
        "به یک دوستت زنگ بزن و بگو دوستت دارم",
        "یک عکس خنده‌دار از خودت بفرست",
        "برای 10 ثانیه مثل یه قورباغه قور قور کن",
        "به سه نفر از گروه تعریف کن",
        "یک راز بگو که تا حالا به کسی نگفتی",
        "حدس بزن کدوم بازیکن بیشترین امتیاز رو داره",
        "یک کار خوب برای یکی از اعضای گروه انجام بده"
    ],
    'en': [
        "Sing a short song",
        "Do a dance and send a video",
        "Introduce 3 people in the group and say if you like them or not",
        "Call a friend and say 'I love you'",
        "Send a funny picture of yourself",
        "Croak like a frog for 10 seconds",
        "Compliment three people in the group",
        "Tell a secret you've never told anyone",
        "Guess which player has the highest score",
        "Do something nice for another player"
    ]
}

# ============================================
# Main Group Game Manager Class (No Keypads)
# ============================================

class GroupGameManager:
    """
    Complete manager for group Truth/Dare games using only text commands.
    No keypads/inline keyboards - everything works with commands and mentions.
    """
    
    def __init__(self, api_client, user_mgr):
        self.api_client = api_client
        self.user_mgr = user_mgr
        self.active_games: Dict[str, GroupGame] = {}  # group_id -> GroupGame
        self.player_to_game: Dict[str, str] = {}      # user_id -> group_id
        self._cleanup_thread_started = False
    
    # ============================================
    # Inactivity Check & Auto Cleanup
    # ============================================
    
    def update_activity(self, group_id: str):
        """Update last activity time for a game (call on any game action)"""
        if group_id in self.active_games:
            self.active_games[group_id].last_action_time = datetime.now()
            self.active_games[group_id].warning_sent = False  # Reset warning flag on activity
    
    def check_inactive_games(self):
        """Check for inactive games and send warnings or end them"""
        now = datetime.now()
        games_to_end = []
        
        for group_id, game in self.active_games.items():
            if game.state != GameState.IN_PROGRESS:
                continue
            
            inactive_seconds = (now - game.last_action_time).total_seconds()
            
            # Check if game should be ended (5 minutes)
            if inactive_seconds >= GAME_TIMEOUT:
                games_to_end.append(group_id)
            
            # Check if warning should be sent (3 minutes) and not sent yet
            elif inactive_seconds >= WARNING_TIMEOUT and not game.warning_sent:
                game.warning_sent = True
                remaining = GAME_TIMEOUT - inactive_seconds
                self.api_client.send_message(
                    group_id,
                    f"⚠️ **اخطار! بازی {int(remaining//60)} دقیقه دیگر به دلیل عدم فعالیت بسته می‌شود!**\n\n"
                    f"لطفاً برای ادامه بازی یکی از دستورات را ارسال کنید:\n"
                    f"• /truth - حقیقت\n"
                    f"• /dare - جرعت\n"
                    f"• /ask - سوال از گروه\n"
                    f"• /skip - رد کردن نوبت\n\n"
                    f"در صورت عدم فعالیت، بازی به صورت خودکار پایان می‌یابد."
                )
        
        # End timed out games
        for group_id in games_to_end:
            self._auto_end_game(group_id)
    
    def _auto_end_game(self, group_id: str):
        """Automatically end an inactive game"""
        if group_id not in self.active_games:
            return
        
        game = self.active_games[group_id]
        
        # Find winner if there are players
        if game.players:
            winner = max(game.players.values(), key=lambda p: p.score)
            scores = "\n".join([f"  🎮 {p.display_name}: {p.score} امتیاز" 
                               for p in sorted(game.players.values(), key=lambda x: -x.score)])
            
            self.api_client.send_message(
                group_id,
                f"⏰ **بازی به دلیل عدم فعالیت به مدت {GAME_TIMEOUT//60} دقیقه پایان یافت!**\n\n"
                f"📊 امتیازات نهایی:\n{scores}\n\n"
                f"🎉 **برنده: {winner.display_name}** با {winner.score} امتیاز!\n\n"
                f"برای شروع بازی جدید /game را بفرستید."
            )
        else:
            self.api_client.send_message(
                group_id,
                f"⏰ **بازی به دلیل عدم فعالیت به مدت {GAME_TIMEOUT//60} دقیقه بسته شد.**\n"
                f"برای شروع بازی جدید /game را بفرستید."
            )
        
        self._cleanup_game(group_id)
    
    def start_inactivity_monitor(self):
        """Start background thread to monitor inactive games"""
        if self._cleanup_thread_started:
            return
        
        def monitor_loop():
            while True:
                time.sleep(60)  # Check every minute
                self.check_inactive_games()
        
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
        self._cleanup_thread_started = True
        print("✅ Inactivity monitor started (checking every minute)")
    
    # ============================================
    # Game Creation & Management
    # ============================================
    
    def create_game(self, group_id: str, host_id: str, host_username: str, 
                    host_display_name: str = "", host_first_name: str = "", host_last_name: str = "") -> Tuple[bool, str]:
        """Create a new game in the group and automatically add the host as a player"""
        if group_id in self.active_games:
            game = self.active_games[group_id]
            if game.state != GameState.FINISHED:
                return False, "❌ یک بازی در این گروه در حال اجراست! برای مشاهده وضعیت /status را بفرستید."
        
        game = GroupGame(
            group_id=group_id,
            host_id=host_id,
            state=GameState.WAITING_PLAYERS
        )
        
        # Create formatted name for host
        formatted_name = host_display_name
        if not formatted_name:
            if host_first_name and host_last_name:
                formatted_name = f"{host_first_name} {host_last_name}"
            elif host_first_name:
                formatted_name = host_first_name
            elif host_username:
                formatted_name = f"{host_username}"
            else:
                formatted_name = host_id
        
        # Automatically add the host as a player
        game.players[host_id] = GamePlayer(
            user_id=host_id,
            chat_id=group_id,
            username=host_username,
            display_name=formatted_name,
            first_name=host_first_name,
            last_name=host_last_name,
            joined_at=datetime.now(),
            score=0,
            has_answered=False,
            turn_count=0,
            waiting_for_answer=False
        )
        
        self.active_games[group_id] = game
        self.player_to_game[host_id] = group_id
        
        # Start inactivity monitor if not already started
        self.start_inactivity_monitor()
        
        return True, f"🎮 بازی جدید ایجاد شد!\n\n با فرستادن /gamehelp می توانید تمام دستورات بازی را مشاهده کنید. \n📝 قوانین:\n• کاربران برای پیوستن: 'هستم' بفرستند\n• میزبان بازی با /go بازی را شروع می‌کند\n • هر بازیکن می‌تواند حقیقت، جرعت یا سوال از گروه انتخاب کند\n• به هر پاسخ امتیاز تعلق می‌گیرد\n\n👑 شما میزبان بازی هستید و به عنوان بازیکن اضافه شدید!\n👥 بازیکنان فعلی: {formatted_name}"

    def add_player(self, group_id: str, user_id: str, username: str, 
                display_name: str, first_name: str = "", last_name: str = "") -> Tuple[bool, str]:
        """
        Add a player to the game
        
        Args:
            group_id: The group chat ID
            user_id: The user's unique ID
            username: The user's username (with @ or without)
            display_name: Formatted display name (first_name + last_name or username)
            first_name: User's first name (optional)
            last_name: User's last name (optional)
        """
        if group_id not in self.active_games:
            return False, "❌ هیچ بازی فعالی در این گروه وجود ندارد. ابتدا /game را بفرستید."
        
        game = self.active_games[group_id]
        
        if game.state != GameState.WAITING_PLAYERS:
            return False, "❌ بازی شروع شده و دیگر نمی‌توانید به آن بپیوندید."
        
        if user_id in game.players:
            return False, f"❌ {display_name} قبلاً به بازی پیوسته‌اید!"
        
        # Check if user exists in database
        user = self.user_mgr.get(user_id=user_id)
        if not user:
            user = self.user_mgr.get_or_create(
                user_id=user_id, 
                chat_id=group_id, 
                username=username,
                first_name=first_name,
                last_name=last_name
            )
        
        # Create formatted name for display
        formatted_name = display_name
        if not formatted_name:
            if first_name and last_name:
                formatted_name = f"{first_name} {last_name}"
            elif first_name:
                formatted_name = first_name
            elif username:
                formatted_name = f"@{username}"
            else:
                formatted_name = user_id
        
        game.players[user_id] = GamePlayer(
            user_id=user_id,
            chat_id=group_id,
            username=username,
            display_name=formatted_name,
            first_name=first_name,
            last_name=last_name,
            joined_at=datetime.now(),
            score=0,
            has_answered=False,
            turn_count=0,
            waiting_for_answer=False
        )
        self.player_to_game[user_id] = group_id
    
        return True, f"✅ {formatted_name} به بازی پیوست! ({len(game.players)} نفر در بازی)"


    def remove_player(self, group_id: str, user_id: str) -> Tuple[bool, str]:
        """Remove a player from the game"""
        if group_id not in self.active_games:
            return False, "❌ هیچ بازی فعالی وجود ندارد."
        
        game = self.active_games[group_id]
        
        if user_id not in game.players:
            return False, "❌ شما در این بازی نیستید."
        
        player = game.players[user_id]
        
        if game.state == GameState.WAITING_PLAYERS:
            game.players.pop(user_id)
            self.player_to_game.pop(user_id, None)
            self.update_activity(group_id)
            return True, f"👋 {player.display_name} از بازی خارج شد. ({len(game.players)} نفر باقی ماندند)"
        
        elif game.state == GameState.IN_PROGRESS:
            # Remove player from ongoing game (they forfeit)
            del game.players[user_id]
            self.player_to_game.pop(user_id, None)
            
            if len(game.players) < 2:
                self.end_game(group_id, game.host_id)
                return True, f"👋 {player.display_name} بازی را ترک کرد. تعداد بازیکنان به زیر ۲ رسید، بازی پایان یافت."
            
            # If it was current turn, move to next
            if game.current_turn == user_id:
                self._next_turn(group_id)
            
            self.update_activity(group_id)
            return True, f"👋 {player.display_name} بازی را ترک کرد. بازی ادامه دارد."
        
        return False, "نمی‌توانید در این مرحله خارج شوید."

    def start_game(self, group_id: str, host_id: str) -> Tuple[bool, str]:
        """Start the game when host sends /go"""
        if group_id not in self.active_games:
            return False, "❌ هیچ بازی فعالی وجود ندارد."
        
        game = self.active_games[group_id]
        
        if game.host_id != host_id:
            return False, "❌ فقط میزبان بازی می‌تواند آن را شروع کند!"
        
        if game.state != GameState.WAITING_PLAYERS:
            return False, "❌ بازی در حال اجراست یا تمام شده!"
        
        if len(game.players) < 2:
            return False, "❌ حداقل ۲ بازیکن برای شروع بازی نیاز است! (هم اکنون {} نفر)".format(len(game.players))
        
        game.state = GameState.IN_PROGRESS
        self.update_activity(group_id)
        
        # Select first random player
        first_player = random.choice(list(game.players.values()))
        game.current_turn = first_player.user_id
        
        # Announce game start
        players_list = "\n".join([f"  🎮 {p.display_name}" for p in game.players.values()])
        
        self.api_client.send_message(
            group_id,
            f"🎯 بازی شروع شد!\n\n👥 بازیکنان:\n{players_list}\n\n"
            f"🎲 **نوبت: {first_player.display_name}**\n\n"
            f"📖 دستورات موجود:\n"
            f"  • /truth - انتخاب حقیقت\n"
            f"  • /dare - انتخاب جرعت\n"
            f"  • /ask - پرسیدن سوال از گروه\n"
            f"  • /skip - رد کردن نوبت (کاهش امتیاز)\n"
            f"  • /answered - ثبت پاسخ (پس از پاسخ به سوال حقیقت)\n"
            f"  • /end - پایان بازی (فقط میزبان)\n"
            f"  • /status - مشاهده وضعیت بازی\n\n"
            f"{first_player.display_name}، نوبت شماست! از دستورات بالا استفاده کنید.\n\n"
            f"⚠️ **توجه:** در صورت عدم فعالیت به مدت 5 دقیقه، بازی به صورت خودکار پایان می‌یابد."
        )
        
        return True, "بازی شروع شد!"

    def end_game(self, group_id: str, host_id: str) -> Tuple[bool, str]:
        """End the game and announce winner"""
        if group_id not in self.active_games:
            return False, "❌ هیچ بازی فعالی وجود ندارد."
        
        game = self.active_games[group_id]
        
        if game.host_id != host_id:
            return False, "❌ فقط میزبان بازی می‌تواند آن را تمام کند!"
        
        if game.state != GameState.IN_PROGRESS:
            return False, "❌ بازی در حال اجرا نیست!"
        
        # Find winner (highest score)
        if game.players:
            winner = max(game.players.values(), key=lambda p: p.score)
            scores = "\n".join([f"  🎮 {p.display_name}: {p.score} امتیاز" for p in sorted(game.players.values(), key=lambda x: -x.score)])
            
            self.api_client.send_message(
                group_id,
                f"🏆 بازی به پایان رسید!\n\n📊 امتیازات نهایی:\n{scores}\n\n"
                f"🎉 **برنده: {winner.display_name}** با {winner.score} امتیاز!\n\n"
                f"🙏 از همه بازیکنان تشکر می‌کنیم!"
            )
        else:
            self.api_client.send_message(group_id, "🏆 بازی به پایان رسید! (بدون بازیکن)")
        
        game.state = GameState.FINISHED
        self._cleanup_game(group_id)
        
        return True, "بازی تمام شد!"

    # ============================================
    # Turn Management (Text Commands)
    # ============================================
    
    def handle_truth(self, group_id: str, user_id: str) -> Tuple[bool, str]:
        """Handle /truth command"""
        game = self._get_user_game(user_id, group_id)
        if not game:
            return False, "❌ شما در هیچ بازی فعالی نیستید یا بازی یافت نشد."
        
        self.update_activity(group_id)
        
        if game.current_turn != user_id:
            current_player = game.players.get(game.current_turn)
            current_name = current_player.display_name if current_player else "نامشخص"
            return False, f"❌ نوبت شما نیست! در حال حضر نوبت {current_name} است."
        
        player = game.players[user_id]
        
        if player.has_answered:
            return False, "❌ شما قبلاً به این نوبت پاسخ داده‌اید!"
        
        language = 'fa'
        question = self._get_random_truth(language)
        
        game.pending_action = TurnAction.TRUTH
        game.pending_question = question
        game.last_action_time = datetime.now()
        player.has_answered = True  # ✅ FIX: Set has_answered to True when question is given
        
        self.api_client.send_message(
            group_id,
            f"📖 **حقیقت برای {player.display_name}:**\n\n{question}\n\n"
            f"{player.display_name}، لطفاً پاسخ خود را در گروه بفرستید.\n"
            f"(برای ثبت پاسخ /answered بفرستید، برای رد کردن نوبت از /skip استفاده کنید)"
        )
        
        return True, "سوال حقیقت ارسال شد."

    def handle_dare(self, group_id: str, user_id: str) -> Tuple[bool, str]:
        """Handle /dare command"""
        game = self._get_user_game(user_id, group_id)
        if not game:
            return False, "❌ شما در هیچ بازی فعالی نیستید یا بازی یافت نشد."
        
        self.update_activity(group_id)
        
        if game.current_turn != user_id:
            current_player = game.players.get(game.current_turn)
            current_name = current_player.display_name if current_player else "نامشخص"
            return False, f"❌ نوبت شما نیست! در حال حضر نوبت {current_name} است."
        
        player = game.players[user_id]
        
        if player.has_answered:
            return False, "❌ شما قبلاً به این نوبت پاسخ داده‌اید!"
        
        language = 'fa'
        dare = self._get_random_dare(language)
        
        game.pending_action = TurnAction.DARE
        game.pending_question = dare
        game.last_action_time = datetime.now()
        player.has_answered = True  # ✅ FIX: Set has_answered to True when challenge is given
        
        self.api_client.send_message(
            group_id,
            f"⚡ **جرعت برای {player.display_name}:**\n\n{dare}\n\n"
            f"{player.display_name}، لطفاً انجام کار خود را تأیید کنید.\n"
            f"(برای تأیید /done بفرستید، برای رد کردن /skip)"
        )
        
        return True, "چالش جرعت ارسال شد."

    def handle_ask(self, group_id: str, user_id: str) -> Tuple[bool, str]:
        """Handle /ask command - ask a custom question to the group"""
        game = self._get_user_game(user_id, group_id)
        if not game:
            return False, "❌ شما در هیچ بازی فعالی نیستید یا بازی یافت نشد."
        
        self.update_activity(group_id)
        
        if game.current_turn != user_id:
            current_player = game.players.get(game.current_turn)
            current_name = current_player.display_name if current_player else "نامشخص"
            return False, f"❌ نوبت شما نیست! در حال حضر نوبت {current_name} است."
        
        player = game.players[user_id]
        
        if player.has_answered:
            return False, "❌ شما قبلاً به این نوبت پاسخ داده‌اید!"
        
        game.pending_action = TurnAction.ASK
        game.last_action_time = datetime.now()
        
        self.api_client.send_message(
            group_id,
            f"❓ {player.display_name} می‌خواهد از گروه سوال بپرسد!\n\n"
            f"لطفاً سوال خود را در گروه تایپ کنید.\n"
            f"(برای پاسخ به سوال، بازیکنان می‌توانند بعداً پاسخ دهند)"
        )
        
        return True, "سوال خود را بپرسید"

    def handle_custom_question(self, group_id: str, user_id: str, question: str) -> Tuple[bool, str]:
        """Handle custom question from user who used /ask"""
        game = self._get_user_game(user_id, group_id)
        if not game:
            return False, "❌ شما در هیچ بازی فعالی نیستید."
        
        if game.pending_action != TurnAction.ASK or game.current_turn != user_id:
            return False, "❌ شما در حال حضر درخواست سوال ندارید. از /ask استفاده کنید."
        
        self.update_activity(group_id)
        
        player = game.players[user_id]
        
        if len(question) > 500:
            return False, "❌ سوال شما خیلی طولانی است (حداکثر 500 کاراکتر)."
        
        game.pending_question = question
        game.pending_action = None
        game.last_action_time = datetime.now()
        player.has_answered = True  # They asked, now wait for others to answer
        
        self.api_client.send_message(
            group_id,
            f"❓ **سوال {player.display_name} از گروه:**\n\n{question}\n\n"
            f"بازیکنان می‌توانند به این سوال پاسخ دهند!\n"
            f"(برای پاسخ از /answer استفاده کنید)"
        )
        
        return True, "سوال شما ارسال شد!"
    

    def handle_answered(self, group_id: str, user_id: str) -> Tuple[bool, str]:
        """Handle /answered command - player confirms they have answered the question (for truth)"""
        game = self._get_user_game(user_id, group_id)
        if not game:
            return False, "❌ شما در هیچ بازی فعالی نیستید یا بازی یافت نشد."
        
        self.update_activity(group_id)  # ✅ Update activity on command
        
        if game.current_turn != user_id:
            current_player = game.players.get(game.current_turn)
            current_name = current_player.display_name if current_player else "نامشخص"
            return False, f"❌ نوبت شما نیست! در حال حضر نوبت {current_name} است."
        
        player = game.players[user_id]
        
        if not player.has_answered:
            return False, "❌ شما در حال حضر هیچ سوالی برای پاسخ دادن ندارید! ابتدا از /truth استفاده کنید."
        
        # Check what type of action is pending
        if game.pending_action == TurnAction.TRUTH:
            # Player answered truth question - award points
            points = random.randint(5, 15)
            player.score += points
            player.turn_count += 1
            player.has_answered = False
            game.pending_action = None
            game.pending_question = None
            
            self.api_client.send_message(
                group_id,
                f"✅ {player.display_name} به سوال حقیقت پاسخ داد و {points} امتیاز گرفت!"
            )
            
            self._next_turn(group_id)
            return True, f"پاسخ شما ثبت شد! {points} امتیاز گرفتید."
        
        else:
            return False, "❌ هیچ سوالی در انتظار پاسخ نیست! از /truth استفاده کنید."
    

    def handle_done(self, group_id: str, user_id: str) -> Tuple[bool, str]:
        """Handle /done command - complete a dare challenge"""
        game = self._get_user_game(user_id, group_id)
        if not game:
            return False, "❌ شما در هیچ بازی فعالی نیستید."
        
        self.update_activity(group_id)
        
        if game.current_turn != user_id:
            return False, "❌ نوبت شما نیست!"
        
        player = game.players[user_id]
        
        if not player.has_answered:
            return False, "❌ شما در حال حضر هیچ چالشی ندارید!"
        
        if game.pending_action != TurnAction.DARE:
            return False, "❌ در حال حضر چالشی برای تکمیل وجود ندارد!"
        
        points = random.randint(5, 15)
        player.score += points
        player.turn_count += 1
        player.has_answered = False
        game.pending_action = None
        game.pending_question = None
        
        self.api_client.send_message(
            group_id,
            f"✅ {player.display_name} چالش را با موفقیت انجام داد و {points} امتیاز گرفت!"
        )
        
        self._next_turn(group_id)
        
        return True, f"چالش تکمیل شد! {points} امتیاز دریافت کردید."

    def handle_skip(self, group_id: str, user_id: str) -> Tuple[bool, str]:
        """Handle /skip command - skip current turn (lose points)"""
        game = self._get_user_game(user_id, group_id)
        if not game:
            return False, "❌ شما در هیچ بازی فعالی نیستید."
        
        self.update_activity(group_id)
        
        if game.current_turn != user_id:
            return False, "❌ نوبت شما نیست!"
        
        player = game.players[user_id]
        
        # Penalty for skipping
        penalty = 5
        player.score = max(0, player.score - penalty)
        player.has_answered = False
        game.pending_action = None
        game.pending_question = None
        
        self.api_client.send_message(
            group_id,
            f"⏭️ {player.display_name} نوبت را رد کرد و {penalty} امتیاز از دست داد!"
        )
        
        self._next_turn(group_id)
        
        return True, f"نوبت رد شد! {penalty} امتیاز از دست دادید."

    def _next_turn(self, group_id: str):
        """Move to the next player"""
        game = self.active_games.get(group_id)
        if not game or game.state != GameState.IN_PROGRESS:
            return
        
        players_list = list(game.players.values())
        if not players_list:
            return
        
        # Find index of current player
        current_index = -1
        for i, p in enumerate(players_list):
            if p.user_id == game.current_turn:
                current_index = i
                break
        
        # Move to next player (circular)
        next_index = (current_index + 1) % len(players_list)
        next_player = players_list[next_index]
        
        game.current_turn = next_player.user_id
        game.pending_action = None
        game.pending_question = None
        game.warning_sent = False  # Reset warning flag for new turn
        
        # Reset has_answered for the new player (they haven't answered yet)
        for p in game.players.values():
            p.has_answered = False
        
        # Announce next turn
        self.api_client.send_message(
            group_id,
            f"🎲 **نوبت بعدی: {next_player.display_name}**\n\n"
            f"{next_player.display_name}، لطفاً یکی از دستورات را بفرستید:\n"
            f"• /truth - حقیقت\n"
            f"• /dare - جرعت\n"
            f"• /ask - سوال از گروه\n"
            f"• /answered - ثبت پاسخ (پس از پاسخ به سوال حقیقت)\n"
            f"• /skip - رد کردن نوبت\n\n"
            f"وضعیت فعلی: /status\n\n"
            f"⚠️ **توجه:** در صورت عدم فعالیت به مدت 3 دقیقه اخطار و پس از 5 دقیقه بازی بسته می‌شود."
        )

    # ============================================
    # Helper Methods
    # ============================================
    
    def _get_user_game(self, user_id: str, group_id: str = None) -> Optional[GroupGame]:
        """Get the game for a user"""
        if group_id and group_id in self.active_games:
            return self.active_games.get(group_id)
        
        game_group = self.player_to_game.get(user_id)
        if game_group:
            return self.active_games.get(game_group)
        
        return None

    def _get_random_truth(self, language: str) -> str:
        """Get random truth question"""
        questions = TRUTH_QUESTIONS.get(language, TRUTH_QUESTIONS['fa'])
        return random.choice(questions)
    
    def _get_random_dare(self, language: str) -> str:
        """Get random dare action"""
        dares = DARE_ACTIONS.get(language, DARE_ACTIONS['fa'])
        return random.choice(dares)

    def get_game_status(self, group_id: str) -> str:
        """Get current game status"""
        game = self.active_games.get(group_id)
        if not game:
            return "❌ هیچ بازی فعالی در این گروه وجود ندارد.\nبرای شروع /game را بفرستید."
        
        if not game.players:
            return "⚠️ هیچ بازیکنی در بازی نیست. برای شروع /game را بفرستید."
        
        # Sort players by score (descending)
        sorted_players = sorted(game.players.values(), key=lambda p: -p.score)
        
        players_list = "\n".join([
            f"  {'👑 ' if p.user_id == game.host_id else '  '}{p.display_name}: {p.score} امتیاز"
            for p in sorted_players
        ])
        
        # Add inactivity info if game is in progress
        inactivity_info = ""
        if game.state == GameState.IN_PROGRESS:
            inactive_seconds = (datetime.now() - game.last_action_time).total_seconds()
            if inactive_seconds > 0:
                inactivity_info = f"\n\n⏰ آخرین فعالیت: {int(inactive_seconds//60)} دقیقه و {int(inactive_seconds%60)} ثانیه پیش"
                if inactive_seconds >= WARNING_TIMEOUT:
                    inactivity_info += f"\n⚠️ **اخطار: بازی در حال بسته شدن است!**"
        
        if game.state == GameState.WAITING_PLAYERS:
            return f"🎯 **بازی در انتظار بازیکنان!**\n\n👥 بازیکنان ثبت‌نام شده:\n{players_list}\n\nبرای شروع بازی /go را بفرستید.{inactivity_info}"
        
        elif game.state == GameState.IN_PROGRESS:
            current = game.players.get(game.current_turn)
            current_name = current.display_name if current else "نامشخص"
            
            return (f"🎯 **بازی در جریان است!**\n\n"
                   f"👥 **بازیکنان:**\n{players_list}\n\n"
                   f"🎲 **نوبت:** {current_name}\n"
                   f"📝 **دستورات:**\n"
                   f"  • /truth - حقیقت\n"
                   f"  • /dare - جرعت\n"
                   f"  • /ask - سوال از گروه\n"
                   f"  • /answered - ثبت پاسخ (پس از پاسخ به سوال حقیقت)\n"
                   f"  • /skip - رد کردن نوبت\n"
                   f"  • /end - پایان بازی (فقط میزبان){inactivity_info}")
        
        return "بازی تمام شده است."

    def _cleanup_game(self, group_id: str):
        """Remove finished game and clean up player mappings"""
        game = self.active_games.pop(group_id, None)
        if game:
            for player_id in game.players:
                self.player_to_game.pop(player_id, None)
    
    def cleanup_inactive_games(self, timeout_minutes: int = 60):
        """Legacy cleanup method - now handled by inactivity monitor"""
        pass  # Now handled by check_inactive_games()

    def get_active_games_count(self) -> int:
        """Get number of active games"""
        return len(self.active_games)


    
# ============================================
# Global Instance
# ============================================

group_game_manager = None

def init_group_game_manager(api_client, user_mgr):
    global group_game_manager
    group_game_manager = GroupGameManager(api_client, user_mgr)
    return group_game_manager