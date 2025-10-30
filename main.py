"""
pickmychild - Telegram Bot for Photo Filtering
Main entry point
"""
import logging
import sys
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

from config import settings
from database import init_db
from services import ai_service

# Import handlers
from handlers import (
    start_handler,
    main_menu_callback,
    people_menu_callback,
    people_add_callback,
    people_list_callback,
    people_view_callback,
    people_delete_callback,
    people_delete_confirm_callback,
    handle_person_photo,
    done_adding_person,
    handle_person_name,
    filter_people_callback,
    handle_filter_photo,
    ask_improve_model,
    improve_model_declined,
    improve_model_accepted,
    confirm_face_callback,
    create_event_callback,
    enter_event_code_callback,
    event_status_callback,
    event_more_callback,
    event_stop_callback,
    copy_event_callback,
    handle_event_zip,
    handle_event_code_input
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, settings.log_level.upper()),
    handlers=[
        logging.FileHandler(settings.log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def setup_handlers(application: Application):
    """
    Setup all bot handlers
    """
    # Command handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("add_person", people_add_callback))
    application.add_handler(CommandHandler("list_people", people_list_callback))
    application.add_handler(CommandHandler("done", done_adding_person))
    
    # Callback query handlers (inline buttons)
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    
    # People management callbacks
    application.add_handler(CallbackQueryHandler(people_menu_callback, pattern="^people_menu$"))
    application.add_handler(CallbackQueryHandler(people_add_callback, pattern="^people_add$"))
    application.add_handler(CallbackQueryHandler(people_list_callback, pattern="^people_list$"))
    application.add_handler(CallbackQueryHandler(people_view_callback, pattern="^people_view::"))
    application.add_handler(CallbackQueryHandler(people_delete_callback, pattern="^people_delete::(?!confirm)"))
    application.add_handler(CallbackQueryHandler(people_delete_confirm_callback, pattern="^people_delete_confirm::"))
    
    # Filter callbacks
    application.add_handler(CallbackQueryHandler(filter_people_callback, pattern="^filter_people$"))
    
    # Improve model callbacks
    application.add_handler(CallbackQueryHandler(ask_improve_model, pattern="^ask_improve_model$"))
    application.add_handler(CallbackQueryHandler(improve_model_declined, pattern="^improve_model_no$"))
    application.add_handler(CallbackQueryHandler(improve_model_accepted, pattern="^improve_model_yes$"))
    application.add_handler(CallbackQueryHandler(confirm_face_callback, pattern="^confirm_face_"))
    
    # Event callbacks
    application.add_handler(CallbackQueryHandler(create_event_callback, pattern="^create_event$"))
    application.add_handler(CallbackQueryHandler(enter_event_code_callback, pattern="^enter_event_code$"))
    application.add_handler(CallbackQueryHandler(event_status_callback, pattern="^event_status::"))
    application.add_handler(CallbackQueryHandler(event_more_callback, pattern="^event_more::"))
    application.add_handler(CallbackQueryHandler(event_stop_callback, pattern="^event_stop::"))
    application.add_handler(CallbackQueryHandler(copy_event_callback, pattern="^copy_event::"))
    
    # Message handlers
    # Photos (for filtering and person examples)
    application.add_handler(
        MessageHandler(
            filters.PHOTO & ~filters.COMMAND,
            handle_photo_dispatcher
        )
    )
    
    # Documents (for ZIP files)
    application.add_handler(
        MessageHandler(
            filters.Document.ALL & ~filters.COMMAND,
            handle_document_dispatcher
        )
    )
    
    # Text messages (for event codes, names, etc.)
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text_dispatcher
        )
    )
    
    logger.info("All handlers registered")


async def handle_photo_dispatcher(update: Update, context):
    """
    Dispatch photo messages to appropriate handler based on user state
    """
    from database import db_session
    from models import UserState
    
    telegram_id = update.effective_user.id
    
    with db_session() as db:
        user_state = db.query(UserState).filter(UserState.telegram_id == telegram_id).first()
        
        if user_state and user_state.state == "ADDING_PERSON":
            # User is adding person examples
            await handle_person_photo(update, context)
        else:
            # Default: filter mode
            await handle_filter_photo(update, context)


async def handle_document_dispatcher(update: Update, context):
    """
    Dispatch document messages to appropriate handler based on user state
    """
    from database import db_session
    from models import UserState
    
    telegram_id = update.effective_user.id
    
    with db_session() as db:
        user_state = db.query(UserState).filter(UserState.telegram_id == telegram_id).first()
        
        if user_state and user_state.state == "CREATING_EVENT":
            # User is uploading event ZIP
            await handle_event_zip(update, context)
        else:
            await update.message.reply_text(
                "לא ברור מה לעשות עם הקובץ הזה. אנא בחר/י פעולה מהתפריט."
            )


async def handle_text_dispatcher(update: Update, context):
    """
    Dispatch text messages to appropriate handler based on user state
    """
    from database import db_session
    from models import UserState
    
    telegram_id = update.effective_user.id
    
    with db_session() as db:
        user_state = db.query(UserState).filter(UserState.telegram_id == telegram_id).first()
        
        if user_state:
            if user_state.state == "NAMING_PERSON":
                # User is entering person name
                await handle_person_name(update, context)
                return
            
            elif user_state.state == "ENTERING_EVENT_CODE":
                # User is entering event code
                await handle_event_code_input(update, context)
                return
        
        # No active state - ignore or send help
        await update.message.reply_text(
            "לא הבנתי. השתמש/י ב-/start כדי לראות את התפריט הראשי."
        )


async def post_init(application: Application):
    """
    Post initialization - setup AI service
    """
    logger.info("Initializing AI service...")
    try:
        ai_service.initialize()
        logger.info("AI service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize AI service: {e}")
        logger.error("Bot may not function correctly without AI service")


def main():
    """
    Main function - start the bot
    """
    logger.info("Starting pickmychild bot...")
    
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized")
    
    # Create application
    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .build()
    )
    
    # Setup handlers
    setup_handlers(application)
    
    # Start bot
    logger.info("Bot is running... Press Ctrl+C to stop")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
