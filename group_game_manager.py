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

class QuestionDifficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

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
    pending_difficulty: Optional[QuestionDifficulty] = None
    last_action_time: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    warning_sent: bool = False  # Track if warning message has been sent
    allow_custom_questions: bool = True  # Host can disable custom questions

# ============================================
# Truth & Dare Questions Database with Tiers
# ============================================

# Easy Questions (5 points)
EASY_TRUTH_QUESTIONS = {
    'fa': [
        "رنگ مورد علاقه‌ات چیه؟",
        "بهترین فیلمی که دیدی کدومه؟",
        "غذای مورد علاقه‌ات چیه؟",
        "چند ساعت میخوابی؟",
        "بهترین هدیه‌ای که گرفتی چی بوده؟"
    ],
    'en': [
        "What's your favorite color?",
        "What's the best movie you've seen?",
        "What's your favorite food?",
        "How many hours do you sleep?",
        "What's the best gift you've received?"
    ]
}

EASY_DARE_ACTIONS = {
    'fa': [
        "یک اسم حیوان بگو",
        "یک عکس از غذای امروزت بفرست",
        "یه متن خنده‌دار توی گروه بفرست",
        "به یکی از اعضای گروه یه تعریف کن",
        "یه استیکر قشنگ بفرست"
    ],
    'en': [
        "Name an animal",
        "Send a picture of today's food",
        "Send a funny text in the group",
        "Compliment one group member",
        "Send a nice sticker"
    ]
}

# Medium Questions (10 points)
MEDIUM_TRUTH_QUESTIONS = {
    'fa': [
        "تا حالا امتحان رو تقلب کردی؟",
        "بهترین سفری که رفتی کجا بوده؟",
        "بزرگترین موفقیت زندگیت چی بوده؟",
        "چه مهارتی داری که بقیه نمی‌دونن؟",
        "تا حالا کسی رو بهت معرفی کردن؟",
        "بزرگترین اشتباه زندگیت چی بوده؟"
    ],
    'en': [
        "Have you ever cheated on an exam?",
        "What's the best trip you've taken?",
        "What's your biggest achievement?",
        "What skill do you have that others don't know?",
        "Have you ever been set up with someone?",
        "What's your biggest mistake?"
    ]
}

MEDIUM_DARE_ACTIONS = {
    'fa': [
        "یه آهنگ کوتاه بخون",
        "یه عکس از خودت بفرست",
        "به یکی از اعضای گروه زنگ بزن و بگو دوستت دارم",
        "یه ویدیو از خنده‌ت بفرست",
        "به سه نفر از گروه بگو چه ویژگی خوبی دارن"
    ],
    'en': [
        "Sing a short song",
        "Send a picture of yourself",
        "Call a group member and say I love you",
        "Send a video of your laugh",
        "Tell three group members their good qualities"
    ]
}

# Hard Questions (15 points)
HARD_TRUTH_QUESTIONS = {
    'fa': [
        "بزرگترین دروغی که گفتي چی بوده؟",
        "سخت‌ترین تصمیم زندگیت چی بوده؟",
        "عمیق‌ترین رازی که داری چیه؟",
        "آیا تا حالا کسی رو آزاری دادی؟",
        "بزرگترین ترس تو چیه؟",
        "چیزی که هیچکس ازت نمیدونه رو بگو"
    ],
    'en': [
        "What's the biggest lie you've told?",
        "What's the hardest decision of your life?",
        "What's your deepest secret?",
        "Have you ever hurt someone?",
        "What's your biggest fear?",
        "Tell something nobody knows about you"
    ]
}

HARD_DARE_ACTIONS = {
    'fa': [
        "به کسی که دوستش داری زنگ بزن و اعتراف کن",
        "یه رقص انجام بده و ویدیو بفرست",
        "به گروه بگو بزرگترین پشیمونیت چیه",
        "با یه غریبه توی خیابون عکس بگیر و بفرست",
        "به کسی که باهاش قهر بودی پیام بده و آشتی کن"
    ],
    'en': [
        "Call someone you love and confess",
        "Do a dance and send a video",
        "Tell the group your biggest regret",
        "Take a photo with a stranger on the street and send it",
        "Message someone you had a fight with and make up"
    ]
}

