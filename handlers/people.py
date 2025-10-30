"""
People Management Handler - Add, list, edit, delete people
Implements Section 4: Managing My People
"""
import logging
import json
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from database import db_session
from models import User, Person, PersonExample, UserState
from services import ai_service, storage_service
from utils.decorators import handle_errors, require_user_registered, log_handler
from utils.keyboards import (
    people_menu_keyboard,
    person_actions_keyboard,
    confirm_delete_keyboard,
    back_to_main_keyboard,
    add_person_button
)
from utils.validators import validate_person_name
from config import settings

logger = logging.getLogger(__name__)


@log_handler
@handle_errors
@require_user_registered
async def people_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show people management menu
    Section 4.1: Sub-menu
    """
    query = update.callback_query
    await query.answer()
    
    # Check if user is in filtering mode
    if context.user_data.get('filtering_mode'):
        await query.answer("⚠️ אתה במצב סינון. לחץ 'סיום סינון' כדי לחזור לתפריט.", show_alert=True)
        return
    
    message_text = "👥 ניהול האנשים שלי\n\nבחר/י פעולה:"
    
    await query.edit_message_text(
        text=message_text,
        reply_markup=people_menu_keyboard()
    )


@log_handler
@handle_errors
@require_user_registered
async def people_add_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Start the process of adding a new person
    Section 4.2: Adding a new person - Interactive process
    """
    query = update.callback_query
    
    # Check if user is in filtering mode
    if context.user_data.get('filtering_mode'):
        await query.answer("⚠️ אתה במצב סינון. לחץ 'סיום סינון' כדי לחזור לתפריט.", show_alert=True)
        return
    
    await query.answer("התחלת הוספת אדם חדש")
    
    telegram_id = update.effective_user.id
    
    # Set user state
    with db_session() as db:
        user_state = db.query(UserState).filter(UserState.telegram_id == telegram_id).first()
        
        if not user_state:
            user_state = UserState(telegram_id=telegram_id)
            db.add(user_state)
        
        user_state.state = "ADDING_PERSON"
        user_state.context = json.dumps({"photos": [], "person_id": None})
        db.commit()
    
    # Send instructions
    message_text = (
        "➕ הוספת אדם חדש\n\n"
        "שלחו 5-20 תמונות פנים ברורות של האדם.\n\n"
        "💡 טיפים לתמונות טובות:\n"
        "• פנים קדמיות וברורות\n"
        "• תאורה טובה\n"
        "• ללא משקפי שמש\n"
        "• מזוויות שונות (מומלץ)\n\n"
        "לסיום שלחו /done"
    )
    
    await query.message.reply_text(text=message_text)


