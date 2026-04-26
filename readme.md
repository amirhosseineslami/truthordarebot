# Rubika Bot Project

A sophisticated Python-based bot for the Rubika messaging platform, designed to facilitate anonymous chat connections between users. This bot enables users to "play with strangers" by pairing them randomly, managing connections, and providing a seamless chat experience with integrated keypad interactions, language support, and persistent data storage.

## 🚀 Features

- **Anonymous Pairing**: Connect users randomly for private conversations.
- **Connection Management**: Handle player connections, disconnections, and waiting queues.
- **Keypad Integration**: Interactive inline keyboards for user commands.
- **Multi-Language Support**: Localized text support (currently Persian/Farsi).
- **Database Persistence**: User profiles, game statistics, and offset tracking using MySQL.
- **Real-Time Messaging**: Parse and forward messages between connected users.
- **User Management**: Track coins, scores, levels, and game history.
- **Offset Handling**: Efficient API polling with offset-based updates.
- **Error Handling**: Robust exception handling and logging.
- **Modular Architecture**: Clean separation of concerns with dedicated classes for API client, parser, keypad, and connection manager.

## 📋 Requirements

- Python 3.8+
- MySQL Database
- Rubika Bot API Token
- Required Python packages (see `requirements.txt`)

## 🛠 Installation

1. **Clone the Repository**:
    ```bash
    git clone https://github.com/yourusername/rubika-bot.git
    cd rubika-bot
    ```

2. **Create Virtual Environment**:
    ```bash
    python -m venv myenv
    source myenv/bin/activate  # On Windows: myenv\Scripts\activate
    ```

3. **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4. **Set Up Environment Variables**:
    Create a `.env` file in the root directory:
    ```
    BOT_TOKEN=your_rubika_bot_token_here
    DB_HOST=your_mysql_host
    DB_USER=your_mysql_username
    DB_PASSWORD=your_mysql_password
    DB_NAME=your_database_name
    ```

5. **Database Setup**:
    - Ensure MySQL is running.
    - The bot will automatically create tables on first run via `database.py`.
    - Alternatively, run the initialization manually:
      ```python
      from database import init_db
      init_db()
      ```

## ⚙ Configuration

### Database Configuration
Edit `database.py` for custom DB settings:
```python
DB_CONFIG = {
     'database': 'your_db_name',
     'user': 'your_user',
     'password': 'your_password',
     'host': 'your_host',
     'port': 3306,  # Default MySQL port
     'charset': 'utf8mb4'
}
```

### Language Files
Add or modify language files in the `locales/` directory (e.g., `fa.json` for Persian):
```json
{
     "welcome": "خوش آمدید!",
     "play_with_stranger": "بازی با غریبه",
     "cancel_the_search": "لغو جستجو"
}
```

### Bot Commands
The bot responds to:
- `/start`: Initialize and show main menu.
- Text matching localized commands (e.g., "بازی با غریبه").
- Connection-based forwarding for paired users.

## 🚀 Usage

1. **Run the Bot**:
    ```bash
    python main.py
    ```

2. **Bot Flow**:
    - Users start with `/start` to receive the welcome message and main keypad.
    - Selecting "Play with Stranger" adds them to the waiting queue.
    - When paired, messages are forwarded between users.
    - Users can disconnect or cancel searches via keypad buttons.

3. **Monitoring**:
    - The bot logs activities to the console.
    - Check database for user stats and offsets.

## 📊 Database Schema

### Users Table
- `user_id`: Unique identifier.
- `chat_id`: Chat identifier.
- `coin`: User coins.
- `score/level`: Game progress.
- `language`: Preferred language.
- Other fields: Subscription, stats, etc.

### Offsets Table
- `next_offset_id`: For API polling.
- `message_count`: Update count.
- `last_request_time`: Timestamp.

## 🔧 API Integration

- **Rubika API**: Uses `botApiClient.py` for sending/receiving messages.
- **Keypad API**: Inline keyboards via `keypad.py`.
- **Message Parsing**: Clean parsing with `rubikaMessageParser.py`.

Ensure your `BOT_TOKEN` is valid and has necessary permissions.

## 🤝 Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature-name`.
3. Commit changes: `git commit -am 'Add feature'`.
4. Push: `git push origin feature-name`.
5. Submit a pull request.

Follow PEP 8 for code style. Add tests for new features.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🐛 Troubleshooting

- **Database Connection Issues**: Verify MySQL credentials and network access.
- **API Errors**: Check token validity and Rubika API status.
- **Import Errors**: Ensure all dependencies are installed.
- **Offset Problems**: Reset `offset.json` if polling fails.

## 📞 Support

For issues or questions, open an issue on GitHub or contact the maintainer.

---

*Built with ❤️ for the Rubika community.*