from . import *


def stageZero(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    global chatId, msgId, sentMsgId
    chatId = update.message.chat.id
    msgId = update.message.message_id
    buttonList: typing.List[str] = \
        [f'[{logFile}] [{botHelper.getHelper.readableSize(os.path.getsize(logFile))}]' for logFile in logFiles[0:3]]
    buttonList += ['All', 'Exit']
    sentMsgId = update.message.reply_text(text='Select:', reply_markup=InlineKeyboardMaker(buttonList).build(1)).message_id
    return FIRST


def stageOne(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    global chatId, msgId
    query = update.callback_query
    query.answer()
    if query.data in ['1', '2', '3', '4']:
        if query.data == '4':
            botHelper.bot.sendMediaGroup(media=[telegram.InputMediaDocument(logFile) for logFile in logFiles[0:3]],
                                         chat_id=chatId, reply_to_message_id=msgId, timeout=docSendTimeout)
            logger.info("Sent logFiles !")
        else:
            logFileIndex = int(query.data) - 1
            botHelper.bot.sendDocument(document=f"file://{botHelper.envVars['currWorkDir']}/{logFiles[logFileIndex]}",
                                       filename=logFiles[logFileIndex], chat_id=chatId, reply_to_message_id=msgId, timeout=docSendTimeout)
            logger.info(f"Sent logFile: '{logFiles[logFileIndex]}' !")
        botHelper.bot.deleteMessage(chat_id=chatId, message_id=sentMsgId)
    if query.data == '5':
        query.edit_message_text(text='Exited.')
    return telegram.ext.ConversationHandler.END


chatId: int
msgId: int
sentMsgId: int
docSendTimeout: int = 600
FIRST = range(1)[0]

handler = telegram.ext.ConversationHandler(
    entry_points=[telegram.ext.CommandHandler(BotCommands.Log.command, stageZero)],
    states={
        FIRST: [telegram.ext.CallbackQueryHandler(stageOne)]
    },
    fallbacks=[telegram.ext.CommandHandler(BotCommands.Log.command, stageZero)],
    conversation_timeout=120,
    run_async=True
)
