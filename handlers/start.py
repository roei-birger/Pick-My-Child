"""
Start Handler - Onboarding flow and main menu
Implements the user greeting and onboarding process from requirements
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from database import db_session
from models import User, Person
from utils.decorators import (
    handle_errors,
    require_user_registered,
    log_handler
)
from utils.keyboards import (
    main_menu_keyboard,
    onboarding_keyboard
)

logger = logging.getLogger(__name__)


@log_handler
@handle_errors
@require_user_registered
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start command handler
    Implements Section 3: Opening Screen and Onboarding
    """
    telegram_id = update.effective_user.id
    
    with db_session() as db:
        # Get user
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        
        # Check if user has any people in their list
        people_count = db.query(Person).filter(Person.user_id == user.id).count()
        
        if people_count == 0:
            # Onboarding flow - Section 3.1
            await show_onboarding(update, context)
        else:
            # Regular main menu - Section 3.2
            await show_main_menu(update, context)


async def show_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show onboarding screen for new users
    Section 3.1: Onboarding (Empty list)
    """
    message_text = (
        "ברוכים הבאים ל-pickmychild! 👋\n\n"
        "הבוט עוזר לכם לסנן תמונות ולמצוא את היקרים לכם.\n\n"
        "כדי להתחיל, אנחנו צריכים קודם להכיר מישהו אחד לפחות."
    )
    
    if update.message:
        await update.message.reply_text(
            text=message_text,
            reply_markup=onboarding_keyboard()
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            text=message_text,
            reply_markup=onboarding_keyboard()
        )


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show main menu for existing users
    Section 3.2: Main Menu (Non-empty list)
    """
    message_text = "מה תרצה לעשות?"
    
    if update.message:
        await update.message.reply_text(
            text=message_text,
            reply_markup=main_menu_keyboard()
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            text=message_text,
            reply_markup=main_menu_keyboard()
        )


@log_handler
@handle_errors
@require_user_registered
async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback handler for returning to main menu
    """
    query = update.callback_query
    await query.answer()
    
    # Exit filtering mode when returning to main menu
    if context.user_data.get('filtering_mode'):
        context.user_data['filtering_mode'] = False
        logger.info(f"User {update.effective_user.id} exited filtering mode")
    
    telegram_id = update.effective_user.id
    
    with db_session() as db:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        people_count = db.query(Person).filter(Person.user_id == user.id).count()
        
        if people_count == 0:
            await show_onboarding(update, context)
        else:
            await show_main_menu(update, context)


async def onboarding_complete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Called after user successfully adds first person
    Show congratulations and main menu
    """
    message_text = (
        "מעולה! עכשיו אפשר להתחיל. ✨\n\n"
        "מה תרצה לעשות?"
    )
    
    if update.message:
        await update.message.reply_text(
            text=message_text,
            reply_markup=main_menu_keyboard()
        )
    elif update.callback_query:
        await update.callback_query.message.reply_text(
            text=message_text,
            reply_markup=main_menu_keyboard()
        )
