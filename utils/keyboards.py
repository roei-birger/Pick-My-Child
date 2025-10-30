"""
Keyboards - Inline keyboard layouts for the bot
All text in Hebrew as per requirements
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List
from config import settings


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard for existing users"""
    keyboard = [
        [InlineKeyboardButton("👥 ניהול האנשים שלי", callback_data="people_menu")],
        [InlineKeyboardButton("📸 סינון תמונות לפי האנשים שלי", callback_data="filter_people")],
    ]
    
    # Add event features only if enabled
    if settings.enable_events_feature:
        keyboard.extend([
            [InlineKeyboardButton("📦 יצירת אירוע (העלאת ZIP)", callback_data="create_event")],
            [InlineKeyboardButton("#️⃣ יש לי מספר אירוע", callback_data="enter_event_code")],
        ])
    
    return InlineKeyboardMarkup(keyboard)


def onboarding_keyboard() -> InlineKeyboardMarkup:
    """Onboarding keyboard for new users"""
    keyboard = [
        [InlineKeyboardButton("➕ הוסף אדם", callback_data="people_add")],
    ]
    return InlineKeyboardMarkup(keyboard)


def people_menu_keyboard() -> InlineKeyboardMarkup:
    """People management menu"""
    keyboard = [
        [InlineKeyboardButton("➕ הוסף אדם", callback_data="people_add")],
        [InlineKeyboardButton("🗂️ הצג רשימה", callback_data="people_list")],
        [InlineKeyboardButton("🔙 חזרה לתפריט ראשי", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def person_actions_keyboard(person_id: int) -> InlineKeyboardMarkup:
    """Actions for a specific person"""
    keyboard = [
        [InlineKeyboardButton("️ מחיקה", callback_data=f"people_delete::{person_id}")],
        [InlineKeyboardButton("🔙 חזרה", callback_data="people_list")],
    ]
    return InlineKeyboardMarkup(keyboard)


def confirm_delete_keyboard(person_id: int) -> InlineKeyboardMarkup:
    """Confirm person deletion"""
    keyboard = [
        [InlineKeyboardButton("✅ כן, מחק", callback_data=f"people_delete_confirm::{person_id}")],
        [InlineKeyboardButton("❌ ביטול", callback_data=f"people_view::{person_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)


def event_created_keyboard(event_code: str) -> InlineKeyboardMarkup:
    """Keyboard shown after event creation"""
    keyboard = [
        [InlineKeyboardButton("📋 העתק מספר האירוע", callback_data=f"copy_event::{event_code}")],
        [InlineKeyboardButton("🔄 סטטוס אירוע", callback_data=f"event_status::{event_code}")],
        [InlineKeyboardButton("🔙 תפריט ראשי", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def event_status_keyboard(event_code: str) -> InlineKeyboardMarkup:
    """Keyboard for event status"""
    keyboard = [
        [InlineKeyboardButton("🔄 רענן סטטוס", callback_data=f"event_status::{event_code}")],
        [InlineKeyboardButton("🔙 תפריט ראשי", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def event_pagination_keyboard(event_code: str, cursor: int, has_more: bool) -> InlineKeyboardMarkup:
    """Pagination keyboard for event results"""
    keyboard = []
    
    if has_more:
        keyboard.append([
            InlineKeyboardButton("⬇️ עוד תמונות", callback_data=f"event_more::{event_code}::{cursor}")
        ])
    
    keyboard.append([
        InlineKeyboardButton("🛑 עצור", callback_data=f"event_stop::{event_code}"),
        InlineKeyboardButton("🔙 תפריט ראשי", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Simple back to main menu button"""
    keyboard = [
        [InlineKeyboardButton("🔙 תפריט ראשי", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def filtering_mode_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for filtering mode - only allows returning to main menu"""
    keyboard = [
        [InlineKeyboardButton("🛑 סיום סינון - חזרה לתפריט", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def add_person_button() -> InlineKeyboardMarkup:
    """Single 'Add Person' button (for empty states)"""
    keyboard = [
        [InlineKeyboardButton("➕ הוסף אדם", callback_data="people_add")],
    ]
    return InlineKeyboardMarkup(keyboard)
