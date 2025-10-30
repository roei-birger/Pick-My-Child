"""
Events Handler - Create events, enter event codes, and retrieve matched photos
Implements Section 6: Event/Wedding Mode
"""
import logging
import json
import pickle
import numpy as np
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from database import db_session
from models import User, Person, PersonExample, Event, EventImage, UserState
from services import ai_service, storage_service, event_processor
from utils.decorators import handle_errors, require_user_registered, log_handler
from utils.keyboards import (
    event_created_keyboard,
    event_status_keyboard,
    event_pagination_keyboard,
    add_person_button,
    back_to_main_keyboard
)
from utils.validators import generate_event_code, validate_event_code, format_confidence_percentage
from config import settings

logger = logging.getLogger(__name__)


@log_handler
@handle_errors
@require_user_registered
async def create_event_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Start event creation flow
    Section 6.1: Create Event
    """
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    
    # Set user state
    with db_session() as db:
        user_state = db.query(UserState).filter(UserState.telegram_id == telegram_id).first()
        
        if not user_state:
            user_state = UserState(telegram_id=telegram_id)
            db.add(user_state)
        
        user_state.state = "CREATING_EVENT"
        user_state.context = None
        db.commit()
    
    message_text = (
        "📦 יצירת אירוע\n\n"
        "שלחו קובץ ZIP של תמונות האירוע.\n\n"
        f"💡 גודל מקסימלי: {settings.max_zip_size_mb}MB\n\n"
        "אם הקובץ גדול מדי, אפשר לשלוח קישור הורדה (Google Drive, Dropbox, וכו')."
    )
    
    await query.edit_message_text(
        text=message_text,
        reply_markup=back_to_main_keyboard()
    )


@log_handler
@handle_errors
@require_user_registered
async def handle_event_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle ZIP file upload for event
    """
    telegram_id = update.effective_user.id
    
    # Check if user is in CREATING_EVENT state
    with db_session() as db:
        user_state = db.query(UserState).filter(UserState.telegram_id == telegram_id).first()
        
        if not user_state or user_state.state != "CREATING_EVENT":
            return  # Not in event creation flow
        
        # Send ACK
        ack_msg = await update.message.reply_text("✅ קליטה בוצעה. מתחיל עיבוד...")
        
        # Get document (ZIP file)
        document = update.message.document
        
        # Validate file size
        if not storage_service.validate_zip_size(document.file_size):
            await ack_msg.edit_text(
                f"❌ הקובץ גדול מדי ({document.file_size / 1024 / 1024:.1f}MB). "
                f"המקסימום המותר: {settings.max_zip_size_mb}MB"
            )
            return
        
        # Download file
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.UPLOAD_DOCUMENT
        )
        
        file = await document.get_file()
        file_bytes = await file.download_as_bytearray()
        
        # Generate event code
        event_code = generate_event_code()
        
        # Save ZIP
        zip_path = storage_service.save_event_zip(bytes(file_bytes), event_code)
        
        # Create event in database
        event = Event(
            code=event_code,
            creator_telegram_id=telegram_id,
            status="UPLOADING",
            zip_file_path=str(zip_path)
        )
        db.add(event)
        db.commit()
        
        # Clear user state
        user_state.state = None
        db.commit()
        
        # Send event code to user
        message_text = (
            f"✅ מספר האירוע נוצר: {event_code}\n\n"
            f"העיבוד מתחיל כעת. זה עשוי לקחת מספר דקות.\n\n"
            f"תקבל/י הודעה כשהאירוע יהיה מוכן."
        )
        
        await ack_msg.edit_text(
            text=message_text,
            reply_markup=event_created_keyboard(event_code)
        )
        
        # Start background processing
        async def progress_callback(code: str, progress: int, message: str):
            """Callback for progress updates"""
            try:
                # Send progress update
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"🔄 {event_code}: {message}"
                )
                
                # Send push notification when ready
                if progress == 100:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=(
                            f"✅ האירוע שלך ({event_code}) מוכן!\n\n"
                            f"העיבוד הסתיים וכעת משתתפים יכולים להזין את הקוד ולקבל את התמונות שלהם."
                        ),
                        reply_markup=event_status_keyboard(event_code)
                    )
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
        
        # Start processing in background
        event_processor.start_processing(
            event_code,
            str(zip_path),
            db,
            progress_callback
        )


