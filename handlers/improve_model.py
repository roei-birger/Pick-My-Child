"""
Improve Model Handler - Allow users to add filtered photos to their model
Implements interactive face confirmation to improve recognition accuracy
"""
import logging
import numpy as np
import cv2
import io
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from database import db_session
from models import User, Person, PersonExample
from services import ai_service, storage_service
from utils.decorators import handle_errors, require_user_registered, log_handler
from config import settings

logger = logging.getLogger(__name__)


@log_handler
@handle_errors
@require_user_registered
async def ask_improve_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ask user if they want to help improve the model after filtering
    Called after successful face detection in filter
    """
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("✅ כן, אשמח לעזור", callback_data="improve_model_yes"),
            InlineKeyboardButton("❌ לא, תודה", callback_data="improve_model_no")
        ]
    ]
    
    text = (
        "🎯 הוספת תמונות למודל\n\n"
        "האם תרצה/י להוסיף את הפנים שזוהו למאגר התמונות?\n\n"
        "אציג לך כל פנים שזוהה ואת/ה תאשר/י שזה באמת האדם הנכון.\n\n"
        "כל תמונה שתתווסף תשפר את הדיוק! 🚀"
    )
    
    try:
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        # If edit fails, send new message
        logger.warning(f"Could not edit message: {e}")
        await query.message.reply_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


@log_handler
@handle_errors
@require_user_registered
async def improve_model_declined(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User declined to improve model"""
    query = update.callback_query
    await query.answer("בסדר גמור!")
    
    from utils.keyboards import main_menu_keyboard
    
    try:
        await query.edit_message_text(
            text="בסדר! תמיד אפשר לעשות זאת מאוחר יותר.\n\nחזרה לתפריט הראשי:",
            reply_markup=main_menu_keyboard()
        )
    except Exception as e:
        # If edit fails, send new message
        logger.warning(f"Could not edit message: {e}")
        await query.message.reply_text(
            text="בסדר! תמיד אפשר לעשות זאת מאוחר יותר.\n\nחזרה לתפריט הראשי:",
            reply_markup=main_menu_keyboard()
        )
    
    # Clear improvement session data
    if 'improvement_session' in context.user_data:
        del context.user_data['improvement_session']


