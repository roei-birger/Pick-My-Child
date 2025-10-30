"""
Decorators for bot handlers - ACK, typing, error handling
"""
import functools
import logging
from typing import Callable
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

logger = logging.getLogger(__name__)


def send_ack(ack_message: str = "✅ קיבלתי"):
    """
    Decorator to send ACK (acknowledgment) response immediately
    Ensures response within 1 second as per SLO
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            # Send ACK
            if update.callback_query:
                await update.callback_query.answer(ack_message)
            elif update.message:
                # For messages, send a quick reaction or typing indicator
                await context.bot.send_chat_action(
                    chat_id=update.effective_chat.id,
                    action=ChatAction.TYPING
                )
            
            # Execute the actual handler
            return await func(update, context, *args, **kwargs)
        
        return wrapper
    return decorator


def send_typing_action(func: Callable):
    """
    Decorator to send typing action during handler execution
    Shows "typing..." indicator to user
    """
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # Send typing action
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING
        )
        
        # Execute handler
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def handle_errors(func: Callable):
    """
    Decorator to handle errors gracefully
    Sends user-friendly error message only for real errors
    """
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            
            # Check if this is a "benign" error that we should ignore
            error_str = str(e).lower()
            benign_errors = [
                'message is not modified',
                'message to edit not found',
                'message can\'t be deleted',
                'message to delete not found',
                'query is too old',
                'message_id_invalid'
            ]
            
            # If it's a benign error, just log and continue
            if any(benign in error_str for benign in benign_errors):
                logger.info(f"Ignoring benign error in {func.__name__}: {e}")
                return None
            
            # Real error - inform user
            error_message = "❌ אופס! משהו השתבש. אנא נסה/י שוב או צור/י קשר עם התמיכה."
            
            # Try to send error message
            try:
                if update.callback_query:
                    await update.callback_query.answer(error_message, show_alert=True)
                elif update.message:
                    await update.message.reply_text(error_message)
            except Exception as send_error:
                logger.error(f"Failed to send error message: {send_error}")
            
            # Don't re-raise - we handled it
            return None
    
    return wrapper


def require_user_registered(func: Callable):
    """
    Decorator to ensure user is registered in database
    Creates user if doesn't exist
    """
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        from database import db_session
        from models import User
        
        telegram_user = update.effective_user
        
        with db_session() as db:
            # Check if user exists
            user = db.query(User).filter(User.telegram_id == telegram_user.id).first()
            
            if not user:
                # Create new user
                user = User(
                    telegram_id=telegram_user.id,
                    username=telegram_user.username,
                    first_name=telegram_user.first_name,
                    last_name=telegram_user.last_name
                )
                db.add(user)
                db.commit()
                logger.info(f"Created new user: {telegram_user.id}")
        
        # Store user_id in context for easy access
        context.user_data['db_user_id'] = telegram_user.id
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def log_handler(func: Callable):
    """Decorator to log handler execution"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        handler_name = func.__name__
        
        if update.message:
            logger.info(f"Handler {handler_name} called by user {user.id} with message")
        elif update.callback_query:
            logger.info(f"Handler {handler_name} called by user {user.id} with callback: {update.callback_query.data}")
        
        result = await func(update, context, *args, **kwargs)
        
        logger.debug(f"Handler {handler_name} completed")
        
        return result
    
    return wrapper


def combine_decorators(*decorators):
    """
    Combine multiple decorators into one
    Usage: @combine_decorators(log_handler, require_user_registered, send_typing_action, handle_errors)
    """
    def decorator(func):
        for dec in reversed(decorators):
            func = dec(func)
        return func
    return decorator