# Difficulty settings
DIFFICULTY_SETTINGS = {
    QuestionDifficulty.EASY: {'points': 5, 'truth': EASY_TRUTH_QUESTIONS, 'dare': EASY_DARE_ACTIONS},
    QuestionDifficulty.MEDIUM: {'points': 10, 'truth': MEDIUM_TRUTH_QUESTIONS, 'dare': MEDIUM_DARE_ACTIONS},
    QuestionDifficulty.HARD: {'points': 15, 'truth': HARD_TRUTH_QUESTIONS, 'dare': HARD_DARE_ACTIONS},
}

# ============================================
# Main Group Game Manager Class
# ============================================

class GroupGameManager:
    def __init__(self, api_client, user_mgr):
        self.api_client = api_client
        self.user_mgr = user_mgr
        self.active_games: Dict[str, GroupGame] = {}
        self.player_to_game: Dict[str, str] = {}
        self._cleanup_thread_started = False
    
    # ============================================
    # Inactivity Check & Auto Cleanup
    # ============================================
    
    def update_activity(self, group_id: str):
        if group_id in self.active_games:
            self.active_games[group_id].last_action_time = datetime.now()
            self.active_games[group_id].warning_sent = False
    
    def check_inactive_games(self):
        now = datetime.now()
        games_to_end = []
        
        for group_id, game in self.active_games.items():
            if game.state != GameState.IN_PROGRESS:
                continue
            
            inactive_seconds = (now - game.last_action_time).total_seconds()
            
            if inactive_seconds >= GAME_TIMEOUT:
                games_to_end.append(group_id)
            elif inactive_seconds >= WARNING_TIMEOUT and not game.warning_sent:
                game.warning_sent = True
                remaining = GAME_TIMEOUT - inactive_seconds
                self.api_client.send_message(
                    group_id,
                    f"⚠️ **اخطار! بازی {int(remaining//60)} دقیقه دیگر به دلیل عدم فعالیت بسته می‌شود!**"
                )
        
        for group_id in games_to_end:
            self._auto_end_game(group_id)
    
    def _auto_end_game(self, group_id: str):
        if group_id not in self.active_games:
            return
        
        game = self.active_games[group_id]
        
        if game.players:
            winner = max(game.players.values(), key=lambda p: p.score)
            self.api_client.send_message(
                group_id,
                f"⏰ **بازی به دلیل عدم فعالیت بسته شد!**\n\n🎉 **برنده: {winner.display_name}**"
            )
        
        self._cleanup_game(group_id)
    
    def start_inactivity_monitor(self):
        if self._cleanup_thread_started:
            return
        
        def monitor_loop():
            while True:
                time.sleep(60)
                self.check_inactive_games()
        
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
        self._cleanup_thread_started = True
    
    # ============================================
    # Game Creation & Management
    # ============================================
    
    def create_game(self, group_id: str, host_id: str, host_username: str, 
                    host_display_name: str = "", host_first_name: str = "", host_last_name: str = "") -> Tuple[bool, str]:
        if group_id in self.active_games:
            game = self.active_games[group_id]
            if game.state != GameState.FINISHED:
                return False, "❌ یک بازی در این گروه در حال اجراست!"
        
        formatted_name = host_display_name or host_username or host_id
        
        game = GroupGame(
            group_id=group_id,
            host_id=host_id,
            state=GameState.WAITING_PLAYERS
        )
        
        game.players[host_id] = GamePlayer(
            user_id=host_id,
            chat_id=group_id,
            username=host_username,
            display_name=formatted_name,
            first_name=host_first_name,
            last_name=host_last_name,
            joined_at=datetime.now()
        )
        
        self.active_games[group_id] = game
        self.player_to_game[host_id] = group_id
        self.start_inactivity_monitor()
        
        return True, f"🎮 بازی جدید ایجاد شد!\n\n👑 شما میزبان هستید!\n📝 کاربران با 'هستم' بپیوندند.\n🎲 میزبان با /go بازی را شروع کند.\n📖 راهنما: /gamehelp"

    def add_player(self, group_id: str, user_id: str, username: str, 
                   display_name: str, first_name: str = "", last_name: str = "") -> Tuple[bool, str]:
        if group_id not in self.active_games:
            return False, "❌ هیچ بازی فعالی نیست. /game بفرستید."
        
        game = self.active_games[group_id]
        
        if game.state != GameState.WAITING_PLAYERS:
            return False, "❌ بازی شروع شده!"
        
        if user_id in game.players:
            return False, f"❌ {display_name} قبلاً پیوسته!"
        
        formatted_name = display_name or first_name or username or user_id
        
        game.players[user_id] = GamePlayer(
            user_id=user_id,
            chat_id=group_id,
            username=username,
            display_name=formatted_name,
            first_name=first_name,
            last_name=last_name,
            joined_at=datetime.now()
        )
        self.player_to_game[user_id] = group_id
        
        return True, f"✅ {formatted_name} به بازی پیوست! ({len(game.players)} نفر)"

    def remove_player(self, group_id: str, user_id: str) -> Tuple[bool, str]:
        if group_id not in self.active_games:
            return False, "❌ هیچ بازی فعالی نیست."
        
        game = self.active_games[group_id]
        
        if user_id not in game.players:
            return False, "❌ شما در بازی نیستید."
        
        player = game.players[user_id]
        
        if game.state == GameState.WAITING_PLAYERS:
            game.players.pop(user_id)
            self.player_to_game.pop(user_id, None)
            return True, f"👋 {player.display_name} خارج شد. ({len(game.players)} نفر ماندند)"
        
        elif game.state == GameState.IN_PROGRESS:
            del game.players[user_id]
            self.player_to_game.pop(user_id, None)
            
            if len(game.players) < 2:
                self.end_game(group_id, game.host_id)
                return True, f"👋 {player.display_name} خارج شد. بازی پایان یافت."
            
            if game.current_turn == user_id:
                self._next_turn(group_id)
            
            return True, f"👋 {player.display_name} خارج شد. بازی ادامه دارد."
        
        return False, "نمی‌توانید خارج شوید."

    def start_game(self, group_id: str, host_id: str) -> Tuple[bool, str]:
        if group_id not in self.active_games:
            return False, "❌ هیچ بازی فعالی نیست."
        
        game = self.active_games[group_id]
        
        if game.host_id != host_id:
            return False, "❌ فقط میزبان می‌تواند شروع کند!"
        
        if game.state != GameState.WAITING_PLAYERS:
            return False, "❌ بازی شروع شده!"
        
        if len(game.players) < 2:
            return False, f"❌ حداقل ۲ بازیکن نیاز است! (هم اکنون {len(game.players)} نفر)"
        
        game.state = GameState.IN_PROGRESS
        self.update_activity(group_id)
        
        first_player = random.choice(list(game.players.values()))
        game.current_turn = first_player.user_id
        
        players_list = "\n".join([f"  🎮 {p.display_name}" for p in game.players.values()])
        
        self.api_client.send_message(
            group_id,
            f"🎯 **بازی شروع شد!**\n\n👥 بازیکنان:\n{players_list}\n\n"
            f"🎲 **نوبت: {first_player.display_name}**\n\n"
            f"📖 دستورات:\n"
            f"  • /truth - حقیقت (مهم)\n"
            f"  • /dare - جرعت (مهم)\n"
            f"  • /truth <easy/medium/hard> - حقیقت با سطح سختی\n"
            f"  • /dare <easy/medium/hard> - جرعت با سطح سختی\n"
            f"  • /answered - ثبت پاسخ\n"
            f"  • /skip - رد نوبت (-۵ امتیاز)\n"
            f"  • /status - وضعیت بازی\n"
            f"\n🎚️ **سطوح سختی:** easy (۵ امتیاز), medium (۱۰ امتیاز), hard (۱۵ امتیاز)\n"
            f"⚠️ عدم فعالیت ۵ دقیقه = بسته شدن خودکار"
        )
        
        return True, "بازی شروع شد!"

    def end_game(self, group_id: str, host_id: str) -> Tuple[bool, str]:
        if group_id not in self.active_games:
            return False, "❌ هیچ بازی فعالی نیست."
        
        game = self.active_games[group_id]
        
        if game.host_id != host_id:
            return False, "❌ فقط میزبان می‌تواند تمام کند!"
        
        if game.state != GameState.IN_PROGRESS:
            return False, "❌ بازی در جریان نیست!"
        
        if game.players:
            winner = max(game.players.values(), key=lambda p: p.score)
            scores = "\n".join([f"  🎮 {p.display_name}: {p.score} امتیاز" 
                               for p in sorted(game.players.values(), key=lambda x: -x.score)])
            
            self.api_client.send_message(
                group_id,
                f"🏆 **بازی پایان یافت!**\n\n📊 امتیازات:\n{scores}\n\n"
                f"🎉 **برنده: {winner.display_name}** با {winner.score} امتیاز!"
            )
        
        game.state = GameState.FINISHED
        self._cleanup_game(group_id)
        
        return True, "بازی تمام شد!"

    # ============================================
    # Host Management Commands
    # ============================================
    
    def host_skip_player(self, group_id: str, host_id: str, target_user_id: str) -> Tuple[bool, str]:
        """Host can skip any player's turn"""
        game = self._get_user_game(host_id, group_id)
        if not game or game.host_id != host_id:
            return False, "❌ فقط میزبان می‌تواند این کار را انجام دهد!"
        
        if target_user_id not in game.players:
            return False, "❌ بازیکن مورد نظر در بازی نیست!"
        
        player = game.players[target_user_id]
        
        # Apply penalty
        penalty = 5
        player.score = max(0, player.score - penalty)
        player.has_answered = False
        game.pending_action = None
        
        self.api_client.send_message(
            group_id,
            f"👑 میزبان نوبت {player.display_name} را رد کرد! {penalty} امتیاز از دست داد."
        )
        
        if game.current_turn == target_user_id:
            self._next_turn(group_id)
        
        return True, f"نوبت {player.display_name} رد شد!"

    def host_add_points(self, group_id: str, host_id: str, target_user_id: str, points: int) -> Tuple[bool, str]:
        """Host can add points to any player"""
        game = self._get_user_game(host_id, group_id)
        if not game or game.host_id != host_id:
            return False, "❌ فقط میزبان می‌تواند این کار را انجام دهد!"
        
        if target_user_id not in game.players:
            return False, "❌ بازیکن مورد نظر در بازی نیست!"
        
        if points < -20 or points > 50:
            return False, "❌ امتیاز باید بین -20 تا +50 باشد!"
        
        player = game.players[target_user_id]
        player.score += points
        
        self.api_client.send_message(
            group_id,
            f"👑 میزبان {points} امتیاز {'اضافه کرد' if points > 0 else 'کم کرد'} به {player.display_name}!"
        )
        
        return True, f"امتیاز {player.display_name} {'افزایش' if points > 0 else 'کاهش'} یافت!"

    def host_end_game_immediately(self, group_id: str, host_id: str) -> Tuple[bool, str]:
        """Host can end game immediately without winner announcement"""
        return self.end_game(group_id, host_id)

    def host_force_next_turn(self, group_id: str, host_id: str) -> Tuple[bool, str]:
        """Host can force move to next turn"""
        game = self._get_user_game(host_id, group_id)
        if not game or game.host_id != host_id:
            return False, "❌ فقط میزبان می‌تواند این کار را انجام دهد!"
        
        if game.state != GameState.IN_PROGRESS:
            return False, "❌ بازی در جریان نیست!"
        
        current = game.players.get(game.current_turn)
        current_name = current.display_name if current else "نامشخص"
        
        self._next_turn(group_id)
        
        return True, f"👑 میزبان نوبت را تغییر داد. نوبت {current_name} رد شد!"

    def host_remove_player(self, group_id: str, host_id: str, target_user_id: str) -> Tuple[bool, str]:
        """Host can remove any player from the game"""
        return self.remove_player(group_id, target_user_id)

    def host_set_difficulty_limit(self, group_id: str, host_id: str, max_difficulty: str) -> Tuple[bool, str]:
        """Host can limit maximum question difficulty"""
        game = self._get_user_game(host_id, group_id)
        if not game or game.host_id != host_id:
            return False, "❌ فقط میزبان می‌تواند این کار را انجام دهد!"
        
        try:
            difficulty = QuestionDifficulty(max_difficulty.lower())
        except ValueError:
            return False, "❌ سطح نامعتبر! (easy/medium/hard)"
        
        # Store in game state (you can add a field for this)
        game.allow_custom_questions = (difficulty != QuestionDifficulty.HARD)
        
        self.api_client.send_message(
            group_id,
            f"👑 میزبان حداکثر سطح سختی را به {max_difficulty} محدود کرد!"
        )
        
        return True, f"حداکثر سطح سختی: {max_difficulty}"

    # ============================================
    # Turn Management with Difficulty
    # ============================================
    
    def _get_question_by_difficulty(self, difficulty: QuestionDifficulty, is_truth: bool, language: str) -> Tuple[str, int]:
        """Get question/dare by difficulty with points"""
        settings = DIFFICULTY_SETTINGS[difficulty]
        points = settings['points']
        
        if is_truth:
            questions = settings['truth'][language]
            question = random.choice(questions) if questions else "سوالی یافت نشد"
        else:
            dares = settings['dare'][language]
            question = random.choice(dares) if dares else "چالشی یافت نشد"
        
        return question, points

    def handle_truth_with_difficulty(self, group_id: str, user_id: str, difficulty: str = None) -> Tuple[bool, str]:
        """Handle /truth command with optional difficulty"""
        game = self._get_user_game(user_id, group_id)
        if not game:
            return False, "❌ شما در بازی نیستید!"
        
        self.update_activity(group_id)
        
        if game.current_turn != user_id:
            current = game.players.get(game.current_turn)
            return False, f"❌ نوبت {current.display_name if current else 'دیگری'} است!"
        
        player = game.players[user_id]
        
        if player.has_answered:
            return False, "❌ قبلاً پاسخ داده‌اید!"
        
        # Parse difficulty
        diff = QuestionDifficulty.EASY
        if difficulty:
            try:
                diff = QuestionDifficulty(difficulty.lower())
            except ValueError:
                return False, "❌ سطح نامعتبر! (easy/medium/hard)"
        
        language = 'fa'
        question, points = self._get_question_by_difficulty(diff, True, language)
        
        game.pending_action = TurnAction.TRUTH
        game.pending_question = question
        game.pending_difficulty = diff
        game.last_action_time = datetime.now()
        player.has_answered = True
        
        self.api_client.send_message(
            group_id,
            f"📖 **حقیقت سطح {diff.value} ({points} امتیاز) برای {player.display_name}:**\n\n{question}\n\n"
            f"پس از پاسخ /answered بفرستید."
        )
        
        return True, f"سوال حقیقت ({diff.value}) ارسال شد!"

    def handle_dare_with_difficulty(self, group_id: str, user_id: str, difficulty: str = None) -> Tuple[bool, str]:
        """Handle /dare command with optional difficulty"""
        game = self._get_user_game(user_id, group_id)
        if not game:
            return False, "❌ شما در بازی نیستید!"
        
        self.update_activity(group_id)
        
        if game.current_turn != user_id:
            current = game.players.get(game.current_turn)
            return False, f"❌ نوبت {current.display_name if current else 'دیگری'} است!"
        
        player = game.players[user_id]
        
        if player.has_answered:
            return False, "❌ قبلاً پاسخ داده‌اید!"
        
        # Parse difficulty
        diff = QuestionDifficulty.EASY
        if difficulty:
            try:
                diff = QuestionDifficulty(difficulty.lower())
            except ValueError:
                return False, "❌ سطح نامعتبر! (easy/medium/hard)"
        
        language = 'fa'
        dare, points = self._get_question_by_difficulty(diff, False, language)
        
        game.pending_action = TurnAction.DARE
        game.pending_question = dare
        game.pending_difficulty = diff
        game.last_action_time = datetime.now()
        player.has_answered = True
        
        self.api_client.send_message(
            group_id,
            f"⚡ **جرعت سطح {diff.value} ({points} امتیاز) برای {player.display_name}:**\n\n{dare}\n\n"
            f"پس از انجام /done بفرستید."
        )
        
        return True, f"چالش جرعت ({diff.value}) ارسال شد!"

    def handle_answered(self, group_id: str, user_id: str) -> Tuple[bool, str]:
        """Handle /answered command - award points based on difficulty"""
        game = self._get_user_game(user_id, group_id)
        if not game:
            return False, "❌ شما در بازی نیستید!"
        
        self.update_activity(group_id)
        
        if game.current_turn != user_id:
            current = game.players.get(game.current_turn)
            return False, f"❌ نوبت {current.display_name if current else 'دیگری'} است!"
        
        player = game.players[user_id]
        
        if not player.has_answered:
            return False, "❌ سوالی برای پاسخ وجود ندارد! ابتدا /truth بفرستید."
        
        if game.pending_action == TurnAction.TRUTH:
            # Get points based on difficulty
            difficulty = game.pending_difficulty or QuestionDifficulty.EASY
            points = DIFFICULTY_SETTINGS[difficulty]['points']
            
            player.score += points
            player.turn_count += 1
            player.has_answered = False
            game.pending_action = None
            game.pending_question = None
            game.pending_difficulty = None
            
            self.api_client.send_message(
                group_id,
                f"✅ {player.display_name} به سوال حقیقت پاسخ داد و {points} امتیاز گرفت!"
            )
            
            self._next_turn(group_id)
            return True, f"پاسخ ثبت شد! {points} امتیاز گرفتید."
        
        else:
            return False, "❌ هیچ سوالی در انتظار پاسخ نیست!"

    def handle_done(self, group_id: str, user_id: str) -> Tuple[bool, str]:
        """Handle /done command - award points based on difficulty"""
        game = self._get_user_game(user_id, group_id)
        if not game:
            return False, "❌ شما در بازی نیستید!"
        
        self.update_activity(group_id)
        
        if game.current_turn != user_id:
            return False, "❌ نوبت شما نیست!"
        
        player = game.players[user_id]
        
        if not player.has_answered:
            return False, "❌ چالشی در انتظار نیست!"
        
        if game.pending_action != TurnAction.DARE:
            return False, "❌ چالشی برای تکمیل وجود ندارد!"
        
        difficulty = game.pending_difficulty or QuestionDifficulty.EASY
        points = DIFFICULTY_SETTINGS[difficulty]['points']
        
        player.score += points
        player.turn_count += 1
        player.has_answered = False
        game.pending_action = None
        game.pending_question = None
        game.pending_difficulty = None
        
        self.api_client.send_message(
            group_id,
            f"✅ {player.display_name} چالش جرعت را انجام داد و {points} امتیاز گرفت!"
        )
        
        self._next_turn(group_id)
        
        return True, f"چالش تکمیل شد! {points} امتیاز گرفتید."

    def handle_skip(self, group_id: str, user_id: str) -> Tuple[bool, str]:
        game = self._get_user_game(user_id, group_id)
        if not game:
            return False, "❌ شما در بازی نیستید!"
        
        self.update_activity(group_id)
        
        if game.current_turn != user_id:
            return False, "❌ نوبت شما نیست!"
        
        player = game.players[user_id]
        
        penalty = 5
        player.score = max(0, player.score - penalty)
        player.has_answered = False
        game.pending_action = None
        game.pending_question = None
        game.pending_difficulty = None
        
        self.api_client.send_message(
            group_id,
            f"⏭️ {player.display_name} نوبت را رد کرد و {penalty} امتیاز از دست داد!"
        )
        
        self._next_turn(group_id)
        
        return True, f"نوبت رد شد! {penalty} امتیاز از دست دادید."


    def handle_ask(self, group_id: str, user_id: str) -> Tuple[bool, str]:
        game = self._get_user_game(user_id, group_id)
        if not game:
            return False, "❌ شما در بازی نیستید!"
        
        self.update_activity(group_id)
        
        if game.current_turn != user_id:
            current = game.players.get(game.current_turn)
            return False, f"❌ نوبت {current.display_name if current else 'دیگری'} است!"
        
        if not game.allow_custom_questions:
            return False, "❌ میزبان سوالات سفارشی را غیرفعال کرده است!"
        
        player = game.players[user_id]
        
        if player.has_answered:
            return False, "❌ قبلاً پاسخ داده‌اید!"
        
        game.pending_action = TurnAction.ASK
        game.last_action_time = datetime.now()
        
        self.api_client.send_message(
            group_id,
            f"❓ {player.display_name} می‌خواهد سوال بپرسد!\nلطفاً سوال خود را بفرستید."
        )
        
        return True, "سوال خود را بپرسید"

    def handle_custom_question(self, group_id: str, user_id: str, question: str) -> Tuple[bool, str]:
        game = self._get_user_game(user_id, group_id)
        if not game:
            return False, "❌ شما در بازی نیستید!"
        
        if game.pending_action != TurnAction.ASK or game.current_turn != user_id:
            return False, "❌ درخواست سوال ندارید!"
        
        self.update_activity(group_id)
        
        player = game.players[user_id]
        
        game.pending_question = question
        game.pending_action = None
        game.last_action_time = datetime.now()
        player.has_answered = True
        
        self.api_client.send_message(
            group_id,
            f"❓ **سوال {player.display_name}:**\n{question}\n\n"
            f"بازیکنان می‌توانند با /answer پاسخ دهند!"
        )
        
        return True, "سوال شما ارسال شد!"

    def handle_answer(self, group_id: str, user_id: str, answer_text: str) -> Tuple[bool, str]:
        game = self.active_games.get(group_id)
        if not game or game.state != GameState.IN_PROGRESS:
            return False, "❌ بازی فعالی نیست!"
        
        self.update_activity(group_id)
        
        if user_id in game.players:
            player = game.players[user_id]
            self.api_client.send_message(
                group_id,
                f"💬 {player.display_name} پاسخ داد:\n{answer_text}"
            )
        
        return True, "پاسخ ارسال شد!"

    def _next_turn(self, group_id: str):
        game = self.active_games.get(group_id)
        if not game or game.state != GameState.IN_PROGRESS:
            return
        
        players_list = list(game.players.values())
        if not players_list:
            return
        
        current_index = -1
        for i, p in enumerate(players_list):
            if p.user_id == game.current_turn:
                current_index = i
                break
        
        next_index = (current_index + 1) % len(players_list)
        next_player = players_list[next_index]
        
        game.current_turn = next_player.user_id
        game.pending_action = None
        game.pending_question = None
        game.pending_difficulty = None
        game.warning_sent = False
        
        for p in game.players.values():
            p.has_answered = False
        
        self.api_client.send_message(
            group_id,
            f"🎲 **نوبت بعدی: {next_player.display_name}**\n"
            f"دستورات: /truth, /dare, /ask"
        )

    # ============================================
    # Helper Methods
    # ============================================
    
    def _get_user_game(self, user_id: str, group_id: str = None) -> Optional[GroupGame]:
        if group_id and group_id in self.active_games:
            return self.active_games.get(group_id)
        
        game_group = self.player_to_game.get(user_id)
        if game_group:
            return self.active_games.get(game_group)
        
        return None

    def get_game_status(self, group_id: str) -> str:
        game = self.active_games.get(group_id)
        if not game:
            return "❌ بازی فعالی نیست. /game بفرستید."
        
        sorted_players = sorted(game.players.values(), key=lambda p: -p.score)
        players_list = "\n".join([
            f"  {'👑 ' if p.user_id == game.host_id else '  '}{p.display_name}: {p.score} امتیاز"
            for p in sorted_players
        ])
        
        if game.state == GameState.WAITING_PLAYERS:
            return f"🎯 **در انتظار بازیکنان**\n\n👥 بازیکنان:\n{players_list}\n\nبازی با /go شروع می‌شود"
        
        elif game.state == GameState.IN_PROGRESS:
            current = game.players.get(game.current_turn)
            return (f"🎯 **بازی در جریان**\n\n👥 بازیکنان:\n{players_list}\n\n"
                   f"🎲 نوبت: {current.display_name if current else 'نامشخص'}\n\n"
                   f"🎚️ سطوح: easy(5) | medium(10) | hard(15)\n"
                   f"📝 /truth, /dare, /ask")
        
        return "بازی تمام شده"

    def _cleanup_game(self, group_id: str):
        game = self.active_games.pop(group_id, None)
        if game:
            for player_id in game.players:
                self.player_to_game.pop(player_id, None)
    
    def get_active_games_count(self) -> int:
        return len(self.active_games)


# ============================================
# Global Instance
# ============================================

group_game_manager = None

def init_group_game_manager(api_client, user_mgr):
    global group_game_manager
    group_game_manager = GroupGameManager(api_client, user_mgr)
    return group_game_manager