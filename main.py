import logging
import asyncio
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

from config import Config
from database import Database
from utils import parse_filename, format_flight_time, format_days_count, escape_markdown
from ui import generate_tree_text, create_navigation_keyboard, create_session_view_keyboard, create_flight_view_keyboard

# Initialize configuration and database
config = Config()
db = Database(config.database_path)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, config.log_level, logging.INFO)
)
log = logging.getLogger(__name__)

class iFLYBot:
    """Main bot class."""
    
    def __init__(self):
        self.config = config
        self.db = db
    
    # Utility methods
    async def send_closable_message(self, update: Update, text: str):
        """Send a message with a close button."""
        message = await update.message.reply_text(text, parse_mode='MarkdownV2')
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Close", callback_data=f"delete:{update.message.chat_id}:{message.message_id}")]
        ])
        return await message.edit_text(text, parse_mode='MarkdownV2', reply_markup=reply_markup)
    
    async def delete_message(self, context: CallbackContext, chat_id: int, message_id: int):
        """Delete a message."""
        try:
            await context.bot.delete_message(chat_id, message_id)
        except Exception as e:
            log.error(f"Error deleting message: {e}")
    
    # Command handlers
    async def start(self, update: Update, context: CallbackContext):
        """Start command handler."""
        try:
            await update.message.delete()
            
            if update.message.chat_id == self.config.ifly_chat_id:
                # iFLY chat - start authentication process
                await self.ask_for_username(update, context)
            else:
                # Private chat - show main menu
                self.db.add_user(update.message.chat_id, update.message.from_user.username)
                await self.show_start_menu(update, context)
        except Exception as e:
            log.error(f"Error in start command: {e}")
    
    async def help(self, update: Update, context: CallbackContext):
        """Help command handler."""
        try:
            await update.message.delete()
            
            if update.message.chat_id == self.config.ifly_chat_id:
                text = "You can send your videos to your bot after completing authentication\\."
            else:
                text = ("Available commands:\n"
                       "/start \\- Shows menu\n"
                       "/help \\- Shows this message\n"
                       "/info \\- Shows info message\n"
                       "/clear\\_data \\- Careful\\! Deletes all saved videos\\!\n\n"
                       "To upload videos \\- just drop them here\\. Bot will automatically find their correct flight\\.")
            
            await self.send_closable_message(update, text)
        except Exception as e:
            log.error(f"Error in help command: {e}")
    
    async def clear_data(self, update: Update, context: CallbackContext):
        """Clear all user data."""
        try:
            await update.message.delete()
            # This would require additional database method to clear user videos
            # For now, just show a message
            await self.send_closable_message(update, "Data clearing not implemented in this version\\.")
        except Exception as e:
            log.error(f"Error in clear_data command: {e}")
    
    # Menu handlers
    async def show_start_menu(self, update: Update, context: CallbackContext, edit: bool = False):
        """Show the main start menu."""
        try:
            text = "🏠 Welcome to the *iFLY Video Storage Bot*\\!\nUse buttons to navigate\\."
            keyboard = [
                [
                    InlineKeyboardButton("🎥 Browse Videos", callback_data="nav:library"),
                    InlineKeyboardButton("📊 My Stats", callback_data="stats")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if edit and hasattr(update, 'callback_query'):
                try:
                    await update.callback_query.edit_message_text(text, parse_mode='MarkdownV2', reply_markup=reply_markup)
                except Exception as inner_e:
                    if "no text in the message" in str(inner_e).lower():
                        # Coming from video message - delete and send new text message
                        chat_id = update.callback_query.from_user.id
                        await update.callback_query.message.delete()
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=text,
                            parse_mode='MarkdownV2',
                            reply_markup=reply_markup
                        )
                    else:
                        raise
            else:
                await update.message.reply_text(text, parse_mode='MarkdownV2', reply_markup=reply_markup)
        except Exception as e:
            log.error(f"Error showing start menu: {e}")
    
    async def show_statistics(self, update: Update, context: CallbackContext):
        """Show user statistics."""
        try:
            chat_id = update.callback_query.from_user.id
            stats = self.db.get_user_stats(chat_id)
            
            days_text = format_days_count(stats['days_since_first_flight'])
            time_text = format_flight_time(stats['total_flight_time'])
            
            text = (f"📊 *Here are some fun stats*:\n"
                   f"`  `*•*` `🛫 You started flying *{escape_markdown(days_text)} ago*\n"
                   f"`  `*•*` `⏱️ Total tunnel time: *{escape_markdown(time_text)}*")
            
            keyboard = [[InlineKeyboardButton("← Back", callback_data="home")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(text, parse_mode='MarkdownV2', reply_markup=reply_markup)
        except Exception as e:
            log.error(f"Error showing statistics: {e}")
    
    # Navigation handlers
    async def navigate_library(self, update: Update, context: CallbackContext, day_index: int = None):
        """Navigate the video library."""
        try:
            chat_id = update.callback_query.from_user.id
            organized_data = self.db.get_organized_videos(chat_id)
            
            if not organized_data['days']:
                text = "📦 *Library*\n\nNo videos uploaded yet\\. Send your videos here to get started\\!"
                keyboard = [[InlineKeyboardButton("← Back", callback_data="home")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
            else:
                text = generate_tree_text(organized_data, day_index)
                reply_markup = create_navigation_keyboard(organized_data, day_index)
            
            # Log generated text for debugging markdown issues
            log.debug(f"navigate_library text (len={len(text)}):\n{text}")
            try:
                await update.callback_query.edit_message_text(text, parse_mode='MarkdownV2', reply_markup=reply_markup)
            except Exception as inner_e:
                if "code entity" in str(inner_e):
                    # Fallback: try again without markdown to avoid user-facing error
                    log.warning(f"Markdown parse failed, falling back to plain text: {inner_e}")
                    await update.callback_query.edit_message_text(text.replace('*', ''), reply_markup=reply_markup)
                elif "no text in the message" in str(inner_e).lower():
                    # Coming from video message - delete and send new text message
                    await update.callback_query.message.delete()
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode='MarkdownV2',
                        reply_markup=reply_markup
                    )
                else:
                    raise
        except Exception as e:
            log.error(f"Error navigating library: {e}")
    
    async def show_session(self, update: Update, context: CallbackContext, day_index: int, session_index: int):
        """Show session with flights."""
        try:
            chat_id = update.callback_query.from_user.id
            organized_data = self.db.get_organized_videos(chat_id)
            
            day = organized_data['days'][day_index]
            session = day['sessions'][session_index]
            
            text = (f"🕐 *Session {escape_markdown(session['time_slot'])}*\n"
                   f"📅 {escape_markdown(datetime.fromtimestamp(day['date']).strftime('%d.%m.%Y'))}\n\n"
                   f"Select a flight:")
            
            reply_markup = create_session_view_keyboard(organized_data, day_index, session_index)
            
            try:
                await update.callback_query.edit_message_text(text, parse_mode='MarkdownV2', reply_markup=reply_markup)
            except Exception as inner_e:
                if "no text in the message" in str(inner_e).lower():
                    # Coming from video message - delete and send new text message
                    await update.callback_query.message.delete()
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode='MarkdownV2',
                        reply_markup=reply_markup
                    )
                else:
                    raise
        except Exception as e:
            log.error(f"Error showing session: {e}")
    
    async def show_flight(self, update: Update, context: CallbackContext, day_index: int, session_index: int, flight_index: int, video_index: int = 0):
        """Show flight with videos."""
        try:
            chat_id = update.callback_query.from_user.id
            organized_data = self.db.get_organized_videos(chat_id)
            
            day = organized_data['days'][day_index]
            session = day['sessions'][session_index]
            flight = session['flights'][flight_index]
            
            if not flight['videos']:
                text = "No videos found for this flight\\."
                keyboard = [[InlineKeyboardButton("← Back", callback_data=f"nav:session:{day_index}:{session_index}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.callback_query.edit_message_text(text, parse_mode='MarkdownV2', reply_markup=reply_markup)
                return
            
            video = flight['videos'][video_index]
            
            reply_markup = create_flight_view_keyboard(organized_data, day_index, session_index, flight_index, video_index)
            
            # Send video
            await update.callback_query.message.delete()
            message = await context.bot.send_video(
                chat_id=chat_id,
                video=video['file_id'],
                caption=f"🎬 *Flight {escape_markdown(flight['flight_number'])}* \\- {escape_markdown(video['camera_name'])}",
                parse_mode='MarkdownV2',
                reply_markup=reply_markup
            )
        except Exception as e:
            log.error(f"Error showing flight: {e}")
    
    # Video upload handler
    async def upload_video(self, update: Update, context: CallbackContext):
        """Handle video uploads."""
        try:
            # Determine target chat_id
            if update.message.chat_id == self.config.ifly_chat_id:
                # iFLY chat - check for active session
                session = self.db.get_active_session()
                if not session:
                    await update.message.delete()
                    return
                target_chat_id = session['target_chat_id']
            else:
                # Private chat
                self.db.add_user(update.message.chat_id, update.message.from_user.username)
                target_chat_id = update.message.chat_id
            
            video = update.message.video
            file_id = video.file_id
            file_name = video.file_name
            duration = round(video.duration / 5) * 5  # Round to nearest 5 seconds
            
            # Parse filename
            try:
                flight_date, time_slot, flight_number, camera_name = parse_filename(file_name)
            except Exception as e:
                log.error(f"Error parsing filename {file_name}: {e}")
                await update.message.delete()
                return
            
            # Add video to database
            success = self.db.add_video(
                target_chat_id, file_id, file_name, duration,
                flight_date, time_slot, flight_number, camera_name
            )
            
            if success:
                log.info(f"Video {file_name} added successfully for user {target_chat_id}")
            else:
                log.info(f"Video {file_name} already exists for user {target_chat_id}")
            
            await update.message.delete()
        except Exception as e:
            log.error(f"Error uploading video: {e}")
    
    # iFLY chat authentication
    async def ask_for_username(self, update: Update, context: CallbackContext):
        """Ask for username in iFLY chat."""
        try:
            text = "To upload videos \\- please send your username"
            
            # Get or create menu message
            menu_message_id = self.db.get_system_value("ifly_menu_message_id")
            if menu_message_id:
                try:
                    await context.bot.edit_message_text(text, self.config.ifly_chat_id, int(menu_message_id))
                except:
                    # Create new message if edit fails
                    message = await context.bot.send_message(self.config.ifly_chat_id, text)
                    self.db.set_system_value("ifly_menu_message_id", str(message.message_id))
            else:
                message = await context.bot.send_message(self.config.ifly_chat_id, text)
                self.db.set_system_value("ifly_menu_message_id", str(message.message_id))
        except Exception as e:
            log.error(f"Error asking for username: {e}")
    
    async def check_username(self, update: Update, context: CallbackContext):
        """Check username and start session."""
        try:
            await update.message.delete()
            
            session = self.db.get_active_session()
            if session:
                return  # Session already active
            
            username = update.message.text.strip()
            user = self.db.get_user_by_username(username)
            
            if user:
                text = f"Found user @{escape_markdown(username)}\\. Start session?"
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Yes", callback_data=f"auth:start:{user['chat_id']}:{username}"),
                        InlineKeyboardButton("❌ No", callback_data="auth:cancel")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                menu_message_id = self.db.get_system_value("ifly_menu_message_id")
                if menu_message_id:
                    await context.bot.edit_message_text(text, self.config.ifly_chat_id, int(menu_message_id), 
                                                      parse_mode='MarkdownV2', reply_markup=reply_markup)
            else:
                text = f"User @{escape_markdown(username)} not found\\. Please try again or ask them to start the bot first\\."
                menu_message_id = self.db.get_system_value("ifly_menu_message_id")
                if menu_message_id:
                    await context.bot.edit_message_text(text, self.config.ifly_chat_id, int(menu_message_id), parse_mode='MarkdownV2')
        except Exception as e:
            log.error(f"Error checking username: {e}")
    
    async def handle_auth_callback(self, update: Update, context: CallbackContext, action: str, data: str = None):
        """Handle authentication callbacks."""
        try:
            if action == "start":
                # Start session
                parts = data.split(':')
                target_chat_id = int(parts[0])
                username = parts[1]
                
                success = self.db.create_session(target_chat_id, username, self.config.session_length_minutes)
                if success:
                    expires_time = datetime.now() + timedelta(minutes=self.config.session_length_minutes)
                    text = (f"✅ *Session started for @{escape_markdown(username)}*\n\n"
                           f"You can now send videos\\. Session expires at "
                           f"{escape_markdown(expires_time.strftime('%H:%M'))}\\.")
                    keyboard = [[InlineKeyboardButton("🛑 End Session", callback_data="auth:end")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                else:
                    text = "❌ Failed to start session\\. Please try again\\."
                    reply_markup = None
            elif action == "cancel":
                await self.ask_for_username(update, context)
                return
            elif action == "end":
                self.db.end_session()
                await self.ask_for_username(update, context)
                return
            else:
                return
            
            menu_message_id = self.db.get_system_value("ifly_menu_message_id")
            if menu_message_id:
                await context.bot.edit_message_text(text, self.config.ifly_chat_id, int(menu_message_id),
                                                  parse_mode='MarkdownV2', reply_markup=reply_markup)
        except Exception as e:
            log.error(f"Error handling auth callback: {e}")
    
    # Callback query handler
    async def callback_handler(self, update: Update, context: CallbackContext):
        """Handle all callback queries."""
        try:
            query = update.callback_query
            await query.answer()
            
            data = query.data
            parts = data.split(':')
            
            if update.callback_query.message.chat_id == self.config.ifly_chat_id:
                # iFLY chat callbacks
                if parts[0] == "auth":
                    action = parts[1]
                    callback_data = ':'.join(parts[2:]) if len(parts) > 2 else None
                    await self.handle_auth_callback(update, context, action, callback_data)
            else:
                # Private chat callbacks
                if parts[0] == "home":
                    await self.show_start_menu(update, context, edit=True)
                elif parts[0] == "stats":
                    await self.show_statistics(update, context)
                elif parts[0] == "nav":
                    if parts[1] == "library":
                        await self.navigate_library(update, context)
                    elif parts[1] == "day":
                        day_index = int(parts[2])
                        await self.navigate_library(update, context, day_index)
                    elif parts[1] == "session":
                        day_index, session_index = int(parts[2]), int(parts[3])
                        await self.show_session(update, context, day_index, session_index)
                    elif parts[1] == "flight":
                        day_index, session_index, flight_index = int(parts[2]), int(parts[3]), int(parts[4])
                        await self.show_flight(update, context, day_index, session_index, flight_index)
                elif parts[0] == "video":
                    day_index, session_index, flight_index, video_index = map(int, parts[1:5])
                    await self.show_flight(update, context, day_index, session_index, flight_index, video_index)
                elif parts[0] == "delete":
                    chat_id, message_id = int(parts[1]), int(parts[2])
                    await self.delete_message(context, chat_id, message_id)
        except Exception as e:
            log.error(f"Error handling callback: {e}")

def main():
    """Main function to start the bot."""
    bot = iFLYBot()
    
    application = ApplicationBuilder().token(config.bot_token).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help))
    application.add_handler(CommandHandler("clear_data", bot.clear_data))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.VIDEO, bot.upload_video))
    application.add_handler(MessageHandler(filters.Chat(config.ifly_chat_id) & filters.TEXT, bot.check_username))
    
    # Callback handler
    application.add_handler(CallbackQueryHandler(bot.callback_handler))
    
    print("iFLY Videos Bot Online")
    application.run_polling()

if __name__ == "__main__":
    main()
