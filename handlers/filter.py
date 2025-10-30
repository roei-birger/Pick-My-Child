"""
Filter Handler - Filter photos by people in user's list  
Implements Section 5: Filter by My People
Supports both single photos and albums (media groups)
"""
import logging
import asyncio
import numpy as np
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from database import db_session
from models import User, Person, PersonExample
from services import ai_service
from utils.decorators import handle_errors, require_user_registered, log_handler
from utils.keyboards import add_person_button, back_to_main_keyboard
from utils.validators import format_confidence_percentage
from config import settings

logger = logging.getLogger(__name__)

# Store for user photo buffers (to accumulate photos from multiple albums)
user_photo_buffers = {}  # user_id -> {'photos': [...], 'task': asyncio.Task}


@log_handler
@handle_errors
@require_user_registered
async def filter_people_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Start filtering mode
    Section 5: Filter by My People
    """
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    
    with db_session() as db:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        people_count = db.query(Person).filter(Person.user_id == user.id).count()
        
        if people_count == 0:
            # Section 4.3: Empty list state
            await query.edit_message_text(
                text=(
                    "אין לך אנשים ברשימה.\n\n"
                    "להתחלה מהירה: 'ניהול האנשים שלי' → '➕ הוסף אדם'"
                ),
                reply_markup=add_person_button()
            )
            return
        
        message_text = (
            "🧭 סינון תמונות\n\n"
            "שלח/י תמונות (בודדות או אלבום) ואני אחזיר רק את אלו "
            "שבהן מופיעים אנשים מהרשימה שלך.\n\n"
            "💡 ככל שיהיו יותר תמונות דוגמה לכל אדם, כך הזיהוי יהיה מדויק יותר.\n\n"
            "⚠️ במצב סינון - פונקציות אחרות נעולות."
        )
        
        from utils.keyboards import filtering_mode_keyboard
        
        await query.edit_message_text(
            text=message_text,
            reply_markup=filtering_mode_keyboard()
        )
        
        # Set user in filtering mode
        context.user_data['filtering_mode'] = True


@log_handler
@handle_errors
@require_user_registered
async def handle_filter_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle photo in filtering mode
    Section 5.1-5.2: Process and return matching photos
    Accumulates photos from user and processes them together
    """
    message = update.message
    telegram_id = update.effective_user.id
    
    # Initialize user buffer if needed
    if telegram_id not in user_photo_buffers:
        user_photo_buffers[telegram_id] = {
            'photos': [],
            'task': None
        }
    
    # Add this photo to the user's buffer
    user_photo_buffers[telegram_id]['photos'].append(message)
    
    # Cancel existing task if any
    if user_photo_buffers[telegram_id]['task']:
        user_photo_buffers[telegram_id]['task'].cancel()
    
    # Create new delayed task (wait for more photos)
    async def process_user_photos():
        await asyncio.sleep(settings.photo_accumulation_timeout)
        await process_user_photo_buffer(telegram_id, context)
    
    user_photo_buffers[telegram_id]['task'] = asyncio.create_task(process_user_photos())


