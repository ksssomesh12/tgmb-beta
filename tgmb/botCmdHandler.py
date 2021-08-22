from . import *
from . import configConv, logConv, mirrorConv, subProc


def startCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    botHelper.bot.sendMessage(text=f'A Telegram Bot Written in Python to Mirror Files on the Internet to Google Drive.\n'
                                   f'Use /{BotCommands.Help.command} for More Info.', parse_mode='HTML',
                              chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)


def helpCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    botHelper.bot.sendMessage(text=f'/{BotCommands.Start.command} {BotCommands.Start.description}\n'
                                   f'/{BotCommands.Help.command} {BotCommands.Help.description}\n'
                                   f'/{BotCommands.Stats.command} {BotCommands.Stats.description}\n'
                                   f'/{BotCommands.Ping.command} {BotCommands.Ping.description}\n'
                                   f'/{BotCommands.Restart.command} {BotCommands.Restart.description}\n'
                                   f'/{BotCommands.Log.command} {BotCommands.Log.description}\n'
                                   f'/{BotCommands.Mirror.command} {BotCommands.Mirror.description}\n'
                                   f'/{BotCommands.Status.command} {BotCommands.Status.description}\n'
                                   f'/{BotCommands.Cancel.command} {BotCommands.Cancel.description}\n'
                                   f'/{BotCommands.List.command} {BotCommands.List.description}\n'
                                   f'/{BotCommands.Delete.command} {BotCommands.Delete.description}\n'
                                   f'/{BotCommands.Authorize.command} {BotCommands.Authorize.description}\n'
                                   f'/{BotCommands.Unauthorize.command} {BotCommands.Unauthorize.description}\n'
                                   f'/{BotCommands.Sync.command} {BotCommands.Sync.description}\n'
                                   f'/{BotCommands.Top.command} {BotCommands.Top.description}\n'
                                   f'/{BotCommands.Config.command} {BotCommands.Config.description}\n', parse_mode='HTML',
                              chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)


# TODO: update stats msg
def statsCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    botHelper.bot.sendMessage(text=getStatsMsg(), parse_mode='HTML', chat_id=update.message.chat_id,
                              reply_to_message_id=update.message.message_id)


# TODO: CommandHandler for /ping
def pingCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    botHelper.bot.sendMessage(text='PingCommand Test Message', parse_mode='HTML',
                              chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)


def restartCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    restartMsg: telegram.Message
    logger.info('Restarting the Bot...')
    restartMsg = botHelper.bot.sendMessage(text='Restarting the Bot...', parse_mode='HTML', chat_id=update.message.chat_id,
                                           reply_to_message_id=update.message.message_id)
    jsonFileWrite(restartJsonFile, {'chatId': f'{restartMsg.chat_id}', 'msgId': f'{restartMsg.message_id}'})
    # TODO: may be not restart all subprocesses on every restart?
    subProc.term()
    time.sleep(5)
    os.execl(sys.executable, sys.executable, '-m', 'tgmb')


def statusCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    threadInit(target=botHelper.mirrorHelper.statusHelper.addStatus, name='statusCallBack-addStatus',
               chatId=update.message.chat.id, msgId=update.message.message_id)


def cancelCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    botHelper.mirrorHelper.cancelMirror(update.message)


# TODO: CommandHandler for /list
def listCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    botHelper.bot.sendMessage(text='ListCommand Test Message', parse_mode='HTML',
                              chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)


def deleteCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    botHelper.bot.sendMessage(text=botHelper.mirrorHelper.googleDriveHelper.deleteByUrl(update.message.text.split(' ')[1].strip()),
                              parse_mode='HTML', chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)


def authorizeCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    chatId, chatName, chatType = getChatDetails(update)
    if str(chatId) in configVars[optConfigVars[0]].keys():
        replyTxt = f"Already Authorized Chat: '{chatName}' - ({chatId}) ({chatType}) !"
    else:
        updateAuthorizedChats(chatId, chatName, chatType, auth=True)
        replyTxt = f"Authorized Chat: '{chatName}' - ({chatId}) ({chatType}) !"
    logger.info(replyTxt)
    botHelper.bot.sendMessage(text=replyTxt, parse_mode='HTML', chat_id=update.message.chat_id,
                              reply_to_message_id=update.message.message_id)


def unauthorizeCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    chatId, chatName, chatType = getChatDetails(update)
    if str(chatId) in configVars[optConfigVars[0]].keys():
        updateAuthorizedChats(chatId, chatName, chatType, unauth=True)
        replyTxt = f"Unauthorized Chat: '{chatName}' - ({chatId}) ({chatType}) !"
    else:
        replyTxt = f"Already Unauthorized Chat: '{chatName}' - ({chatId}) ({chatType}) !"
    logger.info(replyTxt)
    botHelper.bot.sendMessage(text=replyTxt, parse_mode='HTML', chat_id=update.message.chat_id,
                              reply_to_message_id=update.message.message_id)


def syncCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    syncMsg: telegram.Message
    if envVars['dynamicConfig']:
        syncMsgTxt = 'Syncing to Google Drive...'
        logger.info(syncMsgTxt)
        syncMsg = botHelper.bot.sendMessage(text=syncMsgTxt, parse_mode='HTML', chat_id=update.message.chat_id,
                                            reply_to_message_id=update.message.message_id)
        for fileName in configFiles:
            logger.info(botHelper.mirrorHelper.googleDriveHelper.patchFile(f"{envVars['currWorkDir']}/{fileName}"))
        updateFileidJson()
        logger.info('Sync Completed !')
        syncMsg.edit_text(f'Sync Completed !\n{configFiles}\nPlease /{BotCommands.Restart.command} !')
    else:
        syncMsgText = "Not Synced - Using Static Config !"
        logger.info(syncMsgText)
        botHelper.bot.sendMessage(text=syncMsgText, parse_mode='HTML', chat_id=update.message.chat_id,
                                  reply_to_message_id=update.message.message_id)


# TODO: format this properly later on or else remove from release
def topCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    topMsg = ''
    tgmbProc = psutil.Process(os.getpid())
    ariaDaemonProc = psutil.Process(subProc.ariaDaemon.pid)
    botApiServerProc = psutil.Process(subProc.botApiServer.pid)
    topMsg += f'{tgmbProc.name()}\n{tgmbProc.cpu_percent()}\n{tgmbProc.memory_percent()}\n'
    topMsg += f'{ariaDaemonProc.name()}\n{ariaDaemonProc.cpu_percent()}\n{ariaDaemonProc.memory_percent()}\n'
    topMsg += f'{botApiServerProc.name()}\n{botApiServerProc.cpu_percent()}\n{botApiServerProc.memory_percent()}\n'
    botHelper.bot.sendMessage(text=topMsg, parse_mode='HTML', chat_id=update.message.chat_id,
                              reply_to_message_id=update.message.message_id)


def unknownCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    if not '@' in update.message.text.split(' ')[0]:
        botHelper.bot.sendMessage(text='Sorry, the command is not registered with a CommandHandler !', parse_mode='HTML',
                                  chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)


def addHandlers():
    startHandler = telegram.ext.CommandHandler(BotCommands.Start.command, startCallBack, run_async=True)
    botHelper.dispatcher.add_handler(startHandler)
    helpHandler = telegram.ext.CommandHandler(BotCommands.Help.command, helpCallBack, run_async=True)
    botHelper.dispatcher.add_handler(helpHandler)
    statsHandler = telegram.ext.CommandHandler(BotCommands.Stats.command, statsCallBack, run_async=True)
    botHelper.dispatcher.add_handler(statsHandler)
    pingHandler = telegram.ext.CommandHandler(BotCommands.Ping.command, pingCallBack, run_async=True)
    botHelper.dispatcher.add_handler(pingHandler)
    restartHandler = telegram.ext.CommandHandler(BotCommands.Restart.command, restartCallBack, run_async=True)
    botHelper.dispatcher.add_handler(restartHandler)
    statusHandler = telegram.ext.CommandHandler(BotCommands.Status.command, statusCallBack, run_async=True)
    botHelper.dispatcher.add_handler(statusHandler)
    cancelHandler = telegram.ext.CommandHandler(BotCommands.Cancel.command, cancelCallBack, run_async=True)
    botHelper.dispatcher.add_handler(cancelHandler)
    listHandler = telegram.ext.CommandHandler(BotCommands.List.command, listCallBack, run_async=True)
    botHelper.dispatcher.add_handler(listHandler)
    deleteHandler = telegram.ext.CommandHandler(BotCommands.Delete.command, deleteCallBack, run_async=True)
    botHelper.dispatcher.add_handler(deleteHandler)
    authorizeHandler = telegram.ext.CommandHandler(BotCommands.Authorize.command, authorizeCallBack, run_async=True)
    botHelper.dispatcher.add_handler(authorizeHandler)
    unauthorizeHandler = telegram.ext.CommandHandler(BotCommands.Unauthorize.command, unauthorizeCallBack, run_async=True)
    botHelper.dispatcher.add_handler(unauthorizeHandler)
    syncHandler = telegram.ext.CommandHandler(BotCommands.Sync.command, syncCallBack, run_async=True)
    botHelper.dispatcher.add_handler(syncHandler)
    topHandler = telegram.ext.CommandHandler(BotCommands.Top.command, topCallBack, run_async=True)
    botHelper.dispatcher.add_handler(topHandler)
    botHelper.dispatcher.add_handler(configConv.handler)
    botHelper.dispatcher.add_handler(logConv.handler)
    botHelper.dispatcher.add_handler(mirrorConv.handler)
    unknownHandler = telegram.ext.MessageHandler(telegram.ext.Filters.command, unknownCallBack, run_async=True)
    botHelper.dispatcher.add_handler(unknownHandler)
