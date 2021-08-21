from . import *
from . import botCmdHandler, subProc


def main():
    subProc.init()
    checkBotApiStart()
    # TODO: add checkAriaDaemonStart()
    mirrorHelper.ariaHelper.startListener()
    mirrorHelper.googleDriveHelper.authorizeApi()
    botCmdHandler.addHandlers(dispatcher)
    updater.start_webhook(listen="127.0.0.1", port=8443, url_path=configVars[reqConfigVars[0]],
                          webhook_url="http://127.0.0.1:8443/" + configVars[reqConfigVars[0]])
    mirrorHelper.mirrorListener.startWebhookServer()
    logger.info("Bot Started !")
    checkRestart()
    updater.idle()
    subProc.term()
    mirrorHelper.mirrorListener.stopWebhookServer()
    logger.info("Bot Stopped !")


main()
