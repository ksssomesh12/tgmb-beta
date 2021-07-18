from . import *
from . import configEditor, subProc, mirrorConv


def start(update: telegram.Update, _: telegram.ext.CallbackContext):
    bot.sendMessage(text=
                    f'A Telegram Bot Written in Python to Mirror Files on the Internet to Google Drive.\n'
                    f'Use /{BotCommands.Help.command} for More Info.', parse_mode='HTML',
                    chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)


def help(update: telegram.Update, _: telegram.ext.CallbackContext):
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
def stats(update: telegram.Update, _: telegram.ext.CallbackContext):
    bot.sendMessage(text=getStatsMsg(), parse_mode='HTML', chat_id=update.message.chat_id,
                    reply_to_message_id=update.message.message_id)


# TODO: CommandHandler for /ping
def ping(update: telegram.Update, _: telegram.ext.CallbackContext):
    bot.sendMessage(text='PingCommand Test Message', parse_mode='HTML',
                    chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)


def restart(update: telegram.Update, _: telegram.ext.CallbackContext):
    restartMsg: telegram.Message
    logger.info('Restarting the Bot...')
    restartMsg = bot.sendMessage(text='Restarting the Bot...', parse_mode='HTML', chat_id=update.message.chat_id,
                                 reply_to_message_id=update.message.message_id)
    open(restartDumpFile, 'wt').write(f'{restartMsg.message_id} {restartMsg.chat_id}\n')
    # TODO: may be not restart all subprocesses on every restart?
    subProc.term()
    time.sleep(5)
    os.execl(sys.executable, sys.executable, '-m', 'tgmb')


def logs(update: telegram.Update, _: telegram.ext.CallbackContext):
    bot.sendMediaGroup(media=[telegram.InputMediaDocument(logFiles[0]),
                              telegram.InputMediaDocument(logFiles[1]),
                              telegram.InputMediaDocument(logFiles[2])],
                       chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)
    logger.info("Sent logFiles !")


def status(update: telegram.Update, _: telegram.ext.CallbackContext):
    mirrorHelper.statusHelper.addStatus(update.message.chat.id, update.message.message_id)


def cancel(update: telegram.Update, _: telegram.ext.CallbackContext):
    mirrorHelper.cancelMirror(update.message)


# TODO: CommandHandler for /list
def list(update: telegram.Update, _: telegram.ext.CallbackContext):
    bot.sendMessage(text='ListCommand Test Message', parse_mode='HTML',
                    chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)


def delete(update: telegram.Update, _: telegram.ext.CallbackContext):
    bot.sendMessage(text=mirrorHelper.googleDriveHelper.deleteByUrl(update.message.text.split(' ')[1].strip()),
                    parse_mode='HTML', chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)


def authorize(update: telegram.Update, _: telegram.ext.CallbackContext):
    authorizeId, authorizeName = getChatUserId(update)
    if authorizeId in authorizedChatsList:
        replyTxt = f"Already Authorized Chat / User: '{authorizeName}' - ({authorizeId}) !"
    else:
        updateAuthorizedChats(authorizeId, auth=True)
        replyTxt = f"Authorized Chat / User: '{authorizeName}' - ({authorizeId}) !"
    logger.info(replyTxt)
    bot.sendMessage(text=replyTxt, parse_mode='HTML', chat_id=update.message.chat_id,
                    reply_to_message_id=update.message.message_id)


def unauthorize(update: telegram.Update, _: telegram.ext.CallbackContext):
    unauthorizeId, unauthorizeName = getChatUserId(update)
    if unauthorizeId in authorizedChatsList:
        updateAuthorizedChats(unauthorizeId, unauth=True)
        replyTxt = f"Unauthorized Chat / User: '{unauthorizeName}' - ({unauthorizeId}) !"
    else:
        replyTxt = f"Already Unauthorized Chat / User: '{unauthorizeName}' - ({unauthorizeId}) !"
    logger.info(replyTxt)
    bot.sendMessage(text=replyTxt, parse_mode='HTML', chat_id=update.message.chat_id,
                    reply_to_message_id=update.message.message_id)


