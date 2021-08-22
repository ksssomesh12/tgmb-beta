from . import *
from . import botCmdHandler, subProc


def main():
    subProc.init()
    botHelper.checkApiStart()
    # TODO: add checkAriaDaemonStart()
    botHelper.mirrorHelper.ariaHelper.startListener()
    botHelper.mirrorHelper.googleDriveHelper.authorizeApi()
    botHelper.addAllHandlers(botCmdHandler.cmdHandlerInfos, botCmdHandler.convHandlers, botCmdHandler.unknownCallBack)
    botHelper.updaterStart()
    botHelper.mirrorHelper.mirrorListener.startWebhookServer()
    logger.info("Bot Started !")
    checkRestart()
    botHelper.updaterIdle()
    subProc.term()
    botHelper.mirrorHelper.mirrorListener.stopWebhookServer()
    logger.info("Bot Stopped !")


main()
