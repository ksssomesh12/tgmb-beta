from . import *
from . import botCmdHandler, subProc


def main():
    subProc.init()
    checkBotApiStart()
    mirrorHelper.ariaHelper.startListener()
    botCmdHandler.addHandlers(dispatcher)
    updater.start_webhook(listen="127.0.0.1", port=8443, url_path=envVarDict['botToken'],
                          webhook_url="http://127.0.0.1:8443/" + envVarDict['botToken'])
    mirrorHelper.mirrorListener.startWebhookServer()
    logger.info("Bot Started !")
    checkRestart()
    updater.idle()
    subProc.term()
    mirrorHelper.mirrorListener.stopWebhookServer()
    logger.info("Bot Stopped !")


main()