def sync(update: telegram.Update, _: telegram.ext.CallbackContext):
    syncMsg: telegram.Message
    if envVarDict['dynamicConfig'] == 'true':
        syncMsgTxt = 'Syncing to Google Drive...'
        logger.info(syncMsgTxt)
        syncMsg = bot.sendMessage(text=syncMsgTxt, parse_mode='HTML', chat_id=update.message.chat_id,
                                  reply_to_message_id=update.message.message_id)
        for fileName in configFileList:
            logger.info(mirrorHelper.googleDriveHelper.patchFile(f"{envVarDict['CWD']}/{fileName}"))
        updateFileidEnv()
        logger.info('Sync Completed !')
        syncMsg.edit_text(f'Sync Completed !\n{configFileList}\nPlease /{BotCommands.Restart.command} !')
    else:
        syncMsgText = "Not Synced - Using Static Config !"
        logger.info(syncMsgText)
        bot.sendMessage(text=syncMsgText, parse_mode='HTML', chat_id=update.message.chat_id,
                        reply_to_message_id=update.message.message_id)


# TODO: format this properly later on or else remove from release
def top(update: telegram.Update, _: telegram.ext.CallbackContext):
    topMsg = ''
    tgmbProcess = psutil.Process(os.getpid())
    ariaDaemonProcess = psutil.Process(subProc.ariaDaemon.pid)
    botApiServerProcess = psutil.Process(subProc.botApiServer.pid)
    topMsg += f'{tgmbProcess.name()}\n{tgmbProcess.cpu_percent()}\n{tgmbProcess.memory_percent()}\n'
    topMsg += f'{ariaDaemonProcess.name()}\n{ariaDaemonProcess.cpu_percent()}\n{ariaDaemonProcess.memory_percent()}\n'
    topMsg += f'{botApiServerProcess.name()}\n{botApiServerProcess.cpu_percent()}\n{botApiServerProcess.memory_percent()}\n'
    bot.sendMessage(text=topMsg, parse_mode='HTML', chat_id=update.message.chat_id,
                    reply_to_message_id=update.message.message_id)


def unknown(update: telegram.Update, _: telegram.ext.CallbackContext):
    bot.sendMessage(text='Sorry, the command is not registered with a CommandHandler !', parse_mode='HTML',
                    chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)


def addHandlers(dispatcher: telegram.ext.Dispatcher):
    startHandler = telegram.ext.CommandHandler(BotCommands.Start.command, start, run_async=True)
    dispatcher.add_handler(startHandler)
    helpHandler = telegram.ext.CommandHandler(BotCommands.Help.command, help, run_async=True)
    dispatcher.add_handler(helpHandler)
    statsHandler = telegram.ext.CommandHandler(BotCommands.Stats.command, stats, run_async=True)
    dispatcher.add_handler(statsHandler)
    pingHandler = telegram.ext.CommandHandler(BotCommands.Ping.command, ping, run_async=True)
    dispatcher.add_handler(pingHandler)
    restartHandler = telegram.ext.CommandHandler(BotCommands.Restart.command, restart, run_async=True)
    dispatcher.add_handler(restartHandler)
    logsHandler = telegram.ext.CommandHandler(BotCommands.Logs.command, logs, run_async=True)
    dispatcher.add_handler(logsHandler)
    statusHandler = telegram.ext.CommandHandler(BotCommands.Status.command, status, run_async=True)
    dispatcher.add_handler(statusHandler)
    cancelHandler = telegram.ext.CommandHandler(BotCommands.Cancel.command, cancel, run_async=True)
    dispatcher.add_handler(cancelHandler)
    listHandler = telegram.ext.CommandHandler(BotCommands.List.command, list, run_async=True)
    dispatcher.add_handler(listHandler)
    deleteHandler = telegram.ext.CommandHandler(BotCommands.Delete.command, delete, run_async=True)
    dispatcher.add_handler(deleteHandler)
    authorizeHandler = telegram.ext.CommandHandler(BotCommands.Authorize.command, authorize, run_async=True)
    dispatcher.add_handler(authorizeHandler)
    unauthorizeHandler = telegram.ext.CommandHandler(BotCommands.Unauthorize.command, unauthorize, run_async=True)
    dispatcher.add_handler(unauthorizeHandler)
    syncHandler = telegram.ext.CommandHandler(BotCommands.Sync.command, sync, run_async=True)
    dispatcher.add_handler(syncHandler)
    topHandler = telegram.ext.CommandHandler(BotCommands.Top.command, top, run_async=True)
    dispatcher.add_handler(topHandler)
    dispatcher.add_handler(configEditor.handler)
    dispatcher.add_handler(mirrorConv.handler)
    unknownHandler = telegram.ext.MessageHandler(telegram.ext.Filters.command, unknown, run_async=True)
    dispatcher.add_handler(unknownHandler)