@log_handler
@handle_errors
@require_user_registered
async def improve_model_accepted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    User accepted to improve model
    Start showing faces one by one for confirmation
    """
    query = update.callback_query
    await query.answer("נהדר!")
    
    # Get the improvement session data
    if 'improvement_session' not in context.user_data:
        try:
            await query.edit_message_text(
                text="לא נמצא מידע על תמונות לשיפור. אנא נסה/י שוב."
            )
        except:
            await query.message.reply_text(
                text="לא נמצא מידע על תמונות לשיפור. אנא נסה/י שוב."
            )
        return
    
    session = context.user_data['improvement_session']
    
    if not session.get('faces_to_confirm'):
        try:
            await query.edit_message_text(
                text="אין פנים לאישור."
            )
        except:
            await query.message.reply_text(
                text="אין פנים לאישור."
            )
        return
    
    # Initialize counters
    session['current_index'] = 0
    session['confirmed_count'] = 0
    session['rejected_count'] = 0
    
    # Show first face
    await show_next_face(update, context)


async def show_next_face(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the next face for confirmation"""
    try:
        session = context.user_data.get('improvement_session', {})
        current_index = session.get('current_index', 0)
        faces_to_confirm = session.get('faces_to_confirm', [])
        
        if current_index >= len(faces_to_confirm):
            # All faces processed - show summary
            await show_improvement_summary(update, context)
            return
        
        face_data = faces_to_confirm[current_index]
        person_name = face_data['person_name']
        person_id = face_data['person_id']
        face_crop_bytes = face_data['face_crop']
        
        # Create keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ כן, זה הוא/היא", callback_data=f"confirm_face_{person_id}_yes"),
                InlineKeyboardButton("❌ לא, זה לא הוא/היא", callback_data=f"confirm_face_{person_id}_no")
            ]
        ]
        
        # Send the cropped face
        caption = (
            f"זיהוי: {person_name}\n\n"
            f"האם זה באמת {person_name}?\n\n"
            f"תמונה {current_index + 1} מתוך {len(faces_to_confirm)}"
        )
        
        if update.callback_query:
            # First face or after callback
            await update.callback_query.message.reply_photo(
                photo=face_crop_bytes,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            # Delete the previous message
            try:
                await update.callback_query.message.delete()
            except:
                pass
        else:
            # Shouldn't happen, but handle it
            await update.message.reply_photo(
                photo=face_crop_bytes,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        logger.error(f"Error showing next face: {e}", exc_info=True)
        # Don't show error to user - just log it


@log_handler
@handle_errors
@require_user_registered
async def confirm_face_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle face confirmation (yes/no)"""
    query = update.callback_query
    await query.answer()
    
    # Parse callback data: confirm_face_{person_id}_{yes/no}
    parts = query.data.split('_')
    person_id = int(parts[2])
    confirmed = parts[3] == 'yes'
    
    session = context.user_data.get('improvement_session', {})
    current_index = session.get('current_index', 0)
    faces_to_confirm = session.get('faces_to_confirm', [])
    
    if current_index >= len(faces_to_confirm):
        return
    
    face_data = faces_to_confirm[current_index]
    
    if confirmed:
        # Add this face to the person's examples
        telegram_id = update.effective_user.id
        
        with db_session() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            person = db.query(Person).filter(Person.id == person_id, Person.user_id == user.id).first()
            
            if person:
                # Save the face crop
                face_crop_bytes = face_data['face_crop']
                file_extension = ".jpg"
                
                # Save to storage
                saved_path = storage_service.save_uploaded_file(
                    face_crop_bytes.read() if hasattr(face_crop_bytes, 'read') else face_crop_bytes,
                    user.id,
                    file_extension
                )
                
                # Generate embedding for this face
                embedding = face_data.get('embedding')
                if embedding is not None:
                    embedding_bytes = embedding.tobytes()
                else:
                    # Extract embedding from the saved image
                    embedding_array = ai_service.get_embedding(str(saved_path))
                    embedding_bytes = embedding_array.tobytes() if embedding_array is not None else None
                
                # Create new example
                new_example = PersonExample(
                    person_id=person.id,
                    file_path=str(saved_path),
                    embedding=embedding_bytes
                )
                
                db.add(new_example)
                db.commit()
                
                logger.info(f"Added new example for person {person.name} (ID: {person_id})")
                session['confirmed_count'] = session.get('confirmed_count', 0) + 1
    else:
        session['rejected_count'] = session.get('rejected_count', 0) + 1
    
    # Move to next face
    session['current_index'] = current_index + 1
    context.user_data['improvement_session'] = session
    
    await show_next_face(update, context)


async def show_improvement_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show summary after all faces processed"""
    try:
        session = context.user_data.get('improvement_session', {})
        confirmed_count = session.get('confirmed_count', 0)
        rejected_count = session.get('rejected_count', 0)
        total = confirmed_count + rejected_count
        
        telegram_id = update.effective_user.id
        
        # Get updated statistics
        with db_session() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            people = db.query(Person).filter(Person.user_id == user.id).all()
            
            stats_text = ""
            for person in people:
                example_count = db.query(PersonExample).filter(PersonExample.person_id == person.id).count()
                stats_text += f"• {person.name}: {example_count} תמונות דוגמה\n"
        
        from utils.keyboards import main_menu_keyboard
        
        message_text = (
            "🎉 תודה רבה!\n\n"
            f"✅ אושרו: {confirmed_count} תמונות\n"
            f"❌ נדחו: {rejected_count} תמונות\n\n"
            "📊 סטטיסטיקת המודל המעודכנת:\n\n"
            f"{stats_text}\n"
            "הדיוק משתפר עם כל תמונה שמתווספת! 🚀"
        )
        
        if update.callback_query:
            await update.callback_query.message.reply_text(
                text=message_text,
                reply_markup=main_menu_keyboard()
            )
            try:
                await update.callback_query.message.delete()
            except:
                pass
        else:
            await update.message.reply_text(
                text=message_text,
                reply_markup=main_menu_keyboard()
            )
        
        # Clear session
        if 'improvement_session' in context.user_data:
            del context.user_data['improvement_session']
    except Exception as e:
        logger.error(f"Error showing improvement summary: {e}", exc_info=True)
        # Try to send a simple message
        try:
            from utils.keyboards import main_menu_keyboard
            if update.callback_query:
                await update.callback_query.message.reply_text(
                    "תודה על העזרה! חזרה לתפריט הראשי:",
                    reply_markup=main_menu_keyboard()
                )
            elif update.message:
                await update.message.reply_text(
                    "תודה על העזרה! חזרה לתפריט הראשי:",
                    reply_markup=main_menu_keyboard()
                )
        except:
            pass


def extract_face_crop(image_bytes: bytes, bbox: list, padding: float = 0.3) -> io.BytesIO:
    """
    Extract and crop face from image with padding
    
    Args:
        image_bytes: Original image bytes
        bbox: [x1, y1, x2, y2] bounding box
        padding: Padding around face (0.3 = 30% extra)
    
    Returns:
        BytesIO object with cropped face image
    """
    # Convert bytes to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise ValueError("Could not decode image")
    
    h, w = img.shape[:2]
    
    # Extract bbox coordinates
    x1, y1, x2, y2 = [int(coord) for coord in bbox]
    
    # Calculate padding
    face_w = x2 - x1
    face_h = y2 - y1
    pad_w = int(face_w * padding)
    pad_h = int(face_h * padding)
    
    # Apply padding with bounds checking
    x1 = max(0, x1 - pad_w)
    y1 = max(0, y1 - pad_h)
    x2 = min(w, x2 + pad_w)
    y2 = min(h, y2 + pad_h)
    
    # Crop face
    face_crop = img[y1:y2, x1:x2]
    
    # Encode to JPEG
    _, buffer = cv2.imencode('.jpg', face_crop)
    
    return io.BytesIO(buffer.tobytes())
