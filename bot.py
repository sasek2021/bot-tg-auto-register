import os
import asyncio
import logging
import random
import string
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackContext,
    CallbackQueryHandler,
)
import firebase_admin
from firebase_admin import credentials, db
import telegram.error
import httpx  # Import httpx for async HTTP requests
import re  # Import regular expressions module

# Load environment variables
load_dotenv()

# Telegram bot token and support group chat ID from environment variables
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
SUPPORT_GROUP_CHAT_ID = os.getenv('SUPPORT_GROUP_CHAT_ID')
START_MESSAGE = os.getenv('START_MESSAGE', "Welcome to our support bot!")

if not BOT_TOKEN:
    print("Please set TELEGRAM_BOT_TOKEN in your .env file.")
    exit(1)

if not SUPPORT_GROUP_CHAT_ID:
    print("Please set SUPPORT_GROUP_CHAT_ID in your .env file.")
    exit(1)

# Firebase setup
firebase_admin.initialize_app(
    credentials.Certificate('tbot-b1603-firebase-adminsdk-nv7j1-df7e8318c2.json'),
    {
        'databaseURL': 'https://tbot-b1603-default-rtdb.firebaseio.com/'
    }
)
firebase_db = db.reference('/')

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Shared data structures and locks
user_language = {}
language_lock = asyncio.Lock()

# Define website name and currency code
websitename = 'FAFA138'  # Adjusted as per your requirements
currency_code = ''  # No currency code to keep username length within limits

# Set to True to enable support functionality
ENABLE_SUPPORT = True  # We need support feature

# Define country code to remove
COUNTRY_CODE = '855'  # Cambodia country code

