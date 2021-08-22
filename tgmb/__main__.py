from . import *
from . import botCmdHandler, subProc


def main():
    subProc.init()
    botHelper.checkApiStart()
    # TODO: add checkAriaDaemonStart()
    botHelper.mirrorHelper.ariaHelper.startListener()
    botHelper.mirrorHelper.googleDriveHelper.authorizeApi()
    botCmdHandler.addHandlers()
    botHelper.updaterStart()
    botHelper.mirrorHelper.mirrorListener.startWebhookServer()
    logger.info("Bot Started !")
    checkRestart()
    botHelper.updaterIdle()
    subProc.term()
    botHelper.mirrorHelper.mirrorListener.stopWebhookServer()
    logger.info("Bot Stopped !")


main()