@log_handler
@handle_errors
@require_user_registered
async def event_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show event status
    Section 6.1: Status updates
    """
    query = update.callback_query
    await query.answer("מביא סטטוס...")
    
    event_code = query.data.split("::")[1]
    
    with db_session() as db:
        event = db.query(Event).filter(Event.code == event_code).first()
        
        if not event:
            await query.answer("אירוע לא נמצא", show_alert=True)
            return
        
        # Build status message
        status_emoji = {
            "UPLOADING": "📤",
            "PROCESSING": "⚙️",
            "READY": "✅",
            "FAILED": "❌"
        }
        
        emoji = status_emoji.get(event.status, "❓")
        
        message_text = f"{emoji} סטטוס אירוע {event_code}\n\n"
        
        if event.status == "UPLOADING":
            message_text += "מעלה קבצים..."
        
        elif event.status == "PROCESSING":
            message_text += f"מעבד... ({event.progress}%)\n\n"
            if event.progress_message:
                message_text += f"{event.progress_message}\n\n"
            message_text += f"עוברים על {event.processed_images} מתוך {event.total_images} תמונות"
        
        elif event.status == "READY":
            message_text += f"✅ מוכן!\n\n"
            message_text += f"סה\"כ תמונות: {event.total_images}\n"
            if event.ready_at:
                message_text += f"הושלם: {event.ready_at.strftime('%d/%m/%Y %H:%M')}"
        
        elif event.status == "FAILED":
            message_text += f"❌ נכשל\n\n"
            if event.progress_message:
                message_text += f"שגיאה: {event.progress_message}"
        
        await query.edit_message_text(
            text=message_text,
            reply_markup=event_status_keyboard(event_code)
        )


@log_handler
@handle_errors
@require_user_registered
async def enter_event_code_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Start entering event code flow
    Section 6.2: Enter event code
    """
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    
    # Check if user has people
    with db_session() as db:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        people_count = db.query(Person).filter(Person.user_id == user.id).count()
        
        if people_count == 0:
            # Section 4.3: Empty list
            await query.edit_message_text(
                text=(
                    "אין לך אנשים ברשימה.\n\n"
                    "להתחלה מהירה: 'ניהול האנשים שלי' → '➕ הוסף אדם'"
                ),
                reply_markup=add_person_button()
            )
            return
        
        # Set user state
        user_state = db.query(UserState).filter(UserState.telegram_id == telegram_id).first()
        
        if not user_state:
            user_state = UserState(telegram_id=telegram_id)
            db.add(user_state)
        
        user_state.state = "ENTERING_EVENT_CODE"
        db.commit()
    
    message_text = (
        "#️⃣ הזנת מספר אירוע\n\n"
        "הכנס/י את מספר האירוע (למשל: EVT-12345)"
    )
    
    await query.edit_message_text(
        text=message_text,
        reply_markup=back_to_main_keyboard()
    )


