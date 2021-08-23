from . import *
from . import botCmdHandler


if __name__ == '__main__':
    botHelper.botStart(botCmdHandler.handlerInfos)
    botHelper.botIdle()
    botHelper.botStop()