async def process_user_photo_buffer(telegram_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Process all accumulated photos for a user"""
    if telegram_id not in user_photo_buffers:
        return
    
    buffer_data = user_photo_buffers[telegram_id]
    photos = buffer_data['photos']
    
    if not photos:
        del user_photo_buffers[telegram_id]
        return
    
    logger.info(f"Processing {len(photos)} accumulated photos for user {telegram_id}")
    
    results = await process_photos(photos, context)
    
    # Send improve button after all photos processed
    if results and results.get('faces_for_improvement'):
        last_photo = photos[-1]
        await send_improve_button(last_photo, context, results['faces_for_improvement'])
    
    # Cleanup
    del user_photo_buffers[telegram_id]


async def process_photos(messages: list, context: ContextTypes.DEFAULT_TYPE):
    """
    Process one or more photos and return matching faces
    Returns dict with 'faces_for_improvement' list or None
    """
    if not messages:
        return None
    
    first_message = messages[0]
    telegram_id = first_message.from_user.id
    
    # Send ACK
    if len(messages) == 1:
        ack_msg = await first_message.reply_text("קיבלתי, בודק...")
    else:
        ack_msg = await first_message.reply_text(f"קיבלתי {len(messages)} תמונות, בודק...")
    
    # Send typing action
    await context.bot.send_chat_action(
        chat_id=first_message.chat_id,
        action=ChatAction.TYPING
    )
    
    all_faces_for_improvement = []
    processed_count = 0
    matched_count = 0
    is_batch = len(messages) > 1  # Flag to indicate if this is a batch of photos
    
    with db_session() as db:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        
        # Check if user has people
        people = db.query(Person).filter(Person.user_id == user.id).all()
        
        if not people:
            await ack_msg.edit_text(
                "אין לך אנשים ברשימה. להוספת אדם: /add_person"
            )
            return None
        
        # Get all embeddings for user's people
        person_embeddings = {}  # person_id -> {'name', 'embeddings'}
        
        for person in people:
            examples = db.query(PersonExample).filter(PersonExample.person_id == person.id).all()
            embeddings = []
            
            for example in examples:
                if example.embedding:
                    embedding = np.frombuffer(example.embedding, dtype=np.float32)
                    embeddings.append(embedding)
            
            if embeddings:
                person_embeddings[person.id] = {
                    'name': person.name,
                    'embeddings': embeddings
                }
        
        if not person_embeddings:
            await ack_msg.edit_text(
                "אין תמונות דוגמה לאנשים ברשימה. אנא הוסף תמונות דוגמה."
            )
            return None
        
        # Process each photo
        from services import storage_service
        from handlers.improve_model import extract_face_crop
        
        for msg in messages:
            photo = msg.photo[-1]  # Highest resolution
            photo_file = await photo.get_file()
            photo_bytes = await photo_file.download_as_bytearray()
            
            # Save temporarily
            temp_path = storage_service.save_uploaded_file(
                bytes(photo_bytes),
                user.id,
                ".jpg"
            )
            
            # Detect faces in photo
            faces = ai_service.detect_faces(str(temp_path))
            
            # Clean up temp file
            temp_path.unlink()
            
            if not faces:
                # Only send message for single photo, not in batch
                if not is_batch:
                    await msg.reply_text("לא נמצאו פנים בתמונה זו.")
                processed_count += 1
                continue
            
            # Find matches for each face
            matches_found = {}  # person_id -> max similarity
            
            logger.info(f"Comparing {len(faces)} detected faces against {len(person_embeddings)} people")
            
            for face_idx, face in enumerate(faces):
                face_embedding = face['embedding']
                logger.info(f"Processing face {face_idx+1}/{len(faces)} (confidence: {face['det_score']:.2f})")
                
                best_person_id = None
                best_similarity = 0
                
                # Compare with each person's embeddings
                for person_id, person_data in person_embeddings.items():
                    max_similarity = 0
                    similarities = []
                    
                    for person_embedding in person_data['embeddings']:
                        similarity = ai_service.compare_embeddings(face_embedding, person_embedding)
                        similarities.append(similarity)
                        max_similarity = max(max_similarity, similarity)
                    
                    person_name = person_data['name']
                    avg_similarity = np.mean(similarities) if similarities else 0
                    
                    logger.info(
                        f"  {person_name}: max={max_similarity:.3f}, avg={avg_similarity:.3f}, "
                        f"samples={len(similarities)}, threshold={settings.face_match_threshold}"
                    )
                    
                    # Track best match for this face (even if below threshold)
                    if max_similarity > best_similarity:
                        best_similarity = max_similarity
                        best_person_id = person_id
                    
                    # Check if above threshold for reporting
                    if max_similarity >= settings.face_match_threshold:
                        if person_id not in matches_found or matches_found[person_id] < max_similarity:
                            matches_found[person_id] = max_similarity
                            logger.info(f"  ✅ MATCH! {person_name} with score {max_similarity:.3f}")
                
                # Store face for improvement ONLY if match was found ABOVE threshold
                # This way we only ask user to confirm faces that were already successfully matched
                # Avoids overwhelming user with unmatched/weak faces
                if best_person_id is not None and best_similarity >= settings.face_match_threshold:
                    try:
                        face_crop = extract_face_crop(bytes(photo_bytes), face['bbox'])
                        all_faces_for_improvement.append({
                            'person_id': best_person_id,
                            'person_name': person_embeddings[best_person_id]['name'],
                            'face_crop': face_crop,
                            'embedding': face_embedding,
                            'bbox': face['bbox'],
                            'photo_file_id': photo.file_id
                        })
                        logger.info(f"  💡 Added face to improvement queue (matched with score {best_similarity:.3f})")
                    except Exception as e:
                        logger.error(f"Failed to extract face crop: {e}")
            
            if not matches_found:
                # Section 5.2: No matches
                # Only send message for single photo, not in batch to avoid flooding
                if not is_batch:
                    await msg.reply_text(
                        "לא נמצאו התאמות לאנשים מהרשימה שלך בתמונה זו."
                    )
                processed_count += 1
                continue
            
            # Build caption - Section 5.2: Caption format
            caption = "נמצאו התאמות ברשימה שלך:\n\n"
            
            # Sort by confidence (descending)
            sorted_matches = sorted(
                matches_found.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            for person_id, similarity in sorted_matches:
                person_name = person_embeddings[person_id]['name']
                confidence_pct = format_confidence_percentage(similarity)
                caption += f"• {person_name} — {confidence_pct}\n"
            
            # Send the photo back with caption
            await msg.reply_photo(
                photo=photo.file_id,
                caption=caption
            )
            
            processed_count += 1
            matched_count += 1
    
    # Delete ACK message
    await ack_msg.delete()
    
    # Send summary for batch processing
    if is_batch and processed_count > 0:
        skipped_count = processed_count - matched_count
        summary_text = f"✅ סיימתי לעבד {processed_count} תמונות\n\n"
        summary_text += f"📸 נמצאו התאמות: {matched_count} תמונות\n"
        if skipped_count > 0:
            summary_text += f"⏭️ דילגתי: {skipped_count} תמונות (ללא התאמות)"
        
        await first_message.reply_text(summary_text)
    
    logger.info(f"Processed {processed_count} photos, {matched_count} with matches, {len(all_faces_for_improvement)} faces for improvement")
    
    return {
        'faces_for_improvement': all_faces_for_improvement,
        'processed_count': processed_count,
        'matched_count': matched_count
    }


async def send_improve_button(message, context: ContextTypes.DEFAULT_TYPE, faces_for_improvement: list):
    """Send the 'improve model' button after filtering"""
    if not faces_for_improvement:
        return
    
    # Store faces in context
    context.user_data['improvement_session'] = {
        'faces_to_confirm': faces_for_improvement
    }
    
    keyboard = [
        [InlineKeyboardButton(
            "🎯 עזור לשפר את הזיהוי",
            callback_data="ask_improve_model"
        )]
    ]
    
    face_count = len(faces_for_improvement)
    await message.reply_text(
        text=(
            f"💡 זוהו {face_count} פנים בהצלחה!\n\n"
            "רוצה להוסיף את הפנים האלה למאגר התמונות?\n"
            "זה ישפר את דיוק הזיהוי בעתיד! 🎯"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


@log_handler
@handle_errors
@require_user_registered
async def handle_filter_album(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle album/media group in filtering mode
    Note: This is now handled automatically by handle_filter_photo
    """
    pass