@log_handler
@handle_errors
@require_user_registered
async def handle_person_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle photo uploads during person addition
    Section 4.2: Interactive validation and feedback
    """
    telegram_id = update.effective_user.id
    
    # Check if user is in ADDING_PERSON state
    with db_session() as db:
        user_state = db.query(UserState).filter(UserState.telegram_id == telegram_id).first()
        
        if not user_state or user_state.state != "ADDING_PERSON":
            return  # Not in adding person flow
        
        # Send ACK immediately
        ack_msg = await update.message.reply_text("קיבלתי, בודק...")
        
        # Send typing action
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING
        )
        
        # Get photo
        photo = update.message.photo[-1]  # Highest resolution
        photo_file = await photo.get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        # Parse context
        state_context = json.loads(user_state.context)
        photos = state_context.get("photos", [])
        person_id = state_context.get("person_id")
        
        # Get user
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        
        # Create person if first photo
        if person_id is None:
            person = Person(
                user_id=user.id,
                name="אדם חדש"  # Temporary name
            )
            db.add(person)
            db.commit()
            person_id = person.id
            state_context["person_id"] = person_id
        
        # Save photo
        file_path = storage_service.save_person_example(
            bytes(photo_bytes),
            user.id,
            person_id,
            ".jpg"
        )
        
        # Validate face
        is_valid, validation_message = ai_service.validate_face_image(str(file_path))
        
        if not is_valid:
            # Delete invalid photo
            file_path.unlink()
            
            # Send feedback
            await ack_msg.edit_text(f"❌ {validation_message}")
            return
        
        # Get embedding
        embedding = ai_service.get_embedding(str(file_path))
        
        if embedding is None:
            file_path.unlink()
            await ack_msg.edit_text("❌ לא הצלחתי לעבד את התמונה. נסה/י תמונה אחרת.")
            return
        
        # Save to database
        example = PersonExample(
            person_id=person_id,
            file_path=str(file_path),
            telegram_file_id=photo.file_id,
            embedding=embedding.tobytes()
        )
        db.add(example)
        
        # Update context
        photos.append({
            "file_path": str(file_path),
            "file_id": photo.file_id
        })
        state_context["photos"] = photos
        user_state.context = json.dumps(state_context)
        
        db.commit()
        
        # Send feedback based on count
        photo_count = len(photos)
        min_photos = settings.min_photos_per_person
        
        if photo_count < min_photos:
            feedback = (
                f"✅ קיבלתי ({photo_count}/{min_photos}). "
                f"זוהו פנים ברורות. מומלץ לשלוח לפחות {min_photos} תמונות."
            )
        elif photo_count == min_photos:
            feedback = (
                f"✅ קיבלתי ({photo_count}/{min_photos}). "
                f"מעולה! זה מספיק טוב להתחלה. "
                f"אפשר לשלוח עוד תמונות מזוויות שונות לשיפור הדיוק, או לשלוח /done לסיום."
            )
        else:
            feedback = f"✅ קיבלתי ({photo_count}). מעולה! ממשיכים או /done לסיום."
        
        await ack_msg.edit_text(feedback)


@log_handler
@handle_errors
@require_user_registered
async def done_adding_person(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Finish adding person - ask for name
    /done command during ADDING_PERSON state
    """
    telegram_id = update.effective_user.id
    
    with db_session() as db:
        user_state = db.query(UserState).filter(UserState.telegram_id == telegram_id).first()
        
        if not user_state or user_state.state != "ADDING_PERSON":
            await update.message.reply_text("אין תהליך פעיל של הוספת אדם.")
            return
        
        state_context = json.loads(user_state.context)
        photos = state_context.get("photos", [])
        person_id = state_context.get("person_id")
        
        # Check minimum photos
        if len(photos) < settings.min_photos_per_person:
            await update.message.reply_text(
                f"❌ נדרשות לפחות {settings.min_photos_per_person} תמונות. "
                f"יש לך {len(photos)} תמונות. שלח/י עוד תמונות או /cancel לביטול."
            )
            return
        
        # Ask for name
        user_state.state = "NAMING_PERSON"
        db.commit()
        
        await update.message.reply_text(
            "מצוין! 🎉\n\n"
            "איזה שם תרצה לתת לאדם הזה?"
        )


