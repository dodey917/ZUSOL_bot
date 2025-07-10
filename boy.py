import os
import random
import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters
)

# Bot configuration
BOT_TOKEN = "8188559911:AAFu2H1MTvgnG0FGiRlFbGXkOjso5d3U18A"
LINKS = {
    'channel': 'https://t.me/Yakstaschannel',
    'twitter': 'https://twitter.com/bigbangdist10',
    'group': 'https://t.me/yakstascapital'
}

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
AWAITING_TWITTER, AWAITING_WALLET = range(2)

# Game constants
INITIAL_SPEED = 1.0
SPEED_INCREMENT = 0.02
JUMP_HEIGHT = 2.8
GRAVITY = 0.4
OBSTACLE_FREQUENCY = 0.25
MAX_OBSTACLES = 5

# Store user game states
user_games = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message with instructions"""
    user = update.effective_user
    await update.message.reply_html(
        f"👋 <b>Hey {user.first_name}!</b> Welcome to Mr. Kayblezzy2's Airdrop Bot!\n\n"
        "🎮 <b>To qualify for 100 SOL airdrop:</b>\n"
        f"1. Join our channel: {LINKS['channel']}\n"
        f"2. Join our group: {LINKS['group']}\n"
        f"3. Follow our Twitter: {LINKS['twitter']}\n"
        "4. Submit your Solana wallet\n"
        "5. Play the runner game!\n\n"
        "🚀 Start with /verify to submit your details\n"
        "🎮 Play the game with /play\n\n"
        "<i>Note: This is a test bot - no real SOL will be sent</i>"
    )

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start verification process"""
    keyboard = [
        [InlineKeyboardButton("✅ I've Joined Everything", callback_data='joined')]
    ]
    await update.message.reply_text(
        "📢 <b>Please complete these steps:</b>\n"
        f"- Joined channel: {LINKS['channel']}\n"
        f"- Joined group: {LINKS['group']}\n"
        f"- Followed Twitter: {LINKS['twitter']}\n\n"
        "<i>Press the button below when done</i>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    return AWAITING_TWITTER

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'joined':
        await query.edit_message_text(
            "👍 <b>Great job!</b> Now send me your Twitter username (without @):",
            parse_mode='HTML'
        )
        return AWAITING_TWITTER

async def twitter_submitted(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store Twitter handle and request wallet"""
    twitter_handle = update.message.text.strip()
    context.user_data['twitter'] = twitter_handle
    
    await update.message.reply_text(
        f"🐦 <b>Twitter recorded:</b> @{twitter_handle}\n\n"
        "Now send me your <b>Solana wallet address</b>:",
        parse_mode='HTML'
    )
    return AWAITING_WALLET

async def wallet_submitted(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Validate and store wallet address"""
    solana_wallet = update.message.text.strip()
    
    # Basic Solana address validation
    if not re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', solana_wallet):
        await update.message.reply_text(
            "❌ <b>Invalid Solana address!</b> Please send a valid wallet address:",
            parse_mode='HTML'
        )
        return AWAITING_WALLET
    
    context.user_data['wallet'] = solana_wallet
    
    # Send 10 SOL confirmation
    await update.message.reply_text(
        f"🎉 <b>Congratulations!</b> 10 SOL is on its way to:\n"
        f"<code>{solana_wallet}</code>\n\n"
        "Well done! Hope you didn't cheat the system 😉\n\n"
        "🎮 Now play the game with /play to complete all tasks!\n\n"
        "<i>Note: This is a test bot - no real SOL will be sent</i>",
        parse_mode='HTML'
    )
    
    return ConversationHandler.END

async def play_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the runner game"""
    user_id = update.effective_user.id
    
    # Initialize game state
    user_games[user_id] = {
        'position': 0,
        'velocity': 0,
        'is_jumping': False,
        'obstacles': [],
        'score': 0,
        'speed': INITIAL_SPEED,
        'message_id': None
    }
    
    # Send initial game message
    await send_game_update(update, context, user_id)

async def send_game_update(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """Render and send game state"""
    if user_id not in user_games:
        return
    
    game = user_games[user_id]
    
    # Generate new obstacles
    if random.random() < OBSTACLE_FREQUENCY and len(game['obstacles']) < MAX_OBSTACLES:
        game['obstacles'].append(20)
    
    # Update obstacles
    game['obstacles'] = [obs - game['speed'] for obs in game['obstacles'] if obs > -1]
    
    # Update jumping physics
    if game['is_jumping']:
        game['position'] += game['velocity']
        game['velocity'] -= GRAVITY
        if game['position'] <= 0:
            game['position'] = 0
            game['is_jumping'] = False
    
    # Check collisions
    player_x = 3
    player_y = int(game['position'])
    collision = any(
        abs(obs - player_x) < 1.5 and player_y < 1.5
        for obs in game['obstacles']
    )
    
    # Build game board
    board = []
    for y in range(5, -1, -1):
        line = []
        for x in range(20):
            if y == 0:  # Ground
                char = "="
            elif not game['is_jumping'] and y == 1 and x == player_x:
                char = "🏃"  # Running
            elif game['is_jumping'] and y == player_y and x == player_x:
                char = "🦊"  # Jumping
            elif any(int(obs) == x and y < 2 for obs in game['obstacles']):
                char = "🪨"  # Obstacle
            else:
                char = " "
            line.append(char)
        board.append("".join(line))
    
    # Add ground line
    board.append("=" * 20)
    
    # Add score and speed
    game['score'] += 1
    board.append(f"\n<b>Score:</b> {game['score']}  |  <b>Speed:</b> {game['speed']:.1f}x")
    
    # Increase difficulty
    game['speed'] += SPEED_INCREMENT
    
    # Create keyboard
    keyboard = [
        [InlineKeyboardButton("🔼 JUMP", callback_data='jump')],
        [InlineKeyboardButton("🔄 Restart", callback_data='restart'), 
         InlineKeyboardButton("⏹ Stop", callback_data='stop')]
    ]
    
    # Game over check
    if collision:
        await handle_game_over(update, context, user_id)
        return
    
    # Send or update game message
    try:
        if game['message_id']:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=game['message_id'],
                text="\n".join(board),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        else:
            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="\n".join(board),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            game['message_id'] = message.message_id
    except Exception as e:
        logger.error(f"Error updating game: {e}")
        del user_games[user_id]
        return
    
    # Schedule next update
    context.job_queue.run_once(
        lambda ctx: send_game_update(update, ctx, user_id), 
        0.15, 
        user_id=user_id
    )

async def game_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle game buttons"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if user_id not in user_games:
        return
    
    game = user_games[user_id]
    
    if query.data == 'jump' and not game['is_jumping']:
        game['is_jumping'] = True
        game['velocity'] = JUMP_HEIGHT
    
    elif query.data == 'restart':
        game.update({
            'position': 0,
            'velocity': 0,
            'is_jumping': False,
            'obstacles': [],
            'score': 0,
            'speed': INITIAL_SPEED
        })
        await send_game_update(update, context, user_id)
    
    elif query.data == 'stop':
        try:
            await context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=game['message_id']
            )
        except:
            pass
        del user_games[user_id]
        await query.edit_message_text("🛑 Game stopped!")

async def handle_game_over(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """Handle game over scenario"""
    if user_id not in user_games:
        return
    
    game = user_games[user_id]
    final_score = game['score']
    wallet = context.user_data.get('wallet', 'YOUR_WALLET_ADDRESS')
    
    try:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=game['message_id'],
            text=f"💥 <b>GAME OVER!</b> 💥\n\n🏆 Final Score: {final_score}\n\n"
                 "Complete all tasks with /verify to qualify for the airdrop!",
            parse_mode='HTML'
        )
    except:
        pass
    
    # Check if user completed all tasks
    if 'twitter' in context.user_data and 'wallet' in context.user_data:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🎉 <b>CONGRATULATIONS!</b> 🎉\n\n"
                 "You passed Mr. Kayblezzy2's airdrop call!\n"
                 f"🏆 Final Score: <b>{final_score}</b>\n"
                 f"💸 100 SOL will be sent to:\n<code>{wallet}</code>\n\n"
                 "<i>Note: This is a test bot - no real SOL will be sent</i>",
            parse_mode='HTML'
        )
    
    if user_id in user_games:
        del user_games[user_id]

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current operation"""
    await update.message.reply_text('Operation cancelled.')
    return ConversationHandler.END

def main() -> None:
    """Run the bot"""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Set up conversation handler for verification
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('verify', verify)],
        states={
            AWAITING_TWITTER: [
                CallbackQueryHandler(button_handler, pattern='^joined$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, twitter_submitted)
            ],
            AWAITING_WALLET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_submitted)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Register handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('play', play_game))
    application.add_handler(CallbackQueryHandler(game_button))
    
    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()
