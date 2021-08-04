from . import *
from . import configConv, subProc, mirrorConv


def startCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    bot.sendMessage(text=
                    f'A Telegram Bot Written in Python to Mirror Files on the Internet to Google Drive.\n'
                    f'Use /{BotCommands.Help.command} for More Info.', parse_mode='HTML',
                    chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)


def helpCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    bot.sendMessage(text=
                    f'/{BotCommands.Start.command} {BotCommands.Start.description}\n'
                    f'/{BotCommands.Help.command} {BotCommands.Help.description}\n'
                    f'/{BotCommands.Stats.command} {BotCommands.Stats.description}\n'
                    f'/{BotCommands.Ping.command} {BotCommands.Ping.description}\n'
                    f'/{BotCommands.Restart.command} {BotCommands.Restart.description}\n'
                    f'/{BotCommands.Logs.command} {BotCommands.Logs.description}\n'
                    f'/{BotCommands.Mirror.command} {BotCommands.Mirror.description}\n'
                    f'/{BotCommands.Status.command} {BotCommands.Status.description}\n'
                    f'/{BotCommands.Cancel.command} {BotCommands.Cancel.description}\n'
                    f'/{BotCommands.List.command} {BotCommands.List.description}\n'
                    f'/{BotCommands.Delete.command} {BotCommands.Delete.description}\n'
                    f'/{BotCommands.Authorize.command} {BotCommands.Authorize.description}\n'
                    f'/{BotCommands.Unauthorize.command} {BotCommands.Unauthorize.description}\n'
                    f'/{BotCommands.Sync.command} {BotCommands.Sync.description}\n'
                    f'/{BotCommands.Top.command} {BotCommands.Top.description}\n'
                    f'/{BotCommands.Config.command} {BotCommands.Config.description}\n',
                    parse_mode='HTML', chat_id=update.message.chat_id,
                    reply_to_message_id=update.message.message_id)


# TODO: update stats msg
def statsCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    bot.sendMessage(text=getStatsMsg(), parse_mode='HTML', chat_id=update.message.chat_id,
                    reply_to_message_id=update.message.message_id)


# TODO: CommandHandler for /ping
def pingCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    bot.sendMessage(text='PingCommand Test Message', parse_mode='HTML',
                    chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)


def restartCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    restartMsg: telegram.Message
    logger.info('Restarting the Bot...')
    restartMsg = bot.sendMessage(text='Restarting the Bot...', parse_mode='HTML', chat_id=update.message.chat_id,
                                 reply_to_message_id=update.message.message_id)
    jsonFileWrite(restartJsonFile, {'chatId': f'{restartMsg.chat_id}', 'msgId': f'{restartMsg.message_id}'})
    # TODO: may be not restart all subprocesses on every restart?
    subProc.term()
    time.sleep(5)
    os.execl(sys.executable, sys.executable, '-m', 'tgmb')


def logsCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    bot.sendMediaGroup(media=[telegram.InputMediaDocument(logFiles[0]),
                              telegram.InputMediaDocument(logFiles[1]),
                              telegram.InputMediaDocument(logFiles[2])],
                       chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)
    logger.info("Sent logFiles !")


def statusCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    mirrorHelper.statusHelper.addStatus(update.message.chat.id, update.message.message_id)


def cancelCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    mirrorHelper.cancelMirror(update.message)


# TODO: CommandHandler for /list
def listCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    bot.sendMessage(text='ListCommand Test Message', parse_mode='HTML',
                    chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)


def deleteCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    bot.sendMessage(text=mirrorHelper.googleDriveHelper.deleteByUrl(update.message.text.split(' ')[1].strip()),
                    parse_mode='HTML', chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)


def authorizeCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    authorizeId, authorizeName = getChatUserId(update)
    if str(authorizeId) in envVarDict[list(optConfigVarDict.keys())[0]].keys():
        replyTxt = f"Already Authorized Chat / User: '{authorizeName}' - ({authorizeId}) !"
    else:
        updateAuthorizedChatsDict(authorizeId, authorizeName, auth=True)
        replyTxt = f"Authorized Chat / User: '{authorizeName}' - ({authorizeId}) !"
    logger.info(replyTxt)
    bot.sendMessage(text=replyTxt, parse_mode='HTML', chat_id=update.message.chat_id,
                    reply_to_message_id=update.message.message_id)


def unauthorizeCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    unauthorizeId, unauthorizeName = getChatUserId(update)
    if str(unauthorizeId) in envVarDict[list(optConfigVarDict.keys())[0]].keys():
        updateAuthorizedChatsDict(unauthorizeId, unauthorizeName, unauth=True)
        replyTxt = f"Unauthorized Chat / User: '{unauthorizeName}' - ({unauthorizeId}) !"
    else:
        replyTxt = f"Already Unauthorized Chat / User: '{unauthorizeName}' - ({unauthorizeId}) !"
    logger.info(replyTxt)
    bot.sendMessage(text=replyTxt, parse_mode='HTML', chat_id=update.message.chat_id,
                    reply_to_message_id=update.message.message_id)


def syncCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    syncMsg: telegram.Message
    if envVarDict['dynamicConfig'] == 'true':
        syncMsgTxt = 'Syncing to Google Drive...'
        logger.info(syncMsgTxt)
        syncMsg = bot.sendMessage(text=syncMsgTxt, parse_mode='HTML', chat_id=update.message.chat_id,
                                  reply_to_message_id=update.message.message_id)
        for fileName in configFileList:
            logger.info(mirrorHelper.googleDriveHelper.patchFile(f"{envVarDict['cwd']}/{fileName}"))
        updateFileidJson()
        logger.info('Sync Completed !')
        syncMsg.edit_text(f'Sync Completed !\n{configFileList}\nPlease /{BotCommands.Restart.command} !')
    else:
        syncMsgText = "Not Synced - Using Static Config !"
        logger.info(syncMsgText)
        bot.sendMessage(text=syncMsgText, parse_mode='HTML', chat_id=update.message.chat_id,
                        reply_to_message_id=update.message.message_id)


# TODO: format this properly later on or else remove from release
def topCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    topMsg = ''
    tgmbProcess = psutil.Process(os.getpid())
    ariaDaemonProcess = psutil.Process(subProc.ariaDaemon.pid)
    botApiServerProcess = psutil.Process(subProc.botApiServer.pid)
    topMsg += f'{tgmbProcess.name()}\n{tgmbProcess.cpu_percent()}\n{tgmbProcess.memory_percent()}\n'
    topMsg += f'{ariaDaemonProcess.name()}\n{ariaDaemonProcess.cpu_percent()}\n{ariaDaemonProcess.memory_percent()}\n'
    topMsg += f'{botApiServerProcess.name()}\n{botApiServerProcess.cpu_percent()}\n{botApiServerProcess.memory_percent()}\n'
    bot.sendMessage(text=topMsg, parse_mode='HTML', chat_id=update.message.chat_id,
                    reply_to_message_id=update.message.message_id)


def unknownCallBack(update: telegram.Update, _: telegram.ext.CallbackContext):
    bot.sendMessage(text='Sorry, the command is not registered with a CommandHandler !', parse_mode='HTML',
                    chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)


def addHandlers(dispatcher: telegram.ext.Dispatcher):
    startHandler = telegram.ext.CommandHandler(BotCommands.Start.command, startCallBack, run_async=True)
    dispatcher.add_handler(startHandler)
    helpHandler = telegram.ext.CommandHandler(BotCommands.Help.command, helpCallBack, run_async=True)
    dispatcher.add_handler(helpHandler)
    statsHandler = telegram.ext.CommandHandler(BotCommands.Stats.command, statsCallBack, run_async=True)
    dispatcher.add_handler(statsHandler)
    pingHandler = telegram.ext.CommandHandler(BotCommands.Ping.command, pingCallBack, run_async=True)
    dispatcher.add_handler(pingHandler)
    restartHandler = telegram.ext.CommandHandler(BotCommands.Restart.command, restartCallBack, run_async=True)
    dispatcher.add_handler(restartHandler)
    logsHandler = telegram.ext.CommandHandler(BotCommands.Logs.command, logsCallBack, run_async=True)
    dispatcher.add_handler(logsHandler)
    statusHandler = telegram.ext.CommandHandler(BotCommands.Status.command, statusCallBack, run_async=True)
    dispatcher.add_handler(statusHandler)
    cancelHandler = telegram.ext.CommandHandler(BotCommands.Cancel.command, cancelCallBack, run_async=True)
    dispatcher.add_handler(cancelHandler)
    listHandler = telegram.ext.CommandHandler(BotCommands.List.command, listCallBack, run_async=True)
    dispatcher.add_handler(listHandler)
    deleteHandler = telegram.ext.CommandHandler(BotCommands.Delete.command, deleteCallBack, run_async=True)
    dispatcher.add_handler(deleteHandler)
    authorizeHandler = telegram.ext.CommandHandler(BotCommands.Authorize.command, authorizeCallBack, run_async=True)
    dispatcher.add_handler(authorizeHandler)
    unauthorizeHandler = telegram.ext.CommandHandler(BotCommands.Unauthorize.command, unauthorizeCallBack, run_async=True)
    dispatcher.add_handler(unauthorizeHandler)
    syncHandler = telegram.ext.CommandHandler(BotCommands.Sync.command, syncCallBack, run_async=True)
    dispatcher.add_handler(syncHandler)
    topHandler = telegram.ext.CommandHandler(BotCommands.Top.command, topCallBack, run_async=True)
    dispatcher.add_handler(topHandler)
    dispatcher.add_handler(configConv.handler)
    dispatcher.add_handler(mirrorConv.handler)
    unknownHandler = telegram.ext.MessageHandler(telegram.ext.Filters.command, unknownCallBack, run_async=True)
    dispatcher.add_handler(unknownHandler)