@log_handler
@handle_errors
@require_user_registered
async def handle_event_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle event code input from user
    """
    telegram_id = update.effective_user.id
    
    # Check if user is in ENTERING_EVENT_CODE state
    with db_session() as db:
        user_state = db.query(UserState).filter(UserState.telegram_id == telegram_id).first()
        
        if not user_state or user_state.state != "ENTERING_EVENT_CODE":
            return  # Not in event code flow
        
        event_code = update.message.text.strip().upper()
        
        # Validate format
        is_valid, error_message = validate_event_code(event_code)
        if not is_valid:
            await update.message.reply_text(f"❌ {error_message}")
            return
        
        # Check if event exists
        event = db.query(Event).filter(Event.code == event_code).first()
        
        if not event:
            await update.message.reply_text(
                f"❌ האירוע {event_code} לא נמצא.\n\n"
                f"אנא בדוק/י את המספר ונסה/י שוב."
            )
            return
        
        # Check event status
        if event.status == "PROCESSING":
            # Section 6.2: Still processing
            await update.message.reply_text(
                f"⏳ האירוע {event_code} עדיין בעיבוד.\n\n"
                f"התקדמות: {event.progress}%\n\n"
                f"אפשר להמתין כאן או לחזור מאוחר יותר.",
                reply_markup=event_status_keyboard(event_code)
            )
            return
        
        elif event.status == "FAILED":
            await update.message.reply_text(
                f"❌ העיבוד של האירוע {event_code} נכשל.\n\n"
                f"אנא צור/י קשר עם יוצר האירוע."
            )
            return
        
        elif event.status != "READY":
            await update.message.reply_text(
                f"❌ האירוע {event_code} אינו זמין כרגע."
            )
            return
        
        # Clear state
        user_state.state = None
        db.commit()
        
        # Event is READY - retrieve photos
        await retrieve_event_photos(update, context, event_code, cursor=0)


async def retrieve_event_photos(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    event_code: str,
    cursor: int = 0
):
    """
    Retrieve and send photos from event that match user's people
    Section 6.2: READY state - return photos
    """
    telegram_id = update.effective_user.id
    
    # Send ACK
    if cursor == 0:
        ack_msg = await update.message.reply_text(
            "✅ מביא את כל התמונות עם התאמה למישהו מהרשימה שלך..."
        )
    
    # Send typing action
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.UPLOAD_PHOTO
    )
    
    with db_session() as db:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        event = db.query(Event).filter(Event.code == event_code).first()
        
        if not event or event.status != "READY":
            await update.message.reply_text("❌ האירוע אינו זמין")
            return
        
        # Load FAISS index
        if not event.faiss_index_path:
            await update.message.reply_text("❌ אין אינדקס זמין לאירוע זה")
            return
        
        index = ai_service.load_index(event.faiss_index_path)
        
        # Load embedding mapping
        mapping_path = event.faiss_index_path.replace("faiss.index", "embedding_mapping.pkl")
        with open(mapping_path, 'rb') as f:
            embedding_to_image_id = pickle.load(f)
        
        # Get user's people embeddings
        people = db.query(Person).filter(Person.user_id == user.id).all()
        
        query_embeddings = []
        person_names = {}
        
        for person in people:
            examples = db.query(PersonExample).filter(PersonExample.person_id == person.id).all()
            
            for example in examples:
                if example.embedding:
                    embedding = np.frombuffer(example.embedding, dtype=np.float32)
                    query_embeddings.append(embedding)
                    person_names[len(query_embeddings) - 1] = person.name
        
        if not query_embeddings:
            await update.message.reply_text("❌ אין תמונות דוגמה לאנשים ברשימה")
            return
        
        # Search FAISS index
        k = min(100, index.ntotal)  # Top 100 matches
        results = ai_service.search_faiss_index(index, query_embeddings, k=k)
        
        # Collect unique matching images
        matching_image_ids = set()
        image_matches = {}  # image_id -> [(person_name, confidence), ...]
        
        for query_idx, matches in enumerate(results):
            person_name = person_names.get(query_idx, "Unknown")
            
            for faiss_idx, similarity in matches:
                if faiss_idx < len(embedding_to_image_id):
                    image_id = embedding_to_image_id[faiss_idx]
                    matching_image_ids.add(image_id)
                    
                    if image_id not in image_matches:
                        image_matches[image_id] = []
                    
                    # Add match if not already there for this person
                    existing_names = [m[0] for m in image_matches[image_id]]
                    if person_name not in existing_names:
                        image_matches[image_id].append((person_name, similarity))
        
        if not matching_image_ids:
            if cursor == 0:
                await ack_msg.delete()
            await update.message.reply_text("לא נמצאו תמונות מתאימות באירוע זה.")
            return
        
        # Get images for this batch
        image_ids_list = sorted(list(matching_image_ids))
        batch_start = cursor
        batch_end = min(cursor + settings.batch_size, len(image_ids_list))
        batch_image_ids = image_ids_list[batch_start:batch_end]
        
        # Delete ACK message before sending photos
        if cursor == 0:
            await ack_msg.delete()
        
        # Send photos
        for image_id in batch_image_ids:
            event_image = db.query(EventImage).filter(EventImage.id == image_id).first()
            
            if not event_image:
                continue
            
            # Build caption
            caption = "נמצאו התאמות ברשימה שלך:\n\n"
            
            # Sort matches by confidence
            sorted_matches = sorted(
                image_matches[image_id],
                key=lambda x: x[1],
                reverse=True
            )
            
            for person_name, confidence in sorted_matches:
                confidence_pct = format_confidence_percentage(confidence)
                caption += f"• {person_name} — {confidence_pct}\n"
            
            # Send photo
            try:
                if event_image.telegram_file_id:
                    # Photo already uploaded to Telegram
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=event_image.telegram_file_id,
                        caption=caption
                    )
                else:
                    # Upload from file
                    with open(event_image.file_path, 'rb') as photo_file:
                        sent_message = await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=photo_file,
                            caption=caption
                        )
                        
                        # Save telegram_file_id for future use
                        event_image.telegram_file_id = sent_message.photo[-1].file_id
                        db.commit()
            
            except Exception as e:
                logger.error(f"Error sending photo {image_id}: {e}")
        
        # Check if there are more
        has_more = batch_end < len(image_ids_list)
        
        # Send pagination controls
        pagination_msg = f"הוצגו {batch_end} מתוך {len(image_ids_list)} תמונות מתאימות."
        
        await update.message.reply_text(
            text=pagination_msg,
            reply_markup=event_pagination_keyboard(event_code, batch_end, has_more)
        )


@log_handler
@handle_errors
@require_user_registered
async def event_more_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Load more photos from event"""
    query = update.callback_query
    await query.answer("טוען עוד תמונות...")
    
    data_parts = query.data.split("::")
    event_code = data_parts[1]
    cursor = int(data_parts[2])
    
    # Retrieve next batch
    await retrieve_event_photos(update, context, event_code, cursor)


@log_handler
@handle_errors
@require_user_registered
async def event_stop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop retrieving event photos"""
    query = update.callback_query
    await query.answer("עצרתי")
    
    await query.edit_message_text(
        text="✅ הסתיים.",
        reply_markup=back_to_main_keyboard()
    )


@log_handler
@handle_errors
@require_user_registered
async def copy_event_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Copy event code to clipboard"""
    query = update.callback_query
    
    event_code = query.data.split("::")[1]
    
    await query.answer(f"מספר האירוע: {event_code}", show_alert=True)