@log_handler
@handle_errors
@require_user_registered
async def handle_person_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle name input for new person
    """
    telegram_id = update.effective_user.id
    
    with db_session() as db:
        user_state = db.query(UserState).filter(UserState.telegram_id == telegram_id).first()
        
        if not user_state or user_state.state != "NAMING_PERSON":
            return  # Not in naming flow
        
        name = update.message.text.strip()
        
        # Validate name
        is_valid, error_message = validate_person_name(name)
        if not is_valid:
            await update.message.reply_text(f"❌ {error_message}\n\nאנא שלח/י שם תקין:")
            return
        
        # Update person name
        state_context = json.loads(user_state.context)
        person_id = state_context.get("person_id")
        
        person = db.query(Person).filter(Person.id == person_id).first()
        if person:
            person.name = name
        
        # Get user to check if this is first person
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        is_first_person = db.query(Person).filter(Person.user_id == user.id).count() == 1
        
        # Clear state
        user_state.state = None
        user_state.context = None
        db.commit()
        
        # Success message
        success_msg = f"✅ הפרופיל של {name} נשמר בהצלחה!\n\n"
        
        if is_first_person:
            # First person - onboarding complete
            success_msg += "מעולה! עכשיו אפשר להתחיל. ✨"
            from handlers.start import onboarding_complete
            await update.message.reply_text(success_msg)
            await onboarding_complete(update, context)
        else:
            success_msg += "אפשר להשתמש ב'סינון לפי האנשים שלי' או במספר אירוע."
            await update.message.reply_text(
                text=success_msg,
                reply_markup=back_to_main_keyboard()
            )


@log_handler
@handle_errors
@require_user_registered
async def people_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show list of people
    Section 4.1: Show list
    """
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    
    with db_session() as db:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        people = db.query(Person).filter(Person.user_id == user.id).all()
        
        if not people:
            await query.edit_message_text(
                text="אין לך אנשים ברשימה.\n\nלהתחלה מהירה: לחץ על 'הוסף אדם'",
                reply_markup=add_person_button()
            )
            return
        
        # Build list message
        message_text = "👥 הרשימה שלך:\n\n"
        
        for idx, person in enumerate(people, 1):
            examples_count = db.query(PersonExample).filter(PersonExample.person_id == person.id).count()
            message_text += f"{idx}. {person.name} ({examples_count} תמונות)\n"
        
        message_text += "\n💡 לחץ על שם כדי לערוך או למחוק"
        
        # Build inline keyboard with person names
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = []
        for person in people:
            keyboard.append([
                InlineKeyboardButton(
                    f"👤 {person.name}",
                    callback_data=f"people_view::{person.id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("➕ הוסף אדם", callback_data="people_add")
        ])
        keyboard.append([
            InlineKeyboardButton("🔙 חזרה", callback_data="people_menu")
        ])
        
        await query.edit_message_text(
            text=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


@log_handler
@handle_errors
@require_user_registered
async def people_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View person details"""
    query = update.callback_query
    await query.answer()
    
    person_id = int(query.data.split("::")[1])
    
    with db_session() as db:
        person = db.query(Person).filter(Person.id == person_id).first()
        
        if not person:
            await query.answer("אדם לא נמצא", show_alert=True)
            return
        
        examples_count = db.query(PersonExample).filter(PersonExample.person_id == person.id).count()
        
        message_text = (
            f"👤 {person.name}\n\n"
            f"📸 תמונות: {examples_count}\n"
            f"📅 נוצר: {person.created_at.strftime('%d/%m/%Y')}\n\n"
            "בחר/י פעולה:"
        )
        
        await query.edit_message_text(
            text=message_text,
            reply_markup=person_actions_keyboard(person_id)
        )


@log_handler
@handle_errors
@require_user_registered
async def people_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm person deletion"""
    query = update.callback_query
    await query.answer()
    
    person_id = int(query.data.split("::")[1])
    
    with db_session() as db:
        person = db.query(Person).filter(Person.id == person_id).first()
        
        if not person:
            await query.answer("אדם לא נמצא", show_alert=True)
            return
        
        message_text = f"❓ האם אתה בטוח שברצונך למחוק את {person.name}?\n\nכל התמונות והנתונים יימחקו."
        
        await query.edit_message_text(
            text=message_text,
            reply_markup=confirm_delete_keyboard(person_id)
        )


@log_handler
@handle_errors
@require_user_registered
async def people_delete_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete person after confirmation"""
    query = update.callback_query
    await query.answer("מוחק...")
    
    person_id = int(query.data.split("::")[1])
    telegram_id = update.effective_user.id
    
    with db_session() as db:
        person = db.query(Person).filter(Person.id == person_id).first()
        
        if not person:
            await query.answer("אדם לא נמצא", show_alert=True)
            return
        
        person_name = person.name
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        
        # Delete files
        storage_service.delete_person_files(user.id, person_id)
        
        # Delete from database (cascade will delete examples)
        db.delete(person)
        db.commit()
        
        # Check if list is now empty
        remaining_people = db.query(Person).filter(Person.user_id == user.id).count()
        
        message_text = f"✅ {person_name} נמחק בהצלחה."
        
        if remaining_people == 0:
            # Section 4.3: Empty list state
            message_text += "\n\nאין לך אנשים ברשימה.\n\nלהתחלה מהירה: לחץ על 'הוסף אדם'"
            await query.edit_message_text(
                text=message_text,
                reply_markup=add_person_button()
            )
        else:
            await query.edit_message_text(
                text=message_text,
                reply_markup=back_to_main_keyboard()
            )
