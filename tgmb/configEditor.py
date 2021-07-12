from . import *


def loadConfigDat():
    global envNames, envValues, envNamesNew, envValuesNew
    envNames, envValues, envNamesNew, envValuesNew = [], [], [], []
    envNames, envValues = loadDat(configEnvFile)


def choose(update: telegram.Update = None, query: telegram.CallbackQuery = None) -> int:
    global envNames, tempKeyIndex, tempKeyValue
    tempKeyIndex, tempKeyValue = '', ''
    if query is None:
        update.message.reply_text(text="Select an Environment Variable:",
                                  reply_markup=InlineKeyboardMaker(envNames + ['Exit']).build(1))
    if update is None:
        query.edit_message_text(text="Select an Environment Variable:",
                                reply_markup=InlineKeyboardMaker(envNames + ['Exit']).build(1))
    return FIRST


def view(query: telegram.CallbackQuery) -> int:
    global envNames, envValues, tempKeyIndex
    tempKeyIndex = f'{int(query.data) - 1}'
    if not int(tempKeyIndex) == len(envNames):
        query.edit_message_text(text=f'{envNames[int(tempKeyIndex)]} = {envValues[int(tempKeyIndex)]}',
                                reply_markup=InlineKeyboardMaker(['Edit', 'Back']).build(2))
        return SECOND
    else:
        return end(query)


def edit(query: telegram.CallbackQuery) -> int:
    global envNames, tempKeyIndex
    query.edit_message_text(text=f'Send New Value for {envNames[int(tempKeyIndex)]}:',
                            reply_markup=InlineKeyboardMaker(['Ok', 'Back']).build(2))
    return THIRD


def newVal(update: telegram.Update, _: telegram.ext.CallbackContext) -> None:
    global newValMsg, tempKeyValue
    tempKeyValue = update.message['text']
    newValMsg = update.message


def verify(query: telegram.CallbackQuery) -> int:
    global tempKeyValue
    bot.deleteMessage(chat_id=newValMsg.chat_id, message_id=newValMsg.message_id)
    query.edit_message_text(text=f'Entered Value is:\n\n{tempKeyValue}',
                            reply_markup=InlineKeyboardMaker(['Update Value', 'Back']).build(2))
    return FOURTH


def proceed(query: telegram.CallbackQuery) -> int:
    global envNames, envNamesNew, envValuesNew, tempKeyIndex, tempKeyValue
    envNameNewExists = False
    for i in range(len(envNamesNew)):
        if envNames[int(tempKeyIndex)] == envNamesNew[i]:
            envNameNewExists = True
            envValuesNew[i] = tempKeyValue
    if envNameNewExists is False:
        envNamesNew.append(envNames[int(tempKeyIndex)])
        envValuesNew.append(tempKeyValue)
    buttonList = ['Save Changes', 'Discard Changes', 'Change Another Value']
    replyStr = ''
    for i in range(len(envNamesNew)):
        replyStr += f'{envNamesNew[i]} = "{envValuesNew[i]}"' + '\n'
    query.edit_message_text(text=replyStr, reply_markup=InlineKeyboardMaker(buttonList).build(1))
    return FIFTH


def discardChanges(query: telegram.CallbackQuery) -> int:
    global envNamesNew, envValuesNew
    envNamesNew, envValuesNew = [], []
    logger.info(f"Owner '{query.from_user.first_name}' Discarded Changes Made to '{configEnvFile}' !")
    query.edit_message_text(text=f"Discarded Changes.",
                            reply_markup=InlineKeyboardMaker(['Start Over', 'Exit']).build(2))
    return SIXTH


def saveChanges(query: telegram.CallbackQuery) -> int:
    global envNamesNew, envValuesNew
    query.edit_message_text(text=f"Saving Changes...")
    updateConfigEnvFiles(envNamesNew, envValuesNew)
    logger.info(f"Owner '{query.from_user.first_name}' Saved Changes Made to '{configEnvFile}' !")
    query.edit_message_text(text=f"Saved Changes.\nPlease /{BotCommands.Restart.command} to Load Changes.")
    return telegram.ext.ConversationHandler.END


def end(query: telegram.CallbackQuery) -> int:
    query.edit_message_text(text=f"Exited Config Editor.")
    return telegram.ext.ConversationHandler.END


def stageZero(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    logger.info(f"Owner '{update.message.from_user.first_name}' is Editing '{configEnvFile}'...")
    loadConfigDat()
    return choose(update)


def stageOne(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    return view(query)


def stageTwo(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == '1':
        return edit(query)
    if query.data == '2':
        return choose(query)


def stageThree(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == '1':
        return verify(query)
    if query.data == '2':
        return edit(query)


def stageFour(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == '1':
        return proceed(query)
    if query.data == '2':
        return choose(query)


def stageFive(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == '1':
        return saveChanges(query)
    if query.data == '2':
        return discardChanges(query)
    if query.data == '3':
        return choose(query)


def stageSix(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == '1':
        loadConfigDat()
        return choose(query)
    if query.data == '2':
        return end(query)


FIRST, SECOND, THIRD, FOURTH, FIFTH, SIXTH = range(6)
envNames: list
envValues: list
envNamesNew: list
envValuesNew: list
tempKeyIndex: str
tempKeyValue: str
newValMsg: telegram.Message

handler = telegram.ext.ConversationHandler(
    # TODO: filter - add owner_filter
    entry_points=[telegram.ext.CommandHandler(BotCommands.Config.command, stageZero)],
    states={
        # ZEROTH
        # Choose Environment Variable
        FIRST: [telegram.ext.CallbackQueryHandler(stageOne)],
        # Show Existing Value
        SECOND: [telegram.ext.CallbackQueryHandler(stageTwo)],
        # Capture New Value for Environment Variable
        THIRD: [telegram.ext.CallbackQueryHandler(stageThree),
                telegram.ext.MessageHandler(telegram.ext.Filters.text, newVal)],
        # Verify New Value
        FOURTH: [telegram.ext.CallbackQueryHandler(stageFour)],
        # Show All Changes and Proceed
        FIFTH: [telegram.ext.CallbackQueryHandler(stageFive)],
        # Save or Discard Changes
        SIXTH: [telegram.ext.CallbackQueryHandler(stageSix)]
        # Exit or Start Over
    },
    # TODO: filter - add owner_filter
    fallbacks=[telegram.ext.CommandHandler(BotCommands.Config.command, stageZero)],
    conversation_timeout=120,
    run_async=True
)
