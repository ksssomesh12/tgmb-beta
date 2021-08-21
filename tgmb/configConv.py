from . import *


def loadConfigDict():
    global configVarsEditable, configVarsNew
    configVarsEditable = {}
    configVarsNew = {}
    configVarsEditable = jsonFileLoad(configJsonFile)
    for key in [reqConfigVars[4], reqConfigVars[5], list(optConfigVars.keys())[0]]:
        if key in list(configVarsEditable.keys()):
            configVarsEditable.pop(key)


def chooseKey(update: telegram.Update = None, query: telegram.CallbackQuery = None) -> int:
    global configVarsEditable, tempKey, tempVal
    tempKey, tempVal = '', ''
    if query is None:
        update.message.reply_text(text="Select an Environment Variable:",
                                  reply_markup=InlineKeyboardMaker(list(configVarsEditable.keys()) + ['Exit']).build(1))
    if update is None:
        query.edit_message_text(text="Select an Environment Variable:",
                                reply_markup=InlineKeyboardMaker(list(configVarsEditable.keys()) + ['Exit']).build(1))
    return FIRST


def viewVal(query: telegram.CallbackQuery) -> int:
    global configVarsEditable, tempKey
    tempKeyIndex = int(query.data) - 1
    if tempKeyIndex != len(list(configVarsEditable.keys())):
        tempKey = list(configVarsEditable.keys())[tempKeyIndex]
        query.edit_message_text(text=f'"{tempKey}" = "{configVarsEditable[tempKey]}"',
                                reply_markup=InlineKeyboardMaker(['Edit', 'Back']).build(2))
        return SECOND
    else:
        return convEnd(query)


def editVal(query: telegram.CallbackQuery) -> int:
    global tempKey
    query.edit_message_text(text=f'Send New Value for "{tempKey}":',
                            reply_markup=InlineKeyboardMaker(['Ok', 'Back']).build(2))
    return THIRD


def newVal(update: telegram.Update, _: telegram.ext.CallbackContext) -> None:
    global newValMsg, tempVal
    newValMsg = update.message
    tempVal = newValMsg['text']


def verifyNewVal(query: telegram.CallbackQuery) -> int:
    global tempVal
    bot.deleteMessage(chat_id=newValMsg.chat_id, message_id=newValMsg.message_id)
    query.edit_message_text(text=f'Entered Value is:\n\n"{tempVal}"',
                            reply_markup=InlineKeyboardMaker(['Update Value', 'Back']).build(2))
    return FOURTH


def proceedNewVal(query: telegram.CallbackQuery) -> int:
    global configVarsNew, tempKey, tempVal
    configVarsNew[tempKey] = tempVal
    buttonList = ['Save Changes', 'Discard Changes', 'Change Another Value']
    replyStr = ''
    for i in range(len(list(configVarsNew.keys()))):
        replyStr += f'{list(configVarsNew.keys())[i]} = "{list(configVarsNew.values())[i]}"' + '\n'
    query.edit_message_text(text=replyStr, reply_markup=InlineKeyboardMaker(buttonList).build(1))
    return FIFTH


def discardChanges(query: telegram.CallbackQuery) -> int:
    global configVarsNew
    configVarsNew = {}
    logger.info(f"Owner '{query.from_user.first_name}' Discarded Changes Made to '{configJsonFile}' !")
    query.edit_message_text(text=f"Discarded Changes.",
                            reply_markup=InlineKeyboardMaker(['Start Over', 'Exit']).build(2))
    return SIXTH


def saveChanges(query: telegram.CallbackQuery) -> int:
    global configVarsNew
    query.edit_message_text(text=f"Saving Changes...")
    updateConfigJson(configVarsNew)
    logger.info(f"Owner '{query.from_user.first_name}' Saved Changes Made to '{configJsonFile}' !")
    query.edit_message_text(text=f"Saved Changes.\nPlease /{BotCommands.Restart.command} to Load Changes.")
    return telegram.ext.ConversationHandler.END


def convEnd(query: telegram.CallbackQuery) -> int:
    query.edit_message_text(text=f"Exited Config Editor.")
    return telegram.ext.ConversationHandler.END


def stageZero(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    logger.info(f"Owner '{update.message.from_user.first_name}' is Editing '{configJsonFile}'...")
    loadConfigDict()
    return chooseKey(update)


def stageOne(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    return viewVal(query)


def stageTwo(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == '1':
        return editVal(query)
    if query.data == '2':
        return chooseKey(query)


def stageThree(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == '1':
        return verifyNewVal(query)
    if query.data == '2':
        return editVal(query)


def stageFour(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == '1':
        return proceedNewVal(query)
    if query.data == '2':
        return chooseKey(query)


def stageFive(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == '1':
        return saveChanges(query)
    if query.data == '2':
        return discardChanges(query)
    if query.data == '3':
        return chooseKey(query)


def stageSix(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == '1':
        loadConfigDict()
        return chooseKey(query)
    if query.data == '2':
        return convEnd(query)


FIRST, SECOND, THIRD, FOURTH, FIFTH, SIXTH = range(6)
configVarsEditable: typing.Dict[str, typing.Union[str, typing.Dict[str, typing.Union[str, typing.Dict[str, typing.Union[str, typing.Dict[str, typing.Union[str, typing.List[str]]]]]]]]]
configVarsNew: typing.Dict[str, str]
tempKey: str
tempVal: str
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