# Database setup for support topics
def setup_database():
    conn = sqlite3.connect("support.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS forum_topics (
            user_id INTEGER PRIMARY KEY,
            forum_topic_id TEXT
        )
        """
    )
    conn.commit()
    conn.close()

def get_user_forum_topic(user_id):
    conn = sqlite3.connect("support.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT forum_topic_id FROM forum_topics WHERE user_id = ?", (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    if result and result[0]:
        return result[0]
    else:
        return None

def store_forum_topic(user_id, forum_topic_id):
    conn = sqlite3.connect("support.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO forum_topics (user_id, forum_topic_id) VALUES (?, ?)",
        (user_id, forum_topic_id),
    )
    conn.commit()
    conn.close()

def get_user_id_by_thread_id(thread_id):
    conn = sqlite3.connect("support.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT user_id FROM forum_topics WHERE forum_topic_id = ?",
        (thread_id,),
    )

    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Define texts for different languages
texts = {
    'en': {
        'start_prompt': 'Please choose your language or select an option:',
        'language_buttons': ['English 🇺🇸', 'Khmer 🇰🇭'],
        'help_button': 'Help 📖',
        'questions_button': 'Questions ❓',
        'register_button': 'Register 📋',
        'support_button': 'Support 🆘',
        'questions_prompt': 'Please choose a question:',
        'help_text': (
            "📖 *Help*\n\n"
            "Welcome to the Q&A Bot! Here's how you can use me:\n"
            "1. Type /start to begin.\n"
            "2. Choose your preferred language.\n"
            "3. Select a question from the list to receive an answer.\n"
            "4. Use the 'Back to Menu 🔙' button to return to the main menu.\n"
            "If you have any other questions, feel free to ask!"
        ),
        'back_to_menu': 'Back to Menu 🔙',
        'back_to_questions': 'Back to Questions 🔙',
        'other_questions': 'Other Questions ❓',
        'unknown_command': "Sorry, I didn't understand that command. Please use the provided buttons or type /start to begin again.",
        'register_prompt_ph_number': 'To proceed with registration, please share your contact:',
        'registration_data_missing': 'Registration data not found. Please start again.',
        'contact_shared': 'Thank you! Processing your registration...',
        'support_message': 'You can now send messages to support. They will respond as soon as possible.',
        'share_contact_button': 'Share Contact 📱',
    },
    'kh': {
        'start_prompt': 'សូមជ្រើសរើសភាសារបស់អ្នក ឬជ្រើសរើសជម្រើសមួយ:',
        'language_buttons': ['English 🇺🇸', 'ខ្មែរ 🇰🇭'],
        'help_button': 'ជំនួយ 📖',
        'questions_button': 'សំណួរ ❓',
        'register_button': 'ចុះឈ្មោះ 📋',
        'support_button': 'ជំនួយ 🆘',
        'questions_prompt': 'សូមជ្រើសរើសសំណួរ៖',
        'help_text': (
            "📖 *ជំនួយ*\n\n"
            "សូមស្វាគមន៍មកកាន់ Q&A Bot! នេះគឺជាវិធីដែលអ្នកអាចប្រើប្រាស់ខ្ញុំ៖\n"
            "1. វាយ /start ដើម្បីចាប់ផ្តើម។\n"
            "2. ជ្រើសរើសភាសាដែលអ្នកចូលចិត្ត។\n"
            "3. ជ្រើសរើសសំណួរពីបញ្ជីដើម្បីទទួលបានចម្លើយ។\n"
            "4. ប្រើប៊ូតុង 'ត្រឡប់ទៅម៉ឺនុយ 🔙' ដើម្បីត្រឡប់ទៅម៉ឺនុយ។\n"
            "បើអ្នកមានសំណួរផ្សេងទៀត សូមកុំអៀនស៊ែរ!"
        ),
        'back_to_menu': 'ត្រឡប់ទៅម៉ឺនុយ 🔙',
        'back_to_questions': 'ថយក្រោយទៅសំណួរ 🔙',
        'other_questions': 'សំណួរផ្សេងទៀត ❓',
        'unknown_command': "សូមអភ័យទោស ខ្ញុំមិនយល់សេចក្តីបញ្ជារបស់អ្នកទេ។ សូមប្រើប៊ូតុងដែលបានផ្ដល់ឬវាយ /start ដើម្បីចាប់ផ្តើមវិញ។",
        'register_prompt_ph_number': 'ដើម្បីបន្តការចុះឈ្មោះ សូមចែករំលែកទំនាក់ទំនងរបស់អ្នក:',
        'registration_data_missing': 'មិនអាចរកឃើញទិន្នន័យចុះឈ្មោះទេ។ សូមចាប់ផ្តើមម្តងទៀត។',
        'contact_shared': 'អរគុណ! កំពុងដំណើរការការចុះឈ្មោះរបស់អ្នក...',
        'support_message': 'អ្នកអាចផ្ញើសារទៅកាន់ជំនួយ។ ពួកយើងនឹងឆ្លើយតបឱ្យបានឆាប់តាមដែលអាចធ្វើទៅបាន។',
        'share_contact_button': 'ចែករំលែកទំនាក់ទំនង 📱',
    }
}

# Questions and Answers in English with IDs
qa_english = [
    {"id": "en_q1", "question": "Is your website a scam or not?", "answer": "My website is not a scam. If you win, you can withdraw immediately."},
    {"id": "en_q2", "question": "Upon first registration, do you have free credit or not?", "answer": "We have promotions for new customers: 100% and 150% bonuses. For example, deposit $10 and get $20."},
    {"id": "en_q3", "question": "Why is withdrawal so slow now?", "answer": "We apologize because we have many customers depositing and withdrawing. Please wait."},
    {"id": "en_q4", "question": "Why does depositing take so long?", "answer": "Please wait because today we have many customers withdrawing and depositing."},
    {"id": "en_q5", "question": "How to register a game account? Does registering a new account need payment or not? Do you have any new promotions?", "answer": "Yes, sir. For new game account registration, it's free for you, and we have a reward of $168 for new customers."},
    {"id": "en_q6", "question": "How much can I deposit to play this game? (Daily question)", "answer": "Sir, on our website, you can deposit starting from $1, but if you want to get a promotion, deposit $3 or more."},
    {"id": "en_q7", "question": "Why does your website take so long for deposit and withdrawal?", "answer": "Yes, sir, because our website has many customers depositing and withdrawing."},
    {"id": "en_q8", "question": "Why does it take so long to deposit when there is a promotion?", "answer": "Excuse me, for deposits and withdrawals, we process them in the order they are received."},
    {"id": "en_q9", "question": "For new registration, is payment needed? Do you have any promotions? Can you register for me? Is your website a scam?", "answer": "We register game accounts for free. We have a $168 reward. You need to register by yourself. We are not a scam; if you win, you can withdraw your money."},
    {"id": "en_q10", "question": "How to play the game? How much for deposit and withdrawal?", "answer": "Please check the game account. If you cannot play, I will teach you. You can deposit from $1 up and withdraw from $5 up."},
]

# Questions and Answers in Khmer with IDs
qa_khmer = [
    {"id": "kh_q1", "question": "វេបសាយខាងបងបោកឬអត់?", "answer": "ចាសបង វេបសាយខាងប្អូនមិនមានការបោកប្រាស់ទេ បងអោយតែបងលេងឈ្នះ ដកបានពិតភ្លាមៗណាបង។"},
    {"id": "kh_q2", "question": "ចុះឈ្មោះដំបូងមាន free លុយអត់?", "answer": "ចាសបង ខាងប្អូនមានការប្រម៉ូសិនជូនសម្រាប់សមាជិកថ្មី មានប្រម៉ូសិន 100% & 150% ដាក់ប្រាក់ 10$ ទទួលបាន 20$។"},
    {"id": "kh_q3", "question": "ហេតុអ្វីបានដាក់ដកលុយយូរម៉្លេះ?", "answer": "អធ្យាយស្រ័យបង ដោយសារអតិថិជនផ្សេងទៀតដាក់ដកប្រាក់ច្រើនណា បងសូមរងចាំសិនណាបង។"},
    {"id": "kh_q4", "question": "ហេតុអ្វីបានជាវេបសាយរបស់អ្នកនៅពេលដាក់ប្រាក់ promotion ហេតុអ្វីត្រូវចំណាយពេលយូរម្លេះ?", "answer": "សូមអភ័យទោស ចំពោះការដាក់ប្រាក់ និងការដកប្រាក់ យើងនឹងធ្វើតាមលេខរៀងអតិថិជនណាបង។"},
    {"id": "kh_q5", "question": "សូមរបៀបបង្កើតអាខោនហ្គេម បង្កើតអាខោនអស់លុយអត់? ហើយចុះឈ្មោះមានការថែមជូនប្រម៉ូសិនអត់?", "answer": "ចា បង សម្រាប់អាខោនហ្គេម ខាងប្អូនបង្កើតជូនបងហ្រី្វណាបង ហើយសម្រាប់សមាជិកថ្មី ខាងប្អូនមានប្រាក់រង្វាន់ 168$ ថែមជូនណាបង។"},
    {"id": "kh_q6", "question": "ហ្គេមនេះគេលេងមិច? អាចដាក់ប្រាក់ចាប់ពីប៉ុន្មានអាចលេងបាន?", "answer": "ចាសបង សូមចូលគណនីហ្គេម ប្រសិនបើបងមិនអាចលេងបាន ខ្ញុំនឹងបង្រៀនបង។ សម្រាប់វេបសាយខាងប្អូន បងអាចដាក់ចាប់ពី 1$ បានណាបង តែបើបងយកប្រមូសិន បងអាចដាក់ចាប់ពី 3$ ឡើងបាន។"},
    {"id": "kh_q7", "question": "ហេតុអ្វីបានជាវេបសាយដាក់ដកលុយយូរម្លេះ?", "answer": "ចា បង ព្រោះវេបសាយខាងប្អូនមានអតិថិជនដាក់ និងដកលុយច្រើនណាបង។"},
    {"id": "kh_q8", "question": "ហេតុអ្វីបានជាវេបសាយដាក់ប្រាក់ promotion យូរម្លេះ?", "answer": "សូមអភ័យទោស ចំពោះការដាក់ប្រាក់ និងការដកប្រាក់ យើងនឹងធ្វើតាមលេខរៀងរបស់អតិថិជន។"},
    {"id": "kh_q9", "question": "ការចុះឈ្មោះថ្មីត្រូវការបង់ប្រាក់ទេ? មានប្រម៉ូសិនអ្វីខ្លះ? អ្នកអាចចុះឈ្មោះជំនួសខ្ញុំបានទេ? វេបសាយរបស់អ្នកបោកឬអត់?", "answer": "យើងចុះឈ្មោះគណនីហ្គេមឥតគិតថ្លៃ និងមានរង្វាន់ 168$. អ្នកត្រូវចុះឈ្មោះដោយខ្លួនឯង។ យើងមិនមែនជាការបោកប្រាស់ទេ; បើអ្នកឈ្នះ អ្នកអាចដកលុយរបស់អ្នកបាន។"},
    {"id": "kh_q10", "question": "តើអាចលេងហ្គេមនេះបានយ៉ាងដូចម្តេច? តើត្រូវដាក់ប្រាក់ប៉ុន្មាន ដើម្បីលេង ហើយការដកប្រាក់ប៉ុន្មាន?", "answer": "សូមពិនិត្យគណនីហ្គេម ប្រសិនបើអ្នកមិនអាចលេងបាន ខ្ញុំនឹងបង្រៀនអ្នក។ អ្នកអាចដាក់ចាប់ពី 1$ ហើយអាចដកចាប់ពី 5$ ឡើង។"},
]

# Map IDs to answers
qa_dict = {}
for qa in qa_english + qa_khmer:
    qa_dict[qa['id']] = qa['answer']

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Reset support mode and registration step
    context.user_data['in_support'] = False
    context.user_data['registration_step'] = None

    # Access user_language with lock
    async with language_lock:
        language = user_language.get(user_id, 'en')

    # Create keyboard with the desired layout using ReplyKeyboardMarkup
    keyboard = [
        ["English 🇺🇸", "ខ្មែរ 🇰🇭"],
        [texts[language]['questions_button']],
        [texts[language]['help_button']],
        [texts[language]['register_button']],
        [texts[language]['support_button']],
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False  # Keep the keyboard visible
    )

    await update.message.reply_text(
        text=START_MESSAGE,
        reply_markup=reply_markup
    )

# Handle language selection
async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # Set language based on selection
    if text == 'English 🇺🇸':
        language = 'en'
    elif text == 'ខ្មែរ 🇰🇭':
        language = 'kh'
    else:
        # If the text doesn't match a language option, do nothing
        return

    # Update user language with lock
    async with language_lock:
        user_language[user_id] = language

    # Create menu keyboard
    keyboard = [
        [texts[language]['questions_button']],
        [texts[language]['help_button']],
        [texts[language]['register_button']],
        [texts[language]['support_button']],
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

    await update.message.reply_text(
        text=texts[language]['start_prompt'],
        reply_markup=reply_markup
    )

# Questions menu handler
async def questions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Access user_language with lock
    async with language_lock:
        language = user_language.get(user_id, 'en')

    qa_list = qa_english if language == 'en' else qa_khmer

    # Send the questions
    await send_questions(update, context, qa_list, language)

# Function to send questions
async def send_questions(update_or_query, context, qa_list, language):
    prompt = texts[language]['questions_prompt']
    keyboard = [
        [InlineKeyboardButton(qa['question'], callback_data=qa['id'])] for qa in qa_list
    ]
    # Add 'Other Questions' and 'Back to Menu' buttons with their own callback data
    other_questions_text = texts[language]['other_questions']
    back_to_menu_text = texts[language]['back_to_menu']
    keyboard.append([InlineKeyboardButton(other_questions_text, callback_data='other_questions')])
    keyboard.append([InlineKeyboardButton(back_to_menu_text, callback_data='back_to_menu')])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if isinstance(update_or_query, Update):
        await update_or_query.message.reply_text(
            text=prompt,
            reply_markup=reply_markup
        )
    else:
        await update_or_query.edit_message_text(
            text=prompt,
            reply_markup=reply_markup
        )

# Callback query handler for answering questions
async def answer_callback_query(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    # Access user_language with lock
    async with language_lock:
        language = user_language.get(user_id, 'en')

    qa_list = qa_english if language == 'en' else qa_khmer

    # Find the answer using the callback data (question ID)
    answer = None
    for qa in qa_list:
        if qa['id'] == query.data:
            answer = qa['answer']
            break

    if answer:
        # Send the answer with 'Back to Questions' button
        back_to_questions_text = texts[language]['back_to_questions']
        keyboard = [
            [InlineKeyboardButton(back_to_questions_text, callback_data='back_to_questions')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=answer,
            reply_markup=reply_markup
        )
    elif query.data == 'other_questions':
        await support_handler(update, context)
    elif query.data == 'back_to_menu':
        await back_to_menu(update, context)
    elif query.data == 'back_to_questions':
        qa_list = qa_english if language == 'en' else qa_khmer
        await send_questions(query, context, qa_list, language)
    else:
        # Handle unknown callback data
        unknown_msg = texts[language]['unknown_command']
        await query.edit_message_text(text=unknown_msg)

# Help command handler via button and /help command
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Access user_language with lock
    async with language_lock:
        language = user_language.get(user_id, 'en')

    help_text = texts[language]['help_text']
    back_text = texts[language]['back_to_menu']

    # Create 'Back to Menu' button
    keyboard = [
        [back_text]
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

    await update.message.reply_text(
        text=help_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# 'Back to Menu' button handler
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Reset support mode and registration step
    context.user_data['in_support'] = False
    context.user_data['registration_step'] = None

    # Access user_language with lock
    async with language_lock:
        language = user_language.get(user_id, 'en')

    # Show the main menu
    keyboard = [
        [texts[language]['questions_button']],
        [texts[language]['help_button']],
        [texts[language]['register_button']],
        [texts[language]['support_button']],
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

    await update.message.reply_text(
        text=texts[language]['start_prompt'],
        reply_markup=reply_markup
    )

# 'Back to Questions' button handler
async def back_to_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Access user_language with lock
    async with language_lock:
        language = user_language.get(user_id, 'en')

    qa_list = qa_english if language == 'en' else qa_khmer

    # Show questions again
    await send_questions(update, context, qa_list, language)

# Answer handler for contact sharing during registration
async def answer_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message
    step = context.user_data.get('registration_step')

    # Access user_language with lock
    async with language_lock:
        language = user_language.get(user_id, 'en')

    if step == 'request_ph_number':
        # Check if the user shared contact
        if message.contact and message.contact.phone_number:
            ph_number = message.contact.phone_number
            # Remove all non-digit characters from phone number
            ph_number = re.sub(r'\D', '', ph_number)
            logger.info(f"Processed phone number for user {user_id}: {ph_number}")

            # Remove country code '855' if present at the start
            if ph_number.startswith(COUNTRY_CODE):
                ph_number = ph_number[len(COUNTRY_CODE):]
                logger.info(f"Removed country code. New phone number: {ph_number}")
            else:
                logger.info(f"Country code '{COUNTRY_CODE}' not found at the start of the phone number.")

            # Store the phone number
            context.user_data['ph_number'] = ph_number

            # Proceed to registration
            await update.message.reply_text(texts[language]['contact_shared'])

            # Call the function to handle registration data
            await handle_registration(user_id, update, context)

            # Reset registration state
            context.user_data['registration_step'] = None

            # Return to main menu
            await back_to_menu(update, context)
            return
        else:
            # User did not provide contact, prompt again
            await update.message.reply_text(texts[language]['register_prompt_ph_number'])
            return

    # Handle other commands like 'Back to Menu', 'Back to Questions', 'Support'
    if message.text == texts[language]['back_to_menu']:
        await back_to_menu(update, context)
    elif message.text == texts[language]['back_to_questions']:
        await back_to_questions(update, context)
    elif message.text == texts[language]['support_button']:
        await support_handler(update, context)
    else:
        # If the text doesn't match any known command, inform the user
        unknown_msg = texts[language]['unknown_command']
        await update.message.reply_text(
            text=unknown_msg,
            parse_mode='Markdown'
        )

# Registration handler
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Access user_language with lock
    async with language_lock:
        language = user_language.get(user_id, 'en')

    # Set registration step
    context.user_data['registration_step'] = 'request_ph_number'

    # Request contact sharing
    contact_button = KeyboardButton(text=texts[language]['share_contact_button'], request_contact=True)
    back_button_text = texts[language]['back_to_menu']
    keyboard = [
        [contact_button],
        [KeyboardButton(text=back_button_text)]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    register_prompt_ph_number = texts[language]['register_prompt_ph_number']
    await update.message.reply_text(
        text=register_prompt_ph_number,
        reply_markup=reply_markup
    )

# Function to handle registration data
async def handle_registration(user_id, update, context):
    # Access user_language with lock
    async with language_lock:
        language = user_language.get(user_id, 'en')

    ph_number = context.user_data['ph_number']
    user_first_name = update.effective_user.first_name or 'User'

    # Generate username and password
    username = await generate_unique_username(user_first_name)
    password_characters = string.ascii_letters + string.digits
    password = ''.join(random.choice(password_characters) for _ in range(9))

    # Store user data in Firebase
    registration_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    user_ref = firebase_db.child('users').child(str(user_id))
    user_ref.set({
        'username': username,
        'password': password,
        'ph_number': ph_number,
        'registration_time': registration_time
    })

    # Append a random suffix to the phone number to make it unique
    random_suffix = ''.join(random.choices(string.digits, k=4))
    unique_ph_number = ph_number + random_suffix

    # Send data to the proxy server for registration
    register_data = {
        'username': username,
        'password': password,
        'ph_number': unique_ph_number  # Use the modified phone number
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post('https://bot-tg-auto-register.vercel.app//register', json=register_data)
            # response = await client.post('http://localhost:5000/register', json=register_data)
        if response.status_code == 200:
            # Parse response for PHPSESSID
            session_data = response.json()
            phpsessid = session_data.get('PHPSESSID')

            if phpsessid:
                # Provide direct link for user to log in with PHPSESSID
                login_url = f"https://m.fafa138xxx.com/?PHPSESSID={phpsessid}"
                logger.info("PHPSESSID found and provided to user for auto-login.")

                # Inform the user
                message = (
                    f"🆔 Your username: {username}\n"
                    f"🔑 Password: {password}\n"
                    f"👤 @QA1331_bot Bot control 01\n"
                    f"🌐 Website: https://m.fafa138xxx.com\n"
                    f"💰 Balance: USD 0.00\n"
                    f"🕒 Registration time: {registration_time}"
                )

                await update.message.reply_text(
                    message,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go to site", url=login_url)]])
                )
            else:
                logger.error("PHPSESSID missing from response; login may fail.")
                await update.message.reply_text("Registration successful, but session token missing.")
        else:
            # Registration failed
            logger.error(f"Registration failed: {response.text}")
            await update.message.reply_text("Registration failed. Please try again later.")
    except Exception as e:
        logger.error(f"Error during registration: {e}")
        await update.message.reply_text("An error occurred during registration. Please try again later.")

# Function to generate a unique username
async def generate_unique_username(user_first_name):
    base_username = websitename  # 'FAFA138' (adjust as needed)
    max_username_length = 15
    # Take up to 4 alphanumeric characters from user's first name
    first_name_letters = ''.join(filter(str.isalnum, user_first_name))[:4]

    # Initial random digits
    random_digits = ''.join(random.choices(string.digits, k=3))  # Adjust the number of digits as needed

    # Combine to form the initial username
    username = f"{base_username}{first_name_letters}{random_digits}"

    # Ensure the username is not longer than 15 characters
    username = username[:max_username_length]

    # Check Firebase to see if this username is already used
    users_ref = firebase_db.child('users')
    existing_users = users_ref.order_by_child('username').equal_to(username).get()

    attempt = 0
    max_attempts = 10

    while existing_users and attempt < max_attempts:
        # Username already exists, change only the last number of digits
        attempt += 1
        # Increase the random digits
        random_digits = str(int(random_digits) + 1).zfill(len(random_digits))
        # Reconstruct the username
        username = f"{base_username}{first_name_letters}{random_digits}"
        username = username[:max_username_length]
        existing_users = users_ref.order_by_child('username').equal_to(username).get()

    if attempt == max_attempts:
        # If all attempts fail, generate a completely random username
        username = base_username + ''.join(random.choices(string.digits, k=max_username_length - len(base_username)))
        username = username[:max_username_length]
        logger.info(f"Using fallback username: {username}")

    return username

# Support handler
async def support_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    user_first_name = user.first_name

    # Set support mode
    context.user_data['in_support'] = True

    # Access user_language with lock
    async with language_lock:
        language = user_language.get(user_id, 'en')

    forum_topic_id = get_user_forum_topic(user_id)

    if forum_topic_id:
        await update.message.reply_text(
            texts[language]['support_message']
        )
    else:
        try:
            forum_topic = await context.bot.create_forum_topic(
                chat_id=int(SUPPORT_GROUP_CHAT_ID),
                name=f"{user_first_name} (ID: {user_id})",
            )

            await context.bot.send_message(
                chat_id=int(SUPPORT_GROUP_CHAT_ID),
                message_thread_id=forum_topic.message_thread_id,
                text=f"User {user_first_name} started a support chat.",
            )
            store_forum_topic(user_id, str(forum_topic.message_thread_id))
            await update.message.reply_text(
                texts[language]['support_message']
            )
        except Exception as e:
            logger.error(f"Failed to create forum topic: {e}")
            await update.message.reply_text(
                "Failed to create a support topic. Please try again later."
            )

# Handle user messages in private chat
async def handle_user_message(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if update.message.chat.type == "private" and context.user_data.get('in_support', False):
        # Only process messages when user is in support mode
        forum_topic_id = get_user_forum_topic(user_id)

        if forum_topic_id:
            logger.debug(f"User ID: {user_id}, Forum Topic ID: {forum_topic_id}")
            try:
                if update.message.text:
                    await context.bot.copy_message(
                        chat_id=int(SUPPORT_GROUP_CHAT_ID),
                        from_chat_id=update.message.chat_id,
                        message_id=update.message.message_id,
                        message_thread_id=int(forum_topic_id),
                    )
                elif update.message.photo:
                    await context.bot.send_photo(
                        chat_id=int(SUPPORT_GROUP_CHAT_ID),
                        photo=update.message.photo[-1].file_id,
                        caption=update.message.caption,
                        message_thread_id=int(forum_topic_id),
                    )
                elif update.message.video:
                    await context.bot.send_video(
                        chat_id=int(SUPPORT_GROUP_CHAT_ID),
                        video=update.message.video.file_id,
                        caption=update.message.caption,
                        message_thread_id=int(forum_topic_id),
                    )
                elif update.message.document:
                    await context.bot.send_document(
                        chat_id=int(SUPPORT_GROUP_CHAT_ID),
                        document=update.message.document.file_id,
                        caption=update.message.caption,
                        message_thread_id=int(forum_topic_id),
                    )
                elif update.message.voice:
                    await context.bot.send_voice(
                        chat_id=int(SUPPORT_GROUP_CHAT_ID),
                        voice=update.message.voice.file_id,
                        caption=update.message.caption,
                        message_thread_id=int(forum_topic_id),
                    )
            except telegram.error.BadRequest as e:
                logger.error(f"Error forwarding message: {e}")
                if 'Message thread not found' in str(e):
                    # Recreate the support topic
                    await recreate_support_topic_and_forward_message(update, context, user_id)
                else:
                    await update.message.reply_text("An error occurred while sending your message. Please try again later.")
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                await update.message.reply_text("An unexpected error occurred. Please try again later.")
        else:
            # No forum topic exists, create one and forward the message
            await recreate_support_topic_and_forward_message(update, context, user_id)
    else:
        # Not in support mode; do nothing
        return

# Function to recreate support topic and forward the message
async def recreate_support_topic_and_forward_message(update: Update, context: CallbackContext, user_id: int):
    user = update.effective_user
    user_first_name = user.first_name

    # Access user_language with lock
    async with language_lock:
        language = user_language.get(user_id, 'en')

    try:
        # Create a new forum topic
        forum_topic = await context.bot.create_forum_topic(
            chat_id=int(SUPPORT_GROUP_CHAT_ID),
            name=f"{user_first_name} (ID: {user_id})",
        )

        await context.bot.send_message(
            chat_id=int(SUPPORT_GROUP_CHAT_ID),
            message_thread_id=forum_topic.message_thread_id,
            text=f"User {user_first_name} started a support chat.",
        )
        # Store the new forum_topic_id
        store_forum_topic(user_id, str(forum_topic.message_thread_id))
        await update.message.reply_text(
            texts[language]['support_message']
        )
        # Forward the original message
        if update.message.text:
            await context.bot.copy_message(
                chat_id=int(SUPPORT_GROUP_CHAT_ID),
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id,
                message_thread_id=forum_topic.message_thread_id,
            )
        elif update.message.photo:
            await context.bot.send_photo(
                chat_id=int(SUPPORT_GROUP_CHAT_ID),
                photo=update.message.photo[-1].file_id,
                caption=update.message.caption,
                message_thread_id=forum_topic.message_thread_id,
            )
        elif update.message.video:
            await context.bot.send_video(
                chat_id=int(SUPPORT_GROUP_CHAT_ID),
                video=update.message.video.file_id,
                caption=update.message.caption,
                message_thread_id=forum_topic.message_thread_id,
            )
        elif update.message.document:
            await context.bot.send_document(
                chat_id=int(SUPPORT_GROUP_CHAT_ID),
                document=update.message.document.file_id,
                caption=update.message.caption,
                message_thread_id=forum_topic.message_thread_id,
            )
        elif update.message.voice:
            await context.bot.send_voice(
                chat_id=int(SUPPORT_GROUP_CHAT_ID),
                voice=update.message.voice.file_id,
                caption=update.message.caption,
                message_thread_id=forum_topic.message_thread_id,
            )
    except Exception as e:
        logger.error(f"Failed to recreate forum topic: {e}")
        await update.message.reply_text(
            "Failed to create a support topic. Please try again later."
        )

# Handle messages from support group
async def handle_forum_reply(update: Update, context: CallbackContext) -> None:
    logger.debug("Received a message in the support group")

    thread_id = update.message.message_thread_id
    logger.debug(f"Received message in thread ID: {thread_id}")

    user_id = get_user_id_by_thread_id(str(thread_id))

    if user_id:
        try:
            logger.debug(f"Sending message to user ID: {user_id}")
            if update.message.text:
                await context.bot.send_message(
                    chat_id=user_id, text=update.message.text
                )
            elif update.message.photo:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=update.message.photo[-1].file_id,
                    caption=update.message.caption,
                )
            elif update.message.video:
                await context.bot.send_video(
                    chat_id=user_id,
                    video=update.message.video.file_id,
                    caption=update.message.caption,
                )
            elif update.message.document:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=update.message.document.file_id,
                    caption=update.message.caption,
                )
            elif update.message.voice:
                await context.bot.send_voice(
                    chat_id=user_id,
                    voice=update.message.voice.file_id,
                    caption=update.message.caption,
                )

            logger.debug(f"Message sent to user ID {user_id}")
        except Exception as e:
            logger.error(f"Error processing the message from forum topic: {e}")
    else:
        logger.error(f"No user found for thread ID: {thread_id}")

# Main function
def main():
    setup_database()
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers

    # Command Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_handler))  # For /help command

    # Message Handlers

    # Language selection handler
    application.add_handler(MessageHandler(filters.Regex('^(English 🇺🇸|ខ្មែរ 🇰🇭)$'), handle_language_selection))

    # Menu option handlers
    application.add_handler(MessageHandler(
        filters.Regex('^' + texts['en']['questions_button'] + '$') |
        filters.Regex('^' + texts['kh']['questions_button'] + '$'),
        questions_menu))
    application.add_handler(MessageHandler(
        filters.Regex('^' + texts['en']['help_button'] + '$') |
        filters.Regex('^' + texts['kh']['help_button'] + '$'),
        help_handler))
    application.add_handler(MessageHandler(
        filters.Regex('^' + texts['en']['register_button'] + '$') |
        filters.Regex('^' + texts['kh']['register_button'] + '$'),
        register))
    application.add_handler(MessageHandler(
        filters.Regex('^' + texts['en']['support_button'] + '$') |
        filters.Regex('^' + texts['kh']['support_button'] + '$'),
        support_handler))
    application.add_handler(MessageHandler(
        filters.Regex('^' + texts['en']['back_to_menu'] + '$') |
        filters.Regex('^' + texts['kh']['back_to_menu'] + '$'),
        back_to_menu))
    application.add_handler(MessageHandler(
        filters.Regex('^' + texts['en']['back_to_questions'] + '$') |
        filters.Regex('^' + texts['kh']['back_to_questions'] + '$'),
        back_to_questions))

    # Handler for contact sharing during registration
    application.add_handler(MessageHandler(
        filters.CONTACT & filters.ChatType.PRIVATE,
        answer_question
    ))

    # Handler for support messages (added after answer_question)
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.ALL & (~filters.UpdateType.EDITED),
        handle_user_message
    ))

    # Handler for messages in support group
    application.add_handler(MessageHandler(
        filters.Chat(int(SUPPORT_GROUP_CHAT_ID)) & (~filters.UpdateType.EDITED),
        handle_forum_reply
    ))

    # CallbackQueryHandler for inline buttons
    application.add_handler(CallbackQueryHandler(answer_callback_query))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    main()
