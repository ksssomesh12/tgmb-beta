# TODO: add sufficient documentation to the functions and classes in this module
# TODO: Code for Download from Mega
# TODO: Code for Upload to Mega
# TODO: Helper functions - bot_utils.py, fs_utils.py, message_utils.py
# TODO: Code for user filters
# TODO: Add and Handle Exceptions
# TODO: Code for direct link generation
import aria2p
import asyncio
import copy
import googleapiclient.discovery
import googleapiclient.errors
import googleapiclient.http
import google.auth.transport.requests
import google.oauth2.credentials
import google.oauth2.service_account
import hashlib
import json
import logging
import loguru
import magic
import mega
import os
import psutil
import random
import re
import requests
import shutil
import signal
import string
import subprocess
import sys
import time
import telegram
import telegram.ext
import threading
import tornado.httputil
import tornado.httpserver
import tornado.ioloop
import tornado.web
import typing
import warnings
import youtube_dl


class BotWrapper:
    def __init__(self):
        self.botHelper = BotHelper()
        self.botHelper.initHelper()

    def Start(self):
        self.botHelper.botStart()

    def Idle(self):
        self.botHelper.botIdle()

    def Stop(self):
        self.botHelper.botStop()


class BaseHelper:
    def __init__(self, botHelper: 'BotHelper'):
        self.botHelper = botHelper

    def initHelper(self) -> None:
        self.initLogger()

    def initLogger(self) -> None:
        self.logger = self.botHelper.loggingHelper.logger.bind(classname=self.__class__.__name__)


class BotHelper(BaseHelper):
    def __init__(self):
        self.configHelper = ConfigHelper(self)
        self.getHelper = GetHelper(self)
        self.loggingHelper = LoggingHelper(self)
        self.mirrorHelper = MirrorHelper(self)
        self.threadingHelper = ThreadingHelper(self)
        self.botCmdHelper = BotCommandHelper(self)
        self.botConvHelper = BotConversationHelper(self)
        self.ariaHelper = AriaHelper(self)
        self.googleDriveHelper = GoogleDriveHelper(self)
        self.megaHelper = MegaHelper(self)
        self.telegramHelper = TelegramHelper(self)
        self.youTubeHelper = YouTubeHelper(self)
        self.compressionHelper = CompressionHelper(self)
        self.decompressionHelper = DecompressionHelper(self)
        self.statusHelper = StatusHelper(self)
        self.mirrorListenerHelper = MirrorListenerHelper(self)
        super().__init__(self)

    def initHelper(self) -> None:
        self.envVars: typing.Dict[str, typing.Union[bool, str]] = {'currWorkDir': os.getcwd()}
        self.logDebugFile = 'log.debug'
        self.isChangeLogLevel: bool = False
        self.restartJsonFile = 'restart.json'
        self.restartMsgInfo: typing.Dict[str, int] = {}
        self.restartVars = (self.configHelper.jsonFileLoad(self.restartJsonFile) if os.path.exists(self.restartJsonFile) else {})
        self.initSubHelpers()
        super().initHelper()
        self.listenAddress: str = 'localhost'
        self.listenPort: int = 8443
        self.startTime: float = time.time()
        self.apiServerPid: int = 0
        self.apiServerStartCmd: typing.List[str] = \
            ['telegram-bot-api', '--local', '--verbosity=9',
             f'--api-id={self.configHelper.configVars[self.configHelper.reqVars[2]]}',
             f'--api-hash={self.configHelper.configVars[self.configHelper.reqVars[3]]}',
             f'--log={os.path.join(self.envVars["currWorkDir"], self.loggingHelper.logFiles[1])}']
        self.updater = telegram.ext.Updater(token=self.configHelper.configVars[self.configHelper.reqVars[0]],
                                            base_url=f'http://{self.listenAddress}:8081/bot')
        self.dispatcher = self.updater.dispatcher
        self.bot = self.updater.bot
        self.envVars['dlRootDirPath'] = os.path.join(self.envVars['currWorkDir'], self.configHelper.configVars[self.configHelper.optVars[2]])
        self.checkLogLevel()

    def initSubHelpers(self):
        self.loggingHelper.initHelper()
        self.getHelper.initHelper()
        self.threadingHelper.initHelper()
        self.configHelper.initHelper()
        self.mirrorHelper.initHelper()
        self.botCmdHelper.initHelper()
        self.botConvHelper.initHelper()
        self.ariaHelper.initHelper()
        self.googleDriveHelper.initHelper()
        self.megaHelper.initHelper()
        self.telegramHelper.initHelper()
        self.youTubeHelper.initHelper()
        self.compressionHelper.initHelper()
        self.decompressionHelper.initHelper()
        self.statusHelper.initHelper()
        self.mirrorListenerHelper.initHelper()

    def apiServerStart(self) -> None:
        if self.restartVars and self.restartVars['botApiServerPid']:
            self.apiServerPid = self.restartVars['botApiServerPid']
            self.logger.info(f'botApiServer Already Running (pid {self.apiServerPid}) !')
        if not self.apiServerPid:
            self.apiServerPid = subprocess.Popen(self.apiServerStartCmd).pid
            self.logger.info(f'botApiServer Started (pid {self.apiServerPid}) !')

    def apiServerCheck(self) -> None:
        conSuccess = False
        while not conSuccess:
            try:
                self.bot.getMe()
                conSuccess = True
            except telegram.error.NetworkError:
                time.sleep(0.1)
                continue

    def apiServerStop(self) -> None:
        os.kill(self.apiServerPid, signal.SIGTERM)
        self.logger.info(f"botApiServer terminated (pid {self.apiServerPid})")

    def checkLogLevel(self):
        if self.configHelper.configVars[self.configHelper.optVars[3]] == self.configHelper.optVals[3]:
            if os.path.exists(self.logDebugFile):
                self.isChangeLogLevel = True
                os.remove(self.logDebugFile)
        else:
            if not os.path.exists(self.logDebugFile):
                self.isChangeLogLevel = True
                open(self.logDebugFile, 'wt').write('')

    def ifChangeLogLevel(self):
        if self.isChangeLogLevel:
            self.logger.info('Changing logLevel...')
            self.botRestart()

    def addAllHandlers(self) -> None:
        for cmdHandler in self.botCmdHelper.cmdHandlers:
            self.dispatcher.add_handler(cmdHandler)
        for convHandler in self.botConvHelper.convHandlers:
            self.dispatcher.add_handler(convHandler)
        unknownHandler = telegram.ext.MessageHandler(filters=telegram.ext.Filters.command,
                                                     callback=self.botCmdHelper.unknownCallBack, run_async=True)
        self.dispatcher.add_handler(unknownHandler)

    def botRestart(self) -> None:
        self.ariaHelper.api.remove_all(force=True)
        self.cleanDlRootDir()
        self.logger.info('Restarting the Bot...')
        restartJsonDict = {'restartMsgInfo': self.restartMsgInfo, 'ariaRpcSecret': self.ariaHelper.rpcSecret,
                           'ariaDaemonPid': self.ariaHelper.daemonPid, 'botApiServerPid': self.apiServerPid}
        self.configHelper.jsonFileWrite(self.restartJsonFile, restartJsonDict)
        os.execl(sys.executable, sys.executable, '-m', 'tgmb')

    def botStart(self) -> None:
        self.cleanDlRootDir()
        self.delLogFiles()
        self.ariaHelper.daemonStart()
        self.apiServerStart()
        self.ariaHelper.daemonCheck()
        self.apiServerCheck()
        self.ariaHelper.dlTrackersList()
        self.ariaHelper.globalOptsGet()
        self.ariaHelper.globalOptsSet()
        self.ariaHelper.startListener()
        self.megaHelper.addListener()
        self.googleDriveHelper.authorizeApi()
        self.megaHelper.authorizeApi()
        self.addAllHandlers()
        self.updaterStart()
        self.mirrorListenerHelper.startWebhookServer()
        self.logger.info("Bot Started !")

    def botIdle(self) -> None:
        self.ifUpdateRestartMsg()
        self.configHelper.ifFixConfigJson()
        self.ifChangeLogLevel()
        self.updaterIdle()

    def botStop(self) -> None:
        self.megaHelper.unauthorizeApi()
        self.apiServerStop()
        self.ariaHelper.daemonStop()
        self.delLogFiles()
        self.mirrorListenerHelper.stopWebhookServer()
        self.logger.info("Bot Stopped !")

    def ifUpdateRestartMsg(self) -> None:
        if self.restartVars and self.restartVars['restartMsgInfo']:
            self.bot.editMessageText(text='Bot Restarted !', parse_mode='HTML',
                                     chat_id=self.restartVars['restartMsgInfo']['chatId'],
                                     message_id=self.restartVars['restartMsgInfo']['msgId'])
            os.remove(self.restartJsonFile)

    def cleanDlRootDir(self) -> None:
        if os.path.exists(self.envVars['dlRootDirPath']):
            shutil.rmtree(self.envVars['dlRootDirPath'])
        os.mkdir(self.envVars['dlRootDirPath'])

    # TODO: delLogFiles on botStop(), with restartVars != {}
    def delLogFiles(self) -> None:
        if not self.restartVars:
            for logFile in self.loggingHelper.logFiles[1:]:
                if os.path.exists(logFile):
                    os.remove(logFile)
                    self.logger.debug(f"Deleted: '{logFile}'")

    def updaterStart(self):
        self.updater.start_webhook(listen=self.listenAddress, port=self.listenPort, url_path=self.configHelper.configVars[self.configHelper.reqVars[0]],
                                   webhook_url=f'http://{self.listenAddress}:{self.listenPort}/{self.configHelper.configVars[self.configHelper.reqVars[0]]}')

    def updaterIdle(self):
        self.updater.idle()


class ConfigHelper(BaseHelper):
    def __init__(self, botHelper: BotHelper):
        super().__init__(botHelper)

    def initHelper(self) -> None:
        super().initHelper()
        self.configJsonFile = 'config.json'
        self.configJsonBakFile = self.configJsonFile + '.bak'
        self.dynamicJsonFile = 'dynamic.json'
        self.fileidJsonFile = 'fileid.json'
        self.configFiles: [str] = [self.configJsonFile, self.configJsonBakFile]
        self.configVars: typing.Dict = {}
        self.reqVars: [str] = ['botToken', 'botOwnerId', 'telegramApiId', 'telegramApiHash',
                               'googleDriveAuth', 'googleDriveUploadFolderIds']
        self.optVars: typing.List[str] = ['ariaGlobalOpts', 'authorizedChats', 'dlRootDir', 'logLevel',
                                          'megaAuth', 'statusUpdateInterval', 'trackersListUrl']
        self.optVals: typing.List[typing.Union[str, typing.Dict]] = \
            [{'allow-overwrite': 'true', 'bt-max-peers': '0', 'follow-torrent': 'mem',
              'max-connection-per-server': '8', 'max-overall-upload-limit': '1K',
              'min-split-size': '10M', 'seed-time': '0.01', 'split': '10'},
             {}, 'dl', 'INFO', {}, '5', 'https://trackerslist.com/all_aria2.txt']
        self.emptyVals: typing.List[typing.Union[str, typing.Dict]] = ['', ' ', {}]
        self.isFixConfigJson: bool = False
        self.configVarsLoad()
        self.configVarsCheck()

    def configFileDl(self, configFile: str) -> None:
        self.logger.debug(f"Starting Download: '{configFile}'...")
        configFileId = self.botHelper.envVars[self.botHelper.getHelper.fileIdKey(configFile)]
        configFileUrl = f'https://docs.google.com/uc?export=download&id={configFileId}'
        if os.path.exists(configFile):
            os.remove(configFile)
        subprocess.run(['aria2c', configFileUrl, '--quiet=true', '--out=' + configFile])
        # intentional thread switching
        time.sleep(0.1)
        timeElapsed = 0.1
        while timeElapsed <= float(self.botHelper.envVars['dlWaitTime']):
            if os.path.exists(configFile):
                self.logger.debug(f"Downloaded '{configFile}' !")
                break
            else:
                time.sleep(0.1)
                timeElapsed += 0.1

    def configFileCheck(self, configFile: str):
        if not os.path.exists(configFile):
            self.logger.error(f"Missing configFile: '{configFile}' ! Exiting...")
            exit(1)

    def configFileSync(self, configFiles: typing.List[str]) -> None:
        for configFile in configFiles:
            self.logger.info(self.botHelper.googleDriveHelper.patchFile(os.path.join(self.botHelper.envVars['currWorkDir'], configFile),
                                                                        self.botHelper.envVars[self.botHelper.getHelper.fileIdKey(configFile)]))

    def configVarsCheck(self) -> None:
        self.reqVarsCheck()
        self.optVarsCheck()
        self.unknownVarsCheck()

    def configVarsLoad(self) -> None:
        if os.path.exists(self.dynamicJsonFile):
            self.botHelper.envVars['dynamicConfig'] = True
            self.logger.info('Using Dynamic Config...')
            self.botHelper.envVars = {**self.botHelper.envVars, **self.jsonFileLoad(self.dynamicJsonFile)}
            self.configFileDl(self.fileidJsonFile)
            self.configFileCheck(self.fileidJsonFile)
            self.botHelper.envVars = {**self.botHelper.envVars, **self.jsonFileLoad(self.fileidJsonFile)}
            for configFile in self.configFiles:
                fileHashInDict = self.botHelper.envVars[self.botHelper.getHelper.fileHashKey(configFile)]
                if not (os.path.exists(configFile) and fileHashInDict == self.botHelper.getHelper.fileHash(configFile)):
                    self.botHelper.threadingHelper.initThread(target=self.configFileDl, name=f'{configFile}-configFileDl', configFile=configFile)
            while self.botHelper.threadingHelper.runningThreads:
                time.sleep(0.1)
        else:
            self.botHelper.envVars['dynamicConfig'] = False
            self.logger.info('Using Static Config...')
            self.botHelper.envVars['dlWaitTime'] = '5'
        for configFile in self.configFiles:
            self.configFileCheck(configFile)
        self.configVars = self.jsonFileLoad(self.configJsonFile)

    def reqVarsCheck(self):
        for reqVar in self.reqVars:
            try:
                if self.configVars[reqVar] in self.emptyVals:
                    raise KeyError
            except KeyError:
                self.isFixConfigJson = True
                self.logger.error(f"Required Environment Variable Missing: '{reqVar}' ! Exiting...")
                exit(1)

    def optVarsCheck(self):
        for optVar in self.optVars:
            try:
                if self.configVars[optVar] in self.emptyVals:
                    raise KeyError
            except KeyError:
                self.isFixConfigJson = True
                self.configVars[optVar] = self.optVals[self.optVars.index(optVar)]

    def unknownVarsCheck(self):
        for configVar in list(self.configVars.keys()):
            if configVar not in self.reqVars + self.optVars:
                self.isFixConfigJson = True
                self.configVars.pop(configVar)

    def ifFixConfigJson(self):
        if self.isFixConfigJson:
            self.logger.info(f"Fixing '{self.configJsonFile}' (Not Found optConfigVars / Found unknownConfigVars) ...")
            self.updateConfigJson()

    @staticmethod
    def jsonFileLoad(jsonFileName: str) -> typing.Dict:
        return json.loads(open(jsonFileName, 'rt', encoding='utf-8').read())

    @staticmethod
    def jsonFileWrite(jsonFileName: str, jsonDict: dict) -> None:
        open(jsonFileName, 'wt', encoding='utf-8').write(json.dumps(jsonDict, indent=2) + '\n')

    def updateAuthorizedChats(self, chatId: int, chatName: str, chatType: str, auth: bool = None, unauth: bool = None) -> None:
        if auth:
            self.configVars[self.optVars[1]][str(chatId)] = {"chatType": chatType, "chatName": chatName}
        if unauth:
            self.configVars[self.optVars[1]].pop(str(chatId))
        self.updateConfigJson()

    def updateConfigJson(self) -> None:
        self.logger.info(f"Updating '{self.configJsonFile}' ...")
        shutil.copy(os.path.join(self.botHelper.envVars['currWorkDir'], self.configJsonFile),
                    os.path.join(self.botHelper.envVars['currWorkDir'], self.configJsonBakFile))
        self.jsonFileWrite(self.configJsonFile, self.configVars)
        if self.botHelper.envVars['dynamicConfig']:
            self.configFileSync([self.configJsonFile, self.configJsonBakFile])
            self.updateFileidJson()
        self.logger.info(f"Updated '{self.configJsonFile}' !")

    def updateFileidJson(self) -> None:
        self.logger.info(f"Updating '{self.fileidJsonFile}' ...")
        fileidJsonDict: typing.Dict[str, str] = {}
        for configFile in self.configFiles:
            configFileIdKey = self.botHelper.getHelper.fileIdKey(configFile)
            configFileHashKey = self.botHelper.getHelper.fileHashKey(configFile)
            self.botHelper.envVars[configFileHashKey] = self.botHelper.getHelper.fileHash(os.path.join(self.botHelper.envVars['currWorkDir'], configFile))
            fileidJsonDict[configFileIdKey] = self.botHelper.envVars[configFileIdKey]
            fileidJsonDict[configFileHashKey] = self.botHelper.envVars[configFileHashKey]
        self.jsonFileWrite(self.fileidJsonFile, fileidJsonDict)
        self.configFileSync([self.fileidJsonFile])
        self.logger.info(f"Updated '{self.fileidJsonFile}' !")


class GetHelper(BaseHelper):
    def __init__(self, botHelper: BotHelper):
        super().__init__(botHelper)

    def initHelper(self) -> None:
        super().initHelper()
        self.keySuffixId: str = 'Id'
        self.keySuffixHash: str = 'Hash'
        self.sizeUnits: [str] = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        self.progressUnits: typing.List[str] = ['▏', '▎', '▍', '▌', '▋', '▊', '▉', '█']

    @staticmethod
    def chatDetails(update: telegram.Update) -> (int, str, str):
        if update.message.reply_to_message:
            user = update.message.reply_to_message.from_user
            return user.id, user.first_name, 'private'
        else:
            chat = update.effective_chat
            return chat.id, (chat.first_name if chat.type == 'private' else chat.title), chat.type

    def fileIdKey(self, fileName: str) -> str:
        splitList = fileName.split('.')
        fileIdKeyStr = splitList[0]
        if len(splitList) > 1:
            for i in range(1, len(splitList)):
                fileIdKeyStr += splitList[i].capitalize()
        fileIdKeyStr += self.keySuffixId
        return fileIdKeyStr

    def fileHashKey(self, fileName: str) -> str:
        fileHashKeyStr = self.fileIdKey(fileName).replace(self.keySuffixId, self.keySuffixHash)
        return fileHashKeyStr

    @staticmethod
    def fileHash(filePath: str) -> str:
        hashSum = hashlib.sha256()
        blockSize = 128 * hashSum.block_size
        fileStream = open(filePath, 'rb')
        fileChunk = fileStream.read(blockSize)
        while fileChunk:
            hashSum.update(fileChunk)
            fileChunk = fileStream.read(blockSize)
        return hashSum.hexdigest()

    def progressBar(self, progress: float) -> str:
        progressRounded = round(progress)
        numFull = progressRounded // 8
        numEmpty = (100 // 8) - numFull
        partIndex = (progressRounded % 8) - 1
        return f"{self.progressUnits[-1] * numFull}{(self.progressUnits[partIndex] if partIndex >= 0 else '')}{' ' * numEmpty}"

    @staticmethod
    def randomString(length: int) -> str:
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def readableSize(self, numBytes: int) -> str:
        i = 0
        if numBytes is None:
            numBytes = 0
        while numBytes >= 1024:
            numBytes /= 1024
            i += 1
        return f'{round(numBytes, 2)} {self.sizeUnits[i]}'

    @staticmethod
    def readableTime(seconds: float) -> str:
        readableTimeStr = ''
        (numDays, remainderHours) = divmod(seconds, 86400)
        numDays = int(numDays)
        if numDays != 0:
            readableTimeStr += f'{numDays}d'
        (numHours, remainderMins) = divmod(remainderHours, 3600)
        numHours = int(numHours)
        if numHours != 0:
            readableTimeStr += f'{numHours}h'
        (numMins, remainderSecs) = divmod(remainderMins, 60)
        numMins = int(numMins)
        if numMins != 0:
            readableTimeStr += f'{numMins}m'
        numSecs = int(remainderSecs)
        readableTimeStr += f'{numSecs}s'
        return readableTimeStr

    def statsMsg(self) -> str:
        botUpTime = self.readableTime(time.time() - self.botHelper.startTime)
        cpuUsage = psutil.cpu_percent(interval=0.5)
        memoryUsage = psutil.virtual_memory().percent
        diskUsageTotal, diskUsageUsed, diskUsageFree, diskUsage = psutil.disk_usage('.')
        statsMsg = f'botUpTime: {botUpTime}\n' \
                   f'cpuUsage: {cpuUsage}%\n' \
                   f'memoryUsage: {memoryUsage}%\n' \
                   f'diskUsage: {diskUsage}%\n' \
                   f'Total: {self.readableSize(diskUsageTotal)} | ' \
                   f'Used: {self.readableSize(diskUsageUsed)} | ' \
                   f'Free: {self.readableSize(diskUsageFree)}\n' \
                   f'dataDown: {self.readableSize(psutil.net_io_counters().bytes_recv)} | ' \
                   f'dataUp: {self.readableSize(psutil.net_io_counters().bytes_sent)}\n'
        return statsMsg


class LoggingHelper(BaseHelper):
    LogFormats: typing.Dict[str, str] = \
        {'DEFAULT': '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | '
                    '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
         'INFO': '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <6}</level> | <k>{message}</k>',
         'DEBUG': '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | '
                  '<cyan>{name}</cyan>:<cyan>{extra[classname]}</cyan>:<cyan>{function}()</cyan>:<cyan>{line}</cyan> | '
                  '<k>{message}</k>'}

    def __init__(self, botHelper: BotHelper):
        super().__init__(botHelper)

    def initHelper(self) -> None:
        self.logFiles: typing.List[str] = ['bot.log', 'botApiServer.log', 'ariaDaemon.log',
                                           'tqueue.binlog', 'webhooks_db.binlog']
        if os.path.exists(self.logFiles[0]):
            os.remove(self.logFiles[0])
        self.logLevel = (list(self.LogFormats.keys())[2] if os.path.exists(self.botHelper.logDebugFile) else list(self.LogFormats.keys())[1])
        self.logDisableModules: typing.List[str] = ['apscheduler', 'telegram.vendor.ptb_urllib3.urllib3.connectionpool']
        self.logger = loguru.logger
        self.logger.remove()
        self.logger.add(sys.stderr, level=self.logLevel, format=self.LogFormats[self.logLevel])
        self.logger.add(self.logFiles[0], level=self.logLevel, format=self.LogFormats[self.logLevel], rotation='24h')
        self.logger.configure(extra={'classname': 'None'})
        logging.basicConfig(handlers=[InterceptHandler(self.logger)], level=0)
        warnings.filterwarnings('ignore')
        if self.logLevel == list(self.LogFormats.keys())[1]:
            for logDisableModule in self.logDisableModules:
                self.logger.disable(logDisableModule)


class ThreadingHelper(BaseHelper):
    def __init__(self, botHelper: BotHelper):
        super().__init__(botHelper)

    def initHelper(self) -> None:
        super().initHelper()
        self.runningThreads: typing.List[threading.Thread] = []

    def initThread(self, target: typing.Callable, name: str, *args: object, **kwargs: object) -> None:
        thread = threading.Thread(target=self.wrapThread, name=name, args=(target,) + args, kwargs=kwargs, )
        thread.start()

    def wrapThread(self, target: typing.Callable, *args: object, **kwargs: object) -> None:
        currentThread = threading.current_thread()
        self.runningThreads.append(currentThread)
        self.logger.debug(f'Thread Started: {currentThread.name} [runningThreads - {len(self.runningThreads)}]')
        try:
            target(*args, **kwargs)
        except Exception:
            self.logger.exception(f'Unhandled Exception in Thread: {currentThread.name}')
            raise
        self.runningThreads.remove(currentThread)
        self.logger.debug(f'Thread Ended: {currentThread.name} [runningThreads - {len(self.runningThreads)}]')


class BotCommandHelper(BaseHelper):
    StartCmd = telegram.BotCommand(command='start', description='StartCommand')
    HelpCmd = telegram.BotCommand(command='help', description='HelpCommand')
    StatsCmd = telegram.BotCommand(command='stats', description='StatsCommand')
    PingCmd = telegram.BotCommand(command='ping', description='PingCommand')
    RestartCmd = telegram.BotCommand(command='restart', description='RestartCommand')
    LogCmd = telegram.BotCommand(command='log', description='LogCommand')
    MirrorCmd = telegram.BotCommand(command='mirror', description='MirrorCommand')
    StatusCmd = telegram.BotCommand(command='status', description='StatusCommand')
    CancelCmd = telegram.BotCommand(command='cancel', description='CancelCommand')
    ListCmd = telegram.BotCommand(command='list', description='ListCommand')
    DeleteCmd = telegram.BotCommand(command='delete', description='DeleteCommand')
    AuthorizeCmd = telegram.BotCommand(command='authorize', description='AuthorizeCommand')
    UnauthorizeCmd = telegram.BotCommand(command='unauthorize', description='UnauthorizeCommand')
    SyncCmd = telegram.BotCommand(command='sync', description='SyncCommand')
    TopCmd = telegram.BotCommand(command='top', description='TopCommand')
    ConfigCmd = telegram.BotCommand(command='config', description='ConfigCommand')

    def __init__(self, botHelper: BotHelper):
        super().__init__(botHelper)

    def initHelper(self) -> None:
        super().initHelper()
        self.startCmdHandler = telegram.ext.CommandHandler(command=self.StartCmd.command,
                                                           callback=self.startCallBack, run_async=True)
        self.helpCmdHandler = telegram.ext.CommandHandler(command=self.HelpCmd.command,
                                                          callback=self.helpCallBack, run_async=True)
        self.statsCmdHandler = telegram.ext.CommandHandler(command=self.StatsCmd.command,
                                                           callback=self.statsCallBack, run_async=True)
        self.pingCmdHandler = telegram.ext.CommandHandler(command=self.PingCmd.command,
                                                          callback=self.pingCallBack, run_async=True)
        self.restartCmdHandler = telegram.ext.CommandHandler(command=self.RestartCmd.command,
                                                             callback=self.restartCallBack, run_async=True)
        self.statusCmdHandler = telegram.ext.CommandHandler(command=self.StatusCmd.command,
                                                            callback=self.statusCallBack, run_async=True)
        self.cancelCmdHandler = telegram.ext.CommandHandler(command=self.CancelCmd.command,
                                                            callback=self.cancelCallBack, run_async=True)
        self.listCmdHandler = telegram.ext.CommandHandler(command=self.ListCmd.command,
                                                          callback=self.listCallBack, run_async=True)
        self.deleteCmdHandler = telegram.ext.CommandHandler(command=self.DeleteCmd.command,
                                                            callback=self.deleteCallBack, run_async=True)
        self.authorizeCmdHandler = telegram.ext.CommandHandler(command=self.AuthorizeCmd.command,
                                                               callback=self.authorizeCallBack, run_async=True)
        self.unauthorizeCmdHandler = telegram.ext.CommandHandler(command=self.UnauthorizeCmd.command,
                                                                 callback=self.unauthorizeCallBack, run_async=True)
        self.syncCmdHandler = telegram.ext.CommandHandler(command=self.SyncCmd.command,
                                                          callback=self.syncCallBack, run_async=True)
        self.topCmdHandler = telegram.ext.CommandHandler(command=self.TopCmd.command,
                                                         callback=self.topCallBack, run_async=True)
        self.cmdHandlers: typing.List[telegram.ext.CommandHandler] = \
            [self.startCmdHandler, self.helpCmdHandler, self.statsCmdHandler, self.pingCmdHandler,
             self.restartCmdHandler, self.statusCmdHandler, self.cancelCmdHandler, self.listCmdHandler,
             self.deleteCmdHandler, self.authorizeCmdHandler, self.unauthorizeCmdHandler,
             self.syncCmdHandler, self.topCmdHandler]

    def startCallBack(self, update: telegram.Update, _: telegram.ext.CallbackContext):
        self.botHelper.bot.sendMessage(text=f'A Telegram Bot Written in Python to Mirror Files on the Internet to Google Drive.\n'
                                            f'Use /{self.HelpCmd.command} for More Info.', parse_mode='HTML',
                                       chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)

    def helpCallBack(self, update: telegram.Update, _: telegram.ext.CallbackContext):
        self.botHelper.bot.sendMessage(text=f'/{self.StartCmd.command} {self.StartCmd.description}\n'
                                            f'/{self.HelpCmd.command} {self.HelpCmd.description}\n'
                                            f'/{self.StatsCmd.command} {self.StatsCmd.description}\n'
                                            f'/{self.PingCmd.command} {self.PingCmd.description}\n'
                                            f'/{self.RestartCmd.command} {self.RestartCmd.description}\n'
                                            f'/{self.LogCmd.command} {self.LogCmd.description}\n'
                                            f'/{self.MirrorCmd.command} {self.MirrorCmd.description}\n'
                                            f'/{self.StatusCmd.command} {self.StatusCmd.description}\n'
                                            f'/{self.CancelCmd.command} {self.CancelCmd.description}\n'
                                            f'/{self.ListCmd.command} {self.ListCmd.description}\n'
                                            f'/{self.DeleteCmd.command} {self.DeleteCmd.description}\n'
                                            f'/{self.AuthorizeCmd.command} {self.AuthorizeCmd.description}\n'
                                            f'/{self.UnauthorizeCmd.command} {self.UnauthorizeCmd.description}\n'
                                            f'/{self.SyncCmd.command} {self.SyncCmd.description}\n'
                                            f'/{self.TopCmd.command} {self.TopCmd.description}\n'
                                            f'/{self.ConfigCmd.command} {self.ConfigCmd.description}\n', parse_mode='HTML',
                                       chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)

    def statsCallBack(self, update: telegram.Update, _: telegram.ext.CallbackContext):
        self.botHelper.bot.sendMessage(text=self.botHelper.getHelper.statsMsg(), parse_mode='HTML',
                                       chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)

    # TODO: CommandHandler for /ping
    def pingCallBack(self, update: telegram.Update, _: telegram.ext.CallbackContext):
        self.botHelper.bot.sendMessage(text='PingCommand Test Message', parse_mode='HTML', chat_id=update.message.chat_id,
                                       reply_to_message_id=update.message.message_id)

    def restartCallBack(self, update: telegram.Update, _: telegram.ext.CallbackContext):
        restartMsg = self.botHelper.bot.sendMessage(text='Restarting the Bot...', parse_mode='HTML',
                                                    chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)
        self.botHelper.restartMsgInfo['chatId'] = restartMsg.chat_id
        self.botHelper.restartMsgInfo['msgId'] = restartMsg.message_id
        self.botHelper.botRestart()

    def statusCallBack(self, update: telegram.Update, _: telegram.ext.CallbackContext):
        self.botHelper.threadingHelper.initThread(target=self.botHelper.statusHelper.addStatus, name='statusCallBack-addStatus',
                                                  chatId=update.message.chat.id, msgId=update.message.message_id)

    def cancelCallBack(self, update: telegram.Update, _: telegram.ext.CallbackContext):
        self.botHelper.mirrorHelper.cancelMirror(update.message)

    # TODO: CommandHandler for /list
    def listCallBack(self, update: telegram.Update, _: telegram.ext.CallbackContext):
        self.botHelper.bot.sendMessage(text='ListCommand Test Message', parse_mode='HTML',
                                       chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)

    def deleteCallBack(self, update: telegram.Update, _: telegram.ext.CallbackContext):
        self.botHelper.bot.sendMessage(text=self.botHelper.googleDriveHelper.deleteByUrl(update.message.text.split(' ')[1].strip()),
                                       parse_mode='HTML', chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)

    def authorizeCallBack(self, update: telegram.Update, _: telegram.ext.CallbackContext):
        chatId, chatName, chatType = self.botHelper.getHelper.chatDetails(update)
        if str(chatId) in self.botHelper.configHelper.configVars[self.botHelper.configHelper.optVars[1]].keys():
            replyTxt = f"Already Authorized Chat: '{chatName}' - ({chatId}) ({chatType}) !"
        else:
            self.botHelper.configHelper.updateAuthorizedChats(chatId, chatName, chatType, auth=True)
            replyTxt = f"Authorized Chat: '{chatName}' - ({chatId}) ({chatType}) !"
        self.logger.info(replyTxt)
        self.botHelper.bot.sendMessage(text=replyTxt, parse_mode='HTML', chat_id=update.message.chat_id,
                                       reply_to_message_id=update.message.message_id)

    def unauthorizeCallBack(self, update: telegram.Update, _: telegram.ext.CallbackContext):
        chatId, chatName, chatType = self.botHelper.getHelper.chatDetails(update)
        if str(chatId) in self.botHelper.configHelper.configVars[self.botHelper.configHelper.optVars[1]].keys():
            self.botHelper.configHelper.updateAuthorizedChats(chatId, chatName, chatType, unauth=True)
            replyTxt = f"Unauthorized Chat: '{chatName}' - ({chatId}) ({chatType}) !"
        else:
            replyTxt = f"Already Unauthorized Chat: '{chatName}' - ({chatId}) ({chatType}) !"
        self.logger.info(replyTxt)
        self.botHelper.bot.sendMessage(text=replyTxt, parse_mode='HTML', chat_id=update.message.chat_id,
                                       reply_to_message_id=update.message.message_id)

    def syncCallBack(self, update: telegram.Update, _: telegram.ext.CallbackContext):
        if self.botHelper.envVars['dynamicConfig']:
            replyMsgTxt = 'Syncing to Google Drive...'
            self.logger.info(replyMsgTxt)
            replyMsg = self.botHelper.bot.sendMessage(text=replyMsgTxt, parse_mode='HTML', chat_id=update.message.chat_id,
                                                      reply_to_message_id=update.message.message_id)
            self.botHelper.configHelper.configFileSync(self.botHelper.configHelper.configFiles)
            self.botHelper.configHelper.updateFileidJson()
            self.logger.info('Sync Completed !')
            replyMsg.edit_text(f'Sync Completed !\n{self.botHelper.configHelper.configFiles}\nPlease /{self.RestartCmd.command} !')
        else:
            replyMsgTxt = "Not Synced - Using Static Config !"
            self.logger.info(replyMsgTxt)
            self.botHelper.bot.sendMessage(text=replyMsgTxt, parse_mode='HTML', chat_id=update.message.chat_id,
                                           reply_to_message_id=update.message.message_id)

    # TODO: format this properly later or else remove from release
    def topCallBack(self, update: telegram.Update, _: telegram.ext.CallbackContext):
        topMsg = ''
        tgmbProc = psutil.Process(os.getpid())
        ariaDaemonProc = psutil.Process(self.botHelper.ariaHelper.daemonPid)
        botApiServerProc = psutil.Process(self.botHelper.apiServerPid)
        topMsg += f'{tgmbProc.name()}\n{tgmbProc.cpu_percent()}\n{tgmbProc.memory_percent()}\n'
        topMsg += f'{ariaDaemonProc.name()}\n{ariaDaemonProc.cpu_percent()}\n{ariaDaemonProc.memory_percent()}\n'
        topMsg += f'{botApiServerProc.name()}\n{botApiServerProc.cpu_percent()}\n{botApiServerProc.memory_percent()}\n'
        self.botHelper.bot.sendMessage(text=topMsg, parse_mode='HTML', chat_id=update.message.chat_id,
                                       reply_to_message_id=update.message.message_id)

    def unknownCallBack(self, update: telegram.Update, _: telegram.ext.CallbackContext):
        if not '@' in update.message.text.split(' ')[0]:
            self.botHelper.bot.sendMessage(text='Sorry, the command is not registered with a CommandHandler !', parse_mode='HTML',
                                           chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id)


class BotConversationHelper(BaseHelper):
    def __init__(self, botHelper: BotHelper):
        super().__init__(botHelper)
        self.configConvHelper = ConfigConvHelper(self.botHelper)
        self.logConvHelper = LogConvHelper(self.botHelper)
        self.mirrorConvHelper = MirrorConvHelper(self.botHelper)

    def initHelper(self) -> None:
        super().initHelper()
        self.initSubHelpers()
        self.convHandlers: typing.List[telegram.ext.ConversationHandler] = \
            [self.configConvHelper.handler, self.logConvHelper.handler, self.mirrorConvHelper.handler]

    def initSubHelpers(self):
        self.configConvHelper.initHelper()
        self.logConvHelper.initHelper()
        self.mirrorConvHelper.initHelper()


class ConfigConvHelper(BaseHelper):
    def __init__(self, botHelper: BotHelper):
        super().__init__(botHelper)

    def initHelper(self) -> None:
        super().initHelper()
        self.configVarsEditable: typing.Dict
        self.configVarsNew: typing.Dict[str, str]
        self.tempKeyIndex: int
        self.tempKey: str
        self.tempVal: str
        self.newValMsg: telegram.Message
        self.FIRST, self.SECOND, self.THIRD, self.FOURTH, self.FIFTH, self.SIXTH = range(6)
        # TODO: filter - add owner_filter
        self.cmdHandler = telegram.ext.CommandHandler(self.botHelper.botCmdHelper.ConfigCmd.command, self.stageZero)
        self.handler = telegram.ext.ConversationHandler(entry_points=[self.cmdHandler], fallbacks=[self.cmdHandler],
                                                        states={
                                                            # ZEROTH
                                                            # Choose Environment Variable
                                                            self.FIRST: [telegram.ext.CallbackQueryHandler(self.stageOne)],
                                                            # Show Existing Value
                                                            self.SECOND: [telegram.ext.CallbackQueryHandler(self.stageTwo)],
                                                            # Capture New Value for Environment Variable
                                                            self.THIRD: [
                                                                telegram.ext.CallbackQueryHandler(self.stageThree),
                                                                telegram.ext.MessageHandler(telegram.ext.Filters.text, self.newVal)
                                                            ],
                                                            # Verify New Value
                                                            self.FOURTH: [telegram.ext.CallbackQueryHandler(self.stageFour)],
                                                            # Show All Changes and Proceed
                                                            self.FIFTH: [telegram.ext.CallbackQueryHandler(self.stageFive)],
                                                            # Save or Discard Changes
                                                            self.SIXTH: [telegram.ext.CallbackQueryHandler(self.stageSix)]
                                                            # Exit or Start Over
                                                        },
                                                        conversation_timeout=120, run_async=True)

    def stageZero(self, update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
        self.logger.info(f"Owner '{update.message.from_user.first_name}' is Editing '{self.botHelper.configHelper.configJsonFile}'...")
        self.loadConfigDict()
        return self.chooseKey(update=update)

    def stageOne(self, update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        return self.viewVal(query)

    def stageTwo(self, update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        if query.data == '1':
            return self.editVal(query)
        if query.data == '2':
            return self.chooseKey(query=query)

    def stageThree(self, update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        if query.data == '1':
            return self.verifyNewVal(query)
        if query.data == '2':
            return self.editVal(query)

    def stageFour(self, update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        if query.data == '1':
            return self.proceedNewVal(query)
        if query.data == '2':
            return self.chooseKey(query=query)

    def stageFive(self, update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        if query.data == '1':
            return self.saveChanges(query)
        if query.data == '2':
            return self.discardChanges(query)
        if query.data == '3':
            return self.chooseKey(query=query)

    def stageSix(self, update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        if query.data == '1':
            self.loadConfigDict()
            return self.chooseKey(query=query)
        if query.data == '2':
            return self.convEnd(query)

    def loadConfigDict(self):
        self.resetAllDat()
        self.configVarsEditable = self.botHelper.configHelper.jsonFileLoad(self.botHelper.configHelper.configJsonFile)
        for key in [self.botHelper.configHelper.reqVars[4], self.botHelper.configHelper.reqVars[5], self.botHelper.configHelper.optVars[1]]:
            if key in list(self.configVarsEditable.keys()):
                self.configVarsEditable.pop(key)

    def chooseKey(self, update: telegram.Update = None, query: telegram.CallbackQuery = None) -> int:
        self.tempKey, self.tempVal = '', ''
        if query is None:
            update.message.reply_text(text="Select an Environment Variable:",
                                      reply_markup=InlineKeyboardMaker(list(self.configVarsEditable.keys()) + ['Exit']).build(1))
        if update is None:
            query.edit_message_text(text="Select an Environment Variable:",
                                    reply_markup=InlineKeyboardMaker(list(self.configVarsEditable.keys()) + ['Exit']).build(1))
        return self.FIRST

    def viewVal(self, query: telegram.CallbackQuery) -> int:
        self.tempKeyIndex = int(query.data) - 1
        if self.tempKeyIndex != len(list(self.configVarsEditable.keys())):
            self.tempKey = list(self.configVarsEditable.keys())[self.tempKeyIndex]
            query.edit_message_text(text=f'"{self.tempKey}" = "{self.configVarsEditable[self.tempKey]}"',
                                    reply_markup=InlineKeyboardMaker(['Edit', 'Back']).build(2))
            return self.SECOND
        else:
            return self.convEnd(query)

    def editVal(self, query: telegram.CallbackQuery) -> int:
        query.edit_message_text(text=f'Send New Value for "{self.tempKey}":',
                                reply_markup=InlineKeyboardMaker(['Ok', 'Back']).build(2))
        return self.THIRD

    def newVal(self, update: telegram.Update, _: telegram.ext.CallbackContext) -> None:
        self.newValMsg = update.message
        self.tempVal = self.newValMsg['text']

    def verifyNewVal(self, query: telegram.CallbackQuery) -> int:
        self.botHelper.bot.deleteMessage(chat_id=self.newValMsg.chat_id, message_id=self.newValMsg.message_id)
        query.edit_message_text(text=f'Entered Value is:\n\n"{self.tempVal}"',
                                reply_markup=InlineKeyboardMaker(['Update Value', 'Back']).build(2))
        return self.FOURTH

    def proceedNewVal(self, query: telegram.CallbackQuery) -> int:
        self.configVarsNew[self.tempKey] = self.tempVal
        buttonList = ['Save Changes', 'Discard Changes', 'Change Another Value']
        replyStr = ''
        for i in range(len(list(self.configVarsNew.keys()))):
            replyStr += f'{list(self.configVarsNew.keys())[i]} = "{list(self.configVarsNew.values())[i]}"' + '\n'
        query.edit_message_text(text=replyStr, reply_markup=InlineKeyboardMaker(buttonList).build(1))
        return self.FIFTH

    def discardChanges(self, query: telegram.CallbackQuery) -> int:
        self.configVarsNew = {}
        self.logger.info(f"Owner '{query.from_user.first_name}' Discarded Changes Made to '{self.botHelper.configHelper.configJsonFile}' !")
        query.edit_message_text(text=f"Discarded Changes.", reply_markup=InlineKeyboardMaker(['Start Over', 'Exit']).build(2))
        return self.SIXTH

    def saveChanges(self, query: telegram.CallbackQuery) -> int:
        query.edit_message_text(text=f"Saving Changes...")
        for configVarKey in list(self.configVarsNew.keys()):
            self.botHelper.configHelper.configVars[configVarKey] = self.configVarsNew[configVarKey]
        self.botHelper.configHelper.updateConfigJson()
        self.logger.info(f"Owner '{query.from_user.first_name}' Saved Changes Made to '{self.botHelper.configHelper.configJsonFile}' !")
        query.edit_message_text(text=f"Saved Changes.\nPlease /{self.botHelper.botCmdHelper.RestartCmd.command} to Load Changes.")
        return telegram.ext.ConversationHandler.END

    def convEnd(self, query: telegram.CallbackQuery) -> int:
        self.resetAllDat()
        query.edit_message_text(text=f"Exited Config Editor.")
        return telegram.ext.ConversationHandler.END

    def resetAllDat(self) -> None:
        self.configVarsEditable = {}
        self.configVarsNew = {}
        self.tempKeyIndex = 0
        self.tempKey = ''
        self.tempVal = ''


class LogConvHelper(BaseHelper):
    def __init__(self, botHelper: BotHelper):
        super().__init__(botHelper)

    def initHelper(self) -> None:
        super().initHelper()
        self.chatId: int
        self.msgId: int
        self.sentMsgId: int
        self.docSendTimeout: int = 600
        self.FIRST = range(1)[0]
        # TODO: filter - restrict to user who sent LogCommand
        self.cmdHandler = telegram.ext.CommandHandler(self.botHelper.botCmdHelper.LogCmd.command, self.stageZero)
        self.handler = telegram.ext.ConversationHandler(entry_points=[self.cmdHandler], fallbacks=[self.cmdHandler],
                                                        states={self.FIRST: [telegram.ext.CallbackQueryHandler(self.stageOne)]},
                                                        conversation_timeout=120, run_async=True)

    def stageZero(self, update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
        self.chatId = update.message.chat.id
        self.msgId = update.message.message_id
        buttonList: typing.List[str] = \
            [f'[{logFile}] [{self.botHelper.getHelper.readableSize(os.path.getsize(logFile))}]' for logFile in self.botHelper.loggingHelper.logFiles[0:3]]
        buttonList += ['All', 'Exit']
        self.sentMsgId = update.message.reply_text(text='Select:', reply_markup=InlineKeyboardMaker(buttonList).build(1)).message_id
        return self.FIRST

    def stageOne(self, update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        if query.data in ['1', '2', '3', '4']:
            query.edit_message_text(text='Uploading logFiles...')
            if query.data == '4':
                self.botHelper.bot.sendMediaGroup(media=[telegram.InputMediaDocument(logFile) for logFile in self.botHelper.loggingHelper.logFiles[0:3]],
                                                  timeout=self.docSendTimeout, chat_id=self.chatId, reply_to_message_id=self.msgId)
                self.logger.info("Sent logFiles !")
            else:
                logFileIndex = int(query.data) - 1
                self.botHelper.bot.sendDocument(document=f"file://{self.botHelper.envVars['currWorkDir']}/{self.botHelper.loggingHelper.logFiles[logFileIndex]}",
                                                filename=self.botHelper.loggingHelper.logFiles[logFileIndex], timeout=self.docSendTimeout,
                                                chat_id=self.chatId, reply_to_message_id=self.msgId)
                self.logger.info(f"Sent logFile: '{self.botHelper.loggingHelper.logFiles[logFileIndex]}' !")
            self.botHelper.bot.deleteMessage(chat_id=self.chatId, message_id=self.sentMsgId)
        if query.data == '5':
            query.edit_message_text(text='Exited.')
        return telegram.ext.ConversationHandler.END


class MirrorConvHelper(BaseHelper):
    def __init__(self, botHelper: BotHelper):
        super().__init__(botHelper)

    def initHelper(self) -> None:
        super().initHelper()
        self.isValidDl: bool
        self.mirrorInfo: MirrorInfo
        self.FIRST, self.SECOND, self.THIRD, self.FOURTH, self.FIFTH = range(5)
        # TODO: filter - restrict to user who sent MirrorCommand
        self.cmdHandler = telegram.ext.CommandHandler(self.botHelper.botCmdHelper.MirrorCmd.command, self.stageZero)
        self.handler = telegram.ext.ConversationHandler(entry_points=[self.cmdHandler], fallbacks=[self.cmdHandler],
                                                        states={
                                                            # ZEROTH
                                                            # Choose to Modify or Use Default Values
                                                            self.FIRST: [telegram.ext.CallbackQueryHandler(self.stageOne)],
                                                            # Choose Upload Location
                                                            self.SECOND: [telegram.ext.CallbackQueryHandler(self.stageTwo)],
                                                            # Choose googleDriveUploadFolder
                                                            self.THIRD: [telegram.ext.CallbackQueryHandler(self.stageThree)],
                                                            # Choose Compress / Decompress
                                                            self.FOURTH: [telegram.ext.CallbackQueryHandler(self.stageFour)],
                                                            # Confirm and Proceed / Cancel
                                                            self.FIFTH: [telegram.ext.CallbackQueryHandler(self.stageFive)]
                                                        },
                                                        conversation_timeout=120, run_async=True)

    def stageZero(self, update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
        self.isValidDl, self.mirrorInfo = self.botHelper.mirrorHelper.genMirrorInfo(update.message)
        if self.isValidDl:
            # <setDefaults>
            self.mirrorInfo.isGoogleDriveUpload = True
            self.mirrorInfo.googleDriveUploadFolderId = \
            list(self.botHelper.configHelper.configVars[self.botHelper.configHelper.reqVars[5]].keys())[0]
            # </setDefaults>
            update.message.reply_text(text=self.getMirrorInfoStr(), reply_to_message_id=update.message.message_id,
                                      reply_markup=InlineKeyboardMaker(['Use Defaults', 'Customize']).build(1))
            return self.FIRST
        if not self.isValidDl:
            update.message.reply_text(text='No Valid Link Provided !', reply_to_message_id=update.message.message_id)
            return telegram.ext.ConversationHandler.END

    def stageOne(self, update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        if query.data == '1':
            self.logger.info(f"addMirror - ({self.mirrorInfo.uid}) ['{self.mirrorInfo.downloadUrl}']")
            self.botHelper.mirrorHelper.addMirror(self.mirrorInfo)
            query.edit_message_text(text='addMirror Succeeded !')
            return telegram.ext.ConversationHandler.END
        elif query.data == '2':
            buttonList = ['Google Drive', 'Mega', 'Telegram']
            query.edit_message_text(text='Choose Upload Location:', reply_markup=InlineKeyboardMaker(buttonList).build(1))
            return self.SECOND

    def stageTwo(self, update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        if query.data == '1':
            buttonList = [*list(self.botHelper.configHelper.configVars[self.botHelper.configHelper.reqVars[5]].values())]
            query.edit_message_text(text='Choose `googleDriveUploadFolder`:', reply_markup=InlineKeyboardMaker(buttonList).build(1))
            return self.THIRD
        elif query.data in ['2', '3']:
            self.mirrorInfo.isGoogleDriveUpload = False
            self.mirrorInfo.googleDriveUploadFolderId = ''
            if query.data == '2':
                self.mirrorInfo.isMegaUpload = True
            elif query.data == '3':
                self.mirrorInfo.isTelegramUpload = True
            buttonList = ['isCompress', 'isDecompress', 'Skip']
            query.edit_message_text(text='Choose:', reply_markup=InlineKeyboardMaker(buttonList).build(1))
            return self.FOURTH

    def stageThree(self, update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        self.mirrorInfo.googleDriveUploadFolderId = \
        list(self.botHelper.configHelper.configVars[self.botHelper.configHelper.reqVars[5]].keys())[(int(query.data) - 1)]
        buttonList = ['isCompress', 'isDecompress', 'Skip']
        query.edit_message_text(text='Choose:', reply_markup=InlineKeyboardMaker(buttonList).build(1))
        return self.FOURTH

    def stageFour(self, update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        if query.data == '1':
            self.mirrorInfo.isCompress = True
        elif query.data == '2':
            self.mirrorInfo.isDecompress = True
        buttonList = ['Proceed', 'Cancel']
        query.edit_message_text(text=self.getMirrorInfoStr(), reply_markup=InlineKeyboardMaker(buttonList).build(1))
        return self.FIFTH

    def stageFive(self, update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        if query.data == '1':
            self.logger.info(f"addMirror - ['{self.mirrorInfo.downloadUrl}']")
            self.botHelper.mirrorHelper.addMirror(self.mirrorInfo)
            query.edit_message_text(text='addMirror Succeeded !')
        elif query.data == '2':
            query.edit_message_text(text='addMirror Cancelled !')
        return telegram.ext.ConversationHandler.END

    # TODO: reduce this function code if possible
    def getMirrorInfoStr(self):
        mirrorInfoStr = f'[uid | {self.mirrorInfo.uid}]\n'
        if self.mirrorInfo.isAriaDownload:
            mirrorInfoStr += f'[isAriaDownload | True]\n'
        elif self.mirrorInfo.isGoogleDriveDownload:
            mirrorInfoStr += f'[isGoogleDriveDownload | True]\n'
        elif self.mirrorInfo.isMegaDownload:
            mirrorInfoStr += f'[isMegaDownload | True]\n'
        elif self.mirrorInfo.isTelegramDownload:
            mirrorInfoStr += f'[isTelegramDownload | True]\n'
        elif self.mirrorInfo.isYouTubeDownload:
            mirrorInfoStr += f'[isYouTubeDownload | True]\n'
        if self.mirrorInfo.isGoogleDriveUpload:
            mirrorInfoStr += f'[isGoogleDriveUpload | True]\n'
        elif self.mirrorInfo.isMegaUpload:
            mirrorInfoStr += f'[isMegaUpload | True]\n'
        elif self.mirrorInfo.isTelegramUpload:
            mirrorInfoStr += f'[isTelegramUpload | True]\n'
        if self.mirrorInfo.isCompress:
            mirrorInfoStr += f'[isCompress | True]\n'
        elif self.mirrorInfo.isDecompress:
            mirrorInfoStr += f'[isDecompress | True]\n'
        if self.mirrorInfo.isGoogleDriveUpload:
            mirrorInfoStr += f'[googleDriveUploadFolderId | {self.mirrorInfo.googleDriveUploadFolderId}]'
        return mirrorInfoStr


class MirrorHelper(BaseHelper):
    def __init__(self, botHelper: BotHelper):
        super().__init__(botHelper)

    def initHelper(self) -> None:
        super().initHelper()
        self.mirrorInfos: typing.Dict[str, MirrorInfo] = {}
        self.supportedArchiveFormats: typing.Dict[str, str] = {'zip': '.zip', 'tar': '.tar', 'bztar': '.tar.bz2',
                                                               'gztar': '.tar.gz', 'xztar': '.tar.xz'}

    def addMirror(self, mirrorInfo: 'MirrorInfo') -> None:
        self.logger.debug(vars(mirrorInfo))
        self.mirrorInfos[mirrorInfo.uid] = mirrorInfo
        self.mirrorInfos[mirrorInfo.uid].timeStart = int(time.time())
        self.botHelper.mirrorListenerHelper.updateStatus(mirrorInfo.uid, MirrorStatus.addMirror)
        self.botHelper.threadingHelper.initThread(target=self.botHelper.statusHelper.addStatus, name=f'{mirrorInfo.uid}-addStatus',
                                                  chatId=mirrorInfo.chatId, msgId=mirrorInfo.msgId)

    def cancelMirror(self, msg: telegram.Message) -> None:
        if self.mirrorInfos == {}:
            self.logger.info('No Active Downloads !')
            return
        uids: typing.List[str] = []
        try:
            msgTxt = msg.text.split(' ')[1].strip()
            if msgTxt == 'all':
                uids = list(self.mirrorInfos.keys())
            if msgTxt in self.mirrorInfos.keys():
                uids.append(msgTxt)
        except IndexError:
            replyTo = msg.reply_to_message
            if replyTo:
                msgId = replyTo.message_id
                for mirrorInfo in self.mirrorInfos.values():
                    if msgId == mirrorInfo.msgId:
                        uids.append(mirrorInfo.uid)
                        break
        if len(uids) == 0:
            self.logger.info('No Valid Mirror Found !')
            return
        for uid in uids:
            self.botHelper.mirrorListenerHelper.updateStatus(uid, MirrorStatus.cancelMirror)

    def genMirrorInfo(self, msg: telegram.Message) -> (bool, 'MirrorInfo'):
        mirrorInfo = MirrorInfo(msg, self.botHelper)
        isValidDl: bool = True
        try:
            mirrorInfo.downloadUrl = msg.text.split(' ')[1].strip()
            mirrorInfo.tag = msg.from_user.username
            if re.findall(UrlRegex.googleDrive, mirrorInfo.downloadUrl):
                mirrorInfo.isGoogleDriveDownload = True
            elif re.findall(UrlRegex.mega, mirrorInfo.downloadUrl):
                mirrorInfo.isMegaDownload = True
            elif re.findall(UrlRegex.youTube, mirrorInfo.downloadUrl):
                mirrorInfo.isYouTubeDownload = True
            elif re.findall(UrlRegex.bittorrentMagnet, mirrorInfo.downloadUrl):
                mirrorInfo.isAriaDownload = True
            elif re.findall(UrlRegex.generalUrl, mirrorInfo.downloadUrl):
                mirrorInfo.isAriaDownload = True
            else:
                isValidDl = False
        except IndexError:
            replyTo = msg.reply_to_message
            if replyTo:
                mirrorInfo.tag = replyTo.from_user.username
                for media in [replyTo.document, replyTo.audio, replyTo.video]:
                    if media:
                        if media.mime_type == 'application/x-bittorrent':
                            mirrorInfo.isAriaDownload = True
                            mirrorInfo.downloadUrl = media.get_file().file_path
                        else:
                            mirrorInfo.isTelegramDownload = True
                        break
            else:
                isValidDl = False
        if not isValidDl:
            self.logger.info('No Valid Link Provided !')
        return isValidDl, mirrorInfo


class AriaHelper(BaseHelper):
    def __init__(self, botHelper: BotHelper):
        super().__init__(botHelper)

    def initHelper(self) -> None:
        super().initHelper()
        self.rpcSecret = (self.botHelper.restartVars['ariaRpcSecret'] if self.botHelper.restartVars else self.botHelper.getHelper.randomString(8))
        self.api = aria2p.API(aria2p.Client(host="http://localhost", port=6800, secret=self.rpcSecret))
        self.daemonPid: int = 0
        self.daemonStartCmd: typing.List[str] = ['aria2c', '--quiet', '--enable-rpc', f'--rpc-secret={self.rpcSecret}',
                                                 '--rpc-max-request-size=32M', f'--log={self.botHelper.loggingHelper.logFiles[2]}']
        self.globalOpts: aria2p.Options
        self.trackersListFile = 'trackers.list'
        self.gids: typing.Dict[str, str] = {}

    def addDownload(self, mirrorInfo: 'MirrorInfo') -> None:
        if re.findall(UrlRegex.bittorrentMagnet, mirrorInfo.downloadUrl):
            self.gids[mirrorInfo.uid] = self.api.add_magnet(mirrorInfo.downloadUrl, options={'dir': mirrorInfo.path}).gid
        if re.findall(UrlRegex.generalUrl, mirrorInfo.downloadUrl):
            self.gids[mirrorInfo.uid] = self.api.add_uris([mirrorInfo.downloadUrl], options={'dir': mirrorInfo.path}).gid

    def cancelDownload(self, uid: str) -> None:
        self.getDlObj(self.gids[uid]).remove(force=True, files=True)
        self.gids.pop(uid)

    def getUid(self, gid: str) -> str:
        for uid in self.gids.keys():
            if gid == self.gids[uid]:
                return uid

    def getDlObj(self, gid: str) -> aria2p.Download:
        return self.api.get_download(gid)

    def daemonStart(self) -> None:
        if self.botHelper.restartVars and self.botHelper.restartVars['ariaDaemonPid']:
            self.daemonPid = self.botHelper.restartVars['ariaDaemonPid']
            self.logger.info(f'ariaDaemon Already Running (pid {self.daemonPid}) !')
        if not self.daemonPid:
            self.daemonPid = subprocess.Popen(self.daemonStartCmd).pid
            self.logger.info(f"ariaDaemon started (pid {self.daemonPid}) !")

    # TODO: implement this method
    def daemonCheck(self):
        pass

    def daemonStop(self) -> None:
        os.kill(self.daemonPid, signal.SIGTERM)
        self.logger.info(f"ariaDaemon terminated (pid {self.daemonPid})")

    def globalOptsGet(self):
        self.globalOpts = self.api.get_global_options()

    def globalOptsSet(self):
        userOpts = copy.deepcopy(self.botHelper.configHelper.configVars[self.botHelper.configHelper.optVars[0]])
        userOpts['bt-tracker'] = open(self.trackersListFile, 'rt').read()
        for optKey in list(userOpts.keys()):
            optSetResponse = self.globalOpts.set(optKey, userOpts[optKey])
            self.logger.debug(f"(ariaGlobalOpts) ({optSetResponse}) ['{optKey}' : '{userOpts[optKey]}']")

    def dlTrackersList(self):
        if os.path.exists(self.trackersListFile):
            os.remove(self.trackersListFile)
        self.logger.debug(f"Downloading '{self.trackersListFile}' ...")
        dlObj = self.api.add_uris(uris=[self.botHelper.configHelper.configVars[self.botHelper.configHelper.optVars[6]]],
                                  options={'out': self.trackersListFile})
        while dlObj.status == 'active':
            time.sleep(0.1)
            dlObj.update()
        if os.path.exists(self.trackersListFile):
            self.logger.debug(f"Downloaded '{self.trackersListFile}' !")
        else:
            self.logger.debug(f"Download Failed - '{self.trackersListFile}' ! Retrying...")
            self.dlTrackersList()

    def startListener(self) -> None:
        self.api.listen_to_notifications(threaded=True,
                                         on_download_start=self.onDownloadStart,
                                         on_download_pause=self.onDownloadPause,
                                         on_download_complete=self.onDownloadComplete,
                                         on_download_stop=self.onDownloadStop,
                                         on_download_error=self.onDownloadError)

    def updateProgress(self, uid: str) -> None:
        if uid in self.gids.keys():
            dlObj = self.getDlObj(self.gids[uid])
            currVars: typing.Dict[str, typing.Union[int, float, str]] \
                = {MirrorInfo.updatableVars[0]: dlObj.total_length,
                   MirrorInfo.updatableVars[1]: dlObj.completed_length,
                   MirrorInfo.updatableVars[2]: dlObj.download_speed,
                   MirrorInfo.updatableVars[3]: int(time.time())}
            if dlObj.is_torrent:
                currVars[MirrorInfo.updatableVars[4]] = True
                currVars[MirrorInfo.updatableVars[5]] = dlObj.num_seeders
                currVars[MirrorInfo.updatableVars[6]] = dlObj.connections
            self.botHelper.mirrorHelper.mirrorInfos[uid].updateVars(currVars)

    def onDownloadStart(self, _: aria2p.API, gid: str) -> None:
        self.logger.debug(vars(self.getDlObj(gid)))

    def onDownloadPause(self, _: aria2p.API, gid: str) -> None:
        self.logger.debug(vars(self.getDlObj(gid)))

    def onDownloadComplete(self, _: aria2p.API, gid: str) -> None:
        self.logger.debug(vars(self.getDlObj(gid)))
        if self.getDlObj(gid).followed_by_ids:
            self.gids[self.getUid(gid)] = self.getDlObj(gid).followed_by_ids[0]
            return
        self.botHelper.mirrorListenerHelper.updateStatus(self.getUid(gid), MirrorStatus.downloadComplete)

    def onDownloadStop(self, _: aria2p.API, gid: str) -> None:
        self.logger.debug(vars(self.getDlObj(gid)))

    def onDownloadError(self, _: aria2p.API, gid: str) -> None:
        self.logger.debug(vars(self.getDlObj(gid)))


class GoogleDriveHelper(BaseHelper):
    def __init__(self, botHelper: BotHelper):
        super().__init__(botHelper)

    def initHelper(self) -> None:
        super().initHelper()
        self.authInfos: typing.List[str] = ['saJson', 'tokenJson']
        self.authTypes: typing.List[str] = ['saAuth', 'userAuth']
        self.oauthScopes: typing.List[str] = ['https://www.googleapis.com/auth/drive']
        self.baseFileDownloadUrl: str = 'https://drive.google.com/uc?id={}&export=download'
        self.baseFolderDownloadUrl: str = 'https://drive.google.com/drive/folders/{}'
        self.googleDriveFolderMimeType: str = 'application/vnd.google-apps.folder'
        self.chunkSize: int = 32 * 1024 * 1024
        self.service: typing.Any = None
        if self.botHelper.configHelper.configVars[self.botHelper.configHelper.reqVars[4]]['authType'] == self.authTypes[0] and \
                self.botHelper.configHelper.configVars[self.botHelper.configHelper.reqVars[4]]['authInfos'][self.authInfos[0]]:
            self.oauthCreds: google.oauth2.service_account.Credentials \
                = google.oauth2.service_account.Credentials.\
                from_service_account_info(self.botHelper.configHelper.configVars[self.botHelper.configHelper.reqVars[4]]['authInfos'][self.authInfos[0]])
        elif self.botHelper.configHelper.configVars[self.botHelper.configHelper.reqVars[4]]['authType'] == self.authTypes[1] and \
                self.botHelper.configHelper.configVars[self.botHelper.configHelper.reqVars[4]]['authInfos'][self.authInfos[1]]:
            self.oauthCreds: google.oauth2.credentials.Credentials \
                = google.oauth2.credentials.Credentials.\
                from_authorized_user_info(self.botHelper.configHelper.configVars[self.botHelper.configHelper.reqVars[4]]['authInfos'][self.authInfos[1]], self.oauthScopes)
        else:
            self.logger.error('No Valid googleDriveAuth in configJsonFile ! Exiting...')
            exit(1)

    def addDownload(self, mirrorInfo: 'MirrorInfo') -> None:
        sourceId = self.getIdFromUrl(mirrorInfo.downloadUrl)
        self.botHelper.mirrorHelper.mirrorInfos[mirrorInfo.uid].updateVars({mirrorInfo.updatableVars[0]: self.getSizeById(sourceId)})
        isFolder = False
        if self.getMetadataById(sourceId, 'mimeType') == self.googleDriveFolderMimeType:
            isFolder = True
        if mirrorInfo.isGoogleDriveUpload and not (mirrorInfo.isCompress or mirrorInfo.isDecompress):
            if isFolder:
                folderId = self.cloneFolder(sourceFolderId=sourceId, parentFolderId=mirrorInfo.googleDriveUploadFolderId)
                self.botHelper.mirrorHelper.mirrorInfos[mirrorInfo.uid].uploadUrl = self.baseFolderDownloadUrl.format(folderId)
            else:
                fileId = self.cloneFile(sourceFileId=sourceId, parentFolderId=mirrorInfo.googleDriveUploadFolderId)
                self.botHelper.mirrorHelper.mirrorInfos[mirrorInfo.uid].uploadUrl = self.baseFileDownloadUrl.format(fileId)
        else:
            if isFolder:
                self.downloadFolder(sourceFolderId=sourceId, dlPath=mirrorInfo.path)
            else:
                self.downloadFile(sourceFileId=sourceId, dlPath=mirrorInfo.path)
        self.botHelper.mirrorListenerHelper.updateStatus(mirrorInfo.uid, MirrorStatus.downloadComplete)

    def cancelDownload(self, uid: str) -> None:
        raise NotImplementedError

    def addUpload(self, mirrorInfo: 'MirrorInfo') -> None:
        if not (mirrorInfo.isGoogleDriveDownload and not (mirrorInfo.isCompress or mirrorInfo.isDecompress)):
            uploadPath = os.path.join(mirrorInfo.path, os.listdir(mirrorInfo.path)[0])
            if os.path.isdir(uploadPath):
                folderId = self.uploadFolder(folderPath=uploadPath, parentFolderId=mirrorInfo.googleDriveUploadFolderId)
                self.botHelper.mirrorHelper.mirrorInfos[mirrorInfo.uid].uploadUrl = self.baseFolderDownloadUrl.format(folderId)
            if os.path.isfile(uploadPath):
                fileId = self.uploadFile(filePath=uploadPath, parentFolderId=mirrorInfo.googleDriveUploadFolderId)
                self.botHelper.mirrorHelper.mirrorInfos[mirrorInfo.uid].uploadUrl = self.baseFileDownloadUrl.format(fileId)
        else:
            time.sleep(self.botHelper.statusHelper.statusUpdateInterval)
        self.botHelper.mirrorListenerHelper.updateStatus(mirrorInfo.uid, MirrorStatus.uploadComplete)

    def cancelUpload(self, uid: str) -> None:
        raise NotImplementedError

    def authorizeApi(self) -> None:
        if self.botHelper.configHelper.configVars[self.botHelper.configHelper.reqVars[4]]['authType'] == self.authTypes[0]:
            self.buildService()
        if self.botHelper.configHelper.configVars[self.botHelper.configHelper.reqVars[4]]['authType'] == self.authTypes[1]:
            if not self.oauthCreds.valid:
                if self.oauthCreds.expired and self.oauthCreds.refresh_token:
                    self.oauthCreds.refresh(google.auth.transport.requests.Request())
                    self.logger.info('Google Drive API Token Refreshed !')
                    self.botHelper.configHelper.configVars[self.botHelper.configHelper.reqVars[4]]['authInfos'][self.authInfos[1]] = json.loads(self.oauthCreds.to_json())
                    self.buildService()
                    self.botHelper.configHelper.updateConfigJson()
                else:
                    self.logger.info('Google Drive API User Token Needs to Refreshed Manually ! Exiting...')
                    exit(1)

    def buildService(self) -> None:
        self.service = googleapiclient.discovery.build(serviceName='drive', version='v3', credentials=self.oauthCreds,
                                                       cache_discovery=False)

    def uploadFile(self, filePath: str, parentFolderId: str) -> str:
        upStatus: googleapiclient.http.MediaUploadProgress
        fileName, fileMimeType, fileMetadata, mediaBody = self.getUpData(filePath, isResumable=True)
        fileMetadata['parents'] = [parentFolderId]
        fileOp = self.service.files().create(supportsAllDrives=True, body=fileMetadata, media_body=mediaBody)
        upResponse = None
        while not upResponse:
            upStatus, upResponse = fileOp.next_chunk()
        return upResponse['id']

    def uploadFolder(self, folderPath: str, parentFolderId: str) -> str:
        folderName = folderPath.split('/')[-1]
        folderId = self.createFolder(folderName, parentFolderId)
        folderContents = os.listdir(folderPath)
        if len(folderContents) != 0:
            for contentName in folderContents:
                contentPath = os.path.join(folderPath, contentName)
                if os.path.isdir(contentPath):
                    self.uploadFolder(contentPath, folderId)
                if os.path.isfile(contentPath):
                    self.uploadFile(contentPath, folderId)
        return folderId

    def cloneFile(self, sourceFileId: str, parentFolderId: str) -> str:
        fileMetadata = {'parents': [parentFolderId]}
        return self.service.files().copy(supportsAllDrives=True, fileId=sourceFileId, body=fileMetadata).execute()['id']

    def cloneFolder(self, sourceFolderId: str, parentFolderId: str) -> str:
        sourceFolderName = self.getMetadataById(sourceFolderId, 'name')
        folderId = self.createFolder(sourceFolderName, parentFolderId)
        folderContents = self.getFolderContentsById(sourceFolderId)
        if len(folderContents) != 0:
            for content in folderContents:
                if content.get('mimeType') == self.googleDriveFolderMimeType:
                    self.cloneFolder(content.get('id'), folderId)
                else:
                    self.cloneFile(content.get('id'), folderId)
        return folderId

    def downloadFile(self, sourceFileId: str, dlPath: str) -> None:
        fileName = self.getMetadataById(sourceFileId, 'name')
        filePath = os.path.join(dlPath, fileName)
        downStatus: googleapiclient.http.MediaDownloadProgress
        fileOp = googleapiclient.http.MediaIoBaseDownload(fd=open(filePath, 'wb'), chunksize=self.chunkSize,
                                                          request=self.service.files().get_media(fileId=sourceFileId,
                                                                                                 supportsAllDrives=True))
        downResponse = None
        while not downResponse:
            downStatus, downResponse = fileOp.next_chunk()
        return

    def downloadFolder(self, sourceFolderId: str, dlPath: str) -> None:
        folderName = self.getMetadataById(sourceFolderId, 'name')
        folderPath = os.path.join(dlPath, folderName)
        os.mkdir(folderPath)
        folderContents = self.getFolderContentsById(sourceFolderId)
        if len(folderContents) != 0:
            for content in folderContents:
                if content.get('mimeType') == self.googleDriveFolderMimeType:
                    self.downloadFolder(content.get('id'), folderPath)
                else:
                    self.downloadFile(content.get('id'), folderPath)
        return

    def createFolder(self, folderName: str, parentFolderId: str) -> str:
        folderMetadata = {'name': folderName, 'parents': [parentFolderId], 'mimeType': self.googleDriveFolderMimeType}
        folderOp = self.service.files().create(supportsAllDrives=True, body=folderMetadata).execute()
        return folderOp['id']

    def deleteByUrl(self, url: str) -> str:
        contentId = self.getIdFromUrl(url)
        if contentId != '':
            self.service.files().delete(fileId=contentId, supportsAllDrives=True).execute()
            return f'Deleted: [{url}]'
        return 'Not a Valid Google Drive Link !'

    @staticmethod
    def getIdFromUrl(url: str) -> str:
        if 'folders' in url or 'file' in url:
            return re.search(UrlRegex.googleDrive, url).group(5)
        return ''

    def getUpData(self, filePath: str, isResumable: bool) -> (str, str, typing.Dict, googleapiclient.http.MediaIoBaseUpload):
        fileName = filePath.split('/')[-1]
        fileMimeType = magic.Magic(mime=True).from_file(filePath)
        fileMetadata = {'name': fileName, 'mimeType': fileMimeType}
        if isResumable:
            mediaBody = googleapiclient.http.MediaIoBaseUpload(fd=open(filePath, 'rb'), mimetype=fileMimeType,
                                                               resumable=True, chunksize=self.chunkSize)
        else:
            mediaBody = googleapiclient.http.MediaIoBaseUpload(fd=open(filePath, 'rb'), mimetype=fileMimeType,
                                                               resumable=False)
        return fileName, fileMimeType, fileMetadata, mediaBody

    def getMetadataById(self, sourceId: str, field: str) -> str:
        return self.service.files().get(supportsAllDrives=True, fileId=sourceId, fields=field).execute().get(field)

    def getFolderContentsById(self, folderId: str) -> typing.List:
        query = f"'{folderId}' in parents"
        pageToken = None
        folderContents: typing.List = []
        while True:
            result = self.service.files().list(supportsAllDrives=True, includeTeamDriveItems=True, spaces='drive',
                                               fields='nextPageToken, files(name, id, mimeType, size)',
                                               q=query, pageSize=200, pageToken=pageToken).execute()
            for content in result.get('files', []):
                folderContents.append(content)
            pageToken = result.get('nextPageToken', None)
            if not pageToken:
                break
        return folderContents

    def getSizeById(self, sourceId: str) -> int:
        totalSize: int = 0
        if self.getMetadataById(sourceId, 'mimeType') == self.googleDriveFolderMimeType:
            folderContents = self.getFolderContentsById(sourceId)
            if len(folderContents) != 0:
                for content in folderContents:
                    if content.get('mimeType') == self.googleDriveFolderMimeType:
                        totalSize += self.getSizeById(content.get('id'))
                    else:
                        totalSize += int(content.get('size'))
        else:
            totalSize = int(self.getMetadataById(sourceId, 'size'))
        return totalSize

    def patchFile(self, filePath: str, fileId: str) -> str:
        fileName, fileMimeType, fileMetadata, mediaBody = self.getUpData(filePath, isResumable=False)
        fileOp = self.service.files().update(fileId=fileId, body=fileMetadata, media_body=mediaBody).execute()
        return f"Patched: [{fileOp['id']}] [{fileName}] [{os.path.getsize(fileName)} bytes]"


class MegaHelper(BaseHelper):
    def __init__(self, botHelper: BotHelper):
        super().__init__(botHelper)
        self.apiHelper = MegaApiHelper(self.botHelper)

    # TODO: check and set flag if megaAuth is empty
    def initHelper(self) -> None:
        super().initHelper()
        self.initSubHelpers()

    def initSubHelpers(self) -> None:
        self.apiHelper.initHelper()

    def addListener(self) -> None:
        self.apiHelper.api.addListener(self.apiHelper.listener)

    def authorizeApi(self) -> None:
        self.apiHelper.login()
        self.apiHelper.whoami()

    def unauthorizeApi(self) -> None:
        self.apiHelper.logout()

    def addDownload(self, mirrorInfo: 'MirrorInfo') -> None:
        self.apiHelper.getNode(mirrorInfo.downloadUrl)
        self.apiHelper.downloadNode(self.apiHelper.listener.publicNode, mirrorInfo.path)
        self.botHelper.mirrorListenerHelper.updateStatus(mirrorInfo.uid, MirrorStatus.downloadComplete)

    def cancelDownload(self, uid: str) -> None:
        raise NotImplementedError

    def addUpload(self, mirrorInfo: 'MirrorInfo') -> None:
        raise NotImplementedError

    def cancelUpload(self, uid: str) -> None:
        raise NotImplementedError


class TelegramHelper(BaseHelper):
    def __init__(self, botHelper: BotHelper):
        super().__init__(botHelper)

    def initHelper(self) -> None:
        super().initHelper()
        self.uploadMaxSize: int = 2 * 1024 * 1024 * 1024
        self.maxTimeout: int = 24 * 60 * 60

    def addDownload(self, mirrorInfo: 'MirrorInfo') -> None:
        replyTo = mirrorInfo.msg.reply_to_message
        for media in [replyTo.document, replyTo.audio, replyTo.video]:
            if media:
                self.botHelper.mirrorHelper.mirrorInfos[mirrorInfo.uid].updateVars({mirrorInfo.updatableVars[0]: media.file_size})
                self.downloadMedia(media, mirrorInfo.path)
                break
        self.botHelper.mirrorListenerHelper.updateStatus(mirrorInfo.uid, MirrorStatus.downloadComplete)

    def cancelDownload(self, uid: str) -> None:
        raise NotImplementedError

    def addUpload(self, mirrorInfo: 'MirrorInfo') -> None:
        uploadPath = os.path.join(mirrorInfo.path, os.listdir(mirrorInfo.path)[0])
        upResponse: bool = True
        if os.path.isfile(uploadPath):
            if not self.uploadFile(uploadPath, mirrorInfo.chatId, mirrorInfo.msgId):
                upResponse = False
                self.botHelper.bot.sendMessage(text='Files Larger Than 2GB Cannot Be Uploaded Yet !', parse_mode='HTML',
                                                            chat_id=mirrorInfo.chatId, reply_to_message_id=mirrorInfo.msgId)
        if os.path.isdir(uploadPath):
            if not self.uploadFolder(uploadPath, mirrorInfo.chatId, mirrorInfo.msgId):
                upResponse = False
        if upResponse:
            self.botHelper.mirrorListenerHelper.updateStatus(mirrorInfo.uid, MirrorStatus.uploadComplete)
        if not upResponse:
            self.botHelper.mirrorListenerHelper.updateStatus(mirrorInfo.uid, MirrorStatus.cancelMirror)

    def cancelUpload(self, uid: str) -> None:
        raise NotImplementedError

    def downloadMedia(self, media: typing.Union[telegram.Document, telegram.Audio, telegram.Video], mirrorInfoPath: str) -> None:
        shutil.move(src=media.get_file(timeout=self.maxTimeout).file_path,
                    dst=os.path.join(mirrorInfoPath, media.file_name))

    def uploadFile(self, filePath: str, chatId: int, msgId: int) -> bool:
        if os.path.getsize(filePath) < self.uploadMaxSize:
            self.botHelper.bot.sendDocument(document=f'file://{filePath}', filename=filePath.split('/')[-1],
                                            chat_id=chatId, reply_to_message_id=msgId, timeout=self.maxTimeout)
            return True
        return False

    def uploadFolder(self, folderPath: str, chatId: int, msgId: int) -> bool:
        folderContents = os.listdir(folderPath)
        skippedContents: [str] = []
        if len(folderContents) != 0:
            for contentName in folderContents:
                contentPath = os.path.join(folderPath, contentName)
                if os.path.isdir(contentPath):
                    self.uploadFolder(contentPath, chatId, msgId)
                if os.path.isfile(contentPath):
                    if not self.uploadFile(contentPath, chatId, msgId):
                        skippedContents.append(contentPath)
        if skippedContents:
            skippedContentsMsg = 'Skipped Files Due to uploadMaxSize:\n'
            for content in skippedContents:
                skippedContentsMsg += f'{content}\n'
            self.botHelper.bot.sendMessage(text=skippedContentsMsg, parse_mode='HTML',
                                           chat_id=chatId, reply_to_message_id=msgId)
        return True


class YouTubeHelper(BaseHelper):
    def __init__(self, botHelper: BotHelper):
        super().__init__(botHelper)

    def initHelper(self) -> None:
        super().initHelper()

    def addDownload(self, mirrorInfo: 'MirrorInfo') -> None:
        ytdlOpts: dict = {'format': 'best/bestvideo+bestaudio', 'logger': self.logger,
                          'outtmpl': f'{mirrorInfo.path}/%(title)s-%(id)s.f%(format_id)s.%(ext)s'}
        self.downloadVideo(mirrorInfo.downloadUrl, ytdlOpts)
        self.botHelper.mirrorListenerHelper.updateStatus(mirrorInfo.uid, MirrorStatus.downloadComplete)

    def cancelDownload(self, uid: str) -> None:
        raise NotImplementedError

    @staticmethod
    def downloadVideo(videoUrl: str, ytdlOpts: dict) -> None:
        with youtube_dl.YoutubeDL(ytdlOpts) as ytdl:
            ytdl.download([videoUrl])


class CompressionHelper(BaseHelper):
    def __init__(self, botHelper: BotHelper):
        super().__init__(botHelper)

    def initHelper(self) -> None:
        super().initHelper()

    def addCompression(self, mirrorInfo: 'MirrorInfo') -> None:
        self.compressSource(os.path.join(mirrorInfo.path, os.listdir(mirrorInfo.path)[0]))
        self.botHelper.mirrorListenerHelper.updateStatus(mirrorInfo.uid, MirrorStatus.compressionComplete)

    def cancelCompression(self, uid: str) -> None:
        raise NotImplementedError

    def compressSource(self, sourcePath: str) -> None:
        archiveFormat = list(self.botHelper.mirrorHelper.supportedArchiveFormats.keys())[3]
        sourceTempPath = sourcePath + 'temp'
        sourceName = sourcePath.split('/')[-1]
        os.mkdir(sourceTempPath)
        shutil.move(src=sourcePath, dst=os.path.join(sourceTempPath, sourceName))
        shutil.move(src=sourceTempPath, dst=sourcePath)
        shutil.make_archive(sourcePath, archiveFormat, sourcePath)
        shutil.rmtree(sourcePath) if os.path.isdir(sourcePath) else os.remove(sourcePath)


class DecompressionHelper(BaseHelper):
    def __init__(self, botHelper: BotHelper):
        super().__init__(botHelper)

    def initHelper(self) -> None:
        super().initHelper()

    def addDecompression(self, mirrorInfo: 'MirrorInfo') -> None:
        self.decompressArchive(os.path.join(mirrorInfo.path, os.listdir(mirrorInfo.path)[0]))
        self.botHelper.mirrorListenerHelper.updateStatus(mirrorInfo.uid, MirrorStatus.decompressionComplete)

    def cancelDecompression(self, uid: str) -> None:
        raise NotImplementedError

    def decompressArchive(self, archivePath: str) -> None:
        archiveFormat = ''
        for archiveFileExtension in self.botHelper.mirrorHelper.supportedArchiveFormats.values():
            if archivePath.endswith(archiveFileExtension):
                for archiveFileFormat in self.botHelper.mirrorHelper.supportedArchiveFormats.keys():
                    if self.botHelper.mirrorHelper.supportedArchiveFormats[archiveFileFormat] == archiveFileExtension:
                        archiveFormat = archiveFileFormat
                        break
                break
        if archiveFormat == '':
            return
        folderPath = archivePath.replace(self.botHelper.mirrorHelper.supportedArchiveFormats[archiveFormat], '')
        shutil.unpack_archive(archivePath, folderPath, archiveFormat)
        os.remove(archivePath)


class StatusHelper(BaseHelper):
    def __init__(self, botHelper: BotHelper):
        super().__init__(botHelper)

    def initHelper(self) -> None:
        super().initHelper()
        self.updaterLock = threading.Lock()
        self.isInitThread: bool = False
        self.isUpdateStatus: bool = False
        self.statusUpdateInterval: int = int(self.botHelper.configHelper.configVars[self.botHelper.configHelper.optVars[5]])
        self.msgId: int = 0
        self.chatId: int = 0
        self.lastStatusMsgId: int = 0
        self.lastStatusMsgTxt: str = ''

    def addStatus(self, chatId: int, msgId: int) -> None:
        with self.updaterLock:
            if self.botHelper.mirrorHelper.mirrorInfos != {}:
                self.isUpdateStatus = True
            else:
                self.isUpdateStatus = False
            if self.lastStatusMsgId == 0:
                self.isInitThread = True
            if self.lastStatusMsgId != 0:
                self.botHelper.bot.deleteMessage(chat_id=self.chatId, message_id=self.lastStatusMsgId)
            self.chatId = chatId
            self.msgId = msgId
            self.lastStatusMsgId = self.botHelper.bot.sendMessage(text='...', parse_mode='HTML', chat_id=self.chatId,
                                                                  reply_to_message_id=self.msgId).message_id
            if self.isInitThread:
                self.isInitThread = False
                self.botHelper.threadingHelper.initThread(target=self.updateStatusMsg, name='statusUpdaterStart')

    def getStatusMsgTxt(self) -> str:
        statusMsgTxt = ''
        for uid in self.botHelper.mirrorHelper.mirrorInfos.keys():
            mirrorInfo: MirrorInfo = self.botHelper.mirrorHelper.mirrorInfos[uid]
            statusMsgTxt += f'{mirrorInfo.uid} | {mirrorInfo.status}\n'
            if mirrorInfo.status == MirrorStatus.downloadProgress and mirrorInfo.isAriaDownload:
                if mirrorInfo.uid in self.botHelper.ariaHelper.gids.keys():
                    self.botHelper.ariaHelper.updateProgress(mirrorInfo.uid)
                    statusMsgTxt += f'S: {self.botHelper.getHelper.readableSize(mirrorInfo.sizeCurrent)} | ' \
                                    f'{self.botHelper.getHelper.readableSize(mirrorInfo.sizeTotal)} | ' \
                                    f'{self.botHelper.getHelper.readableSize(mirrorInfo.sizeTotal - mirrorInfo.sizeCurrent)}\n' \
                                    f'P: {self.botHelper.getHelper.progressBar(mirrorInfo.progressPercent)} | ' \
                                    f'{mirrorInfo.progressPercent}% | ' \
                                    f'{self.botHelper.getHelper.readableSize(mirrorInfo.speedCurrent)}/s\n' \
                                    f'T: {self.botHelper.getHelper.readableTime(mirrorInfo.timeCurrent - mirrorInfo.timeStart)} | ' \
                                    f'{self.botHelper.getHelper.readableTime(mirrorInfo.timeEnd - mirrorInfo.timeCurrent)}\n'
                    if mirrorInfo.isTorrent:
                        statusMsgTxt += f'nS: {mirrorInfo.numSeeders} nL: {mirrorInfo.numLeechers}\n'
        return statusMsgTxt

    def updateStatusMsg(self) -> None:
        with self.updaterLock:
            if self.isUpdateStatus:
                if self.botHelper.mirrorHelper.mirrorInfos:
                    statusMsgTxt = self.getStatusMsgTxt()
                    if statusMsgTxt != self.lastStatusMsgTxt:
                        self.botHelper.bot.editMessageText(text=statusMsgTxt, parse_mode='HTML', chat_id=self.chatId,
                                                           message_id=self.lastStatusMsgId)
                        self.lastStatusMsgTxt = statusMsgTxt
                        time.sleep(self.statusUpdateInterval - 1)
                    time.sleep(1)
                    self.botHelper.threadingHelper.initThread(target=self.updateStatusMsg, name='statusUpdaterContinue')
                    return
                if not self.botHelper.mirrorHelper.mirrorInfos:
                    self.isUpdateStatus = False
                    self.botHelper.threadingHelper.initThread(target=self.updateStatusMsg, name='statusUpdaterEnd')
                    return
            if not self.isUpdateStatus:
                self.botHelper.bot.editMessageText(text='No Active Downloads !', parse_mode='HTML',
                                                                chat_id=self.chatId, message_id=self.lastStatusMsgId)
                self.resetAllDat()

    def resetAllDat(self) -> None:
        self.isInitThread = False
        self.isUpdateStatus = False
        self.msgId = 0
        self.chatId = 0
        self.lastStatusMsgId = 0
        self.lastStatusMsgTxt = ''


class MirrorListenerHelper(BaseHelper):
    def __init__(self, botHelper: BotHelper):
        super().__init__(botHelper)

    def initHelper(self) -> None:
        super().initHelper()
        self.webhookServer: WebhookServer
        self.downloadQueueSize: int = 3
        self.downloadQueueActive: int = 0
        self.downloadQueue: typing.List[str] = []
        self.compressionQueueSize: int = 1
        self.compressionQueueActive: int = 0
        self.compressionQueue: typing.List[str] = []
        self.decompressionQueueSize: int = 1
        self.decompressionQueueActive: int = 0
        self.decompressionQueue: typing.List[str] = []
        self.uploadQueueSize: int = 3
        self.uploadQueueActive: int = 0
        self.uploadQueue: typing.List[str] = []
        self.statusCallBacks: typing.Dict[str, typing.Callable] \
            = {MirrorStatus.addMirror: self.onAddMirror,
               MirrorStatus.cancelMirror: self.onCancelMirror,
               MirrorStatus.completeMirror: self.onCompleteMirror,
               MirrorStatus.downloadQueue: self.onDownloadQueue,
               MirrorStatus.downloadStart: self.onDownloadStart,
               MirrorStatus.downloadProgress: self.onDownloadProgress,
               MirrorStatus.downloadComplete: self.onDownloadComplete,
               MirrorStatus.downloadError: self.onDownloadError,
               MirrorStatus.compressionQueue: self.onCompressionQueue,
               MirrorStatus.compressionStart: self.onCompressionStart,
               MirrorStatus.compressionProgress: self.onCompressionProgress,
               MirrorStatus.compressionComplete: self.onCompressionComplete,
               MirrorStatus.compressionError: self.onCompressionError,
               MirrorStatus.decompressionQueue: self.onDecompressionQueue,
               MirrorStatus.decompressionStart: self.onDecompressionStart,
               MirrorStatus.decompressionProgress: self.onDecompressionProgress,
               MirrorStatus.decompressionComplete: self.onDecompressionComplete,
               MirrorStatus.decompressionError: self.onDecompressionError,
               MirrorStatus.uploadQueue: self.onUploadQueue,
               MirrorStatus.uploadStart: self.onUploadStart,
               MirrorStatus.uploadProgress: self.onUploadProgress,
               MirrorStatus.uploadComplete: self.onUploadComplete,
               MirrorStatus.uploadError: self.onUploadError}

    def startWebhookServer(self, ready=None, forceEventLoop=False) -> None:
        self.webhookServer = WebhookServer(self.botHelper)
        self.botHelper.threadingHelper.initThread(target=self.webhookServer.serveForever, name='MirrorListenerHelper.webhookServer',
                                                  forceEventLoop=forceEventLoop, ready=ready)

    def stopWebhookServer(self) -> None:
        if self.webhookServer:
            self.webhookServer.shutdown()
            self.webhookServer = None

    def updateStatus(self, uid: str, mirrorStatus: str) -> None:
        self.botHelper.mirrorHelper.mirrorInfos[uid].status = mirrorStatus
        data = {'mirrorUid': uid, 'mirrorStatus': mirrorStatus}
        headers = {'Content-Type': 'application/json'}
        requests.post(url=self.webhookServer.webhookUrl, data=json.dumps(data), headers=headers)

    def updateStatusCallback(self, uid: str) -> None:
        mirrorInfo: MirrorInfo = self.botHelper.mirrorHelper.mirrorInfos[uid]
        self.logger.info(f'{mirrorInfo.uid} : {mirrorInfo.status}')
        self.statusCallBacks[mirrorInfo.status](mirrorInfo)

    def onAddMirror(self, mirrorInfo: 'MirrorInfo') -> None:
        self.downloadQueue.append(mirrorInfo.uid)
        self.updateStatus(mirrorInfo.uid, MirrorStatus.downloadQueue)

    # TODO: improve method and maybe not use onCancelMirror callback in operationErrors and improve onOperationErrors
    def onCancelMirror(self, mirrorInfo: 'MirrorInfo') -> None:
        # TODO: implement cancel callbacks for various download and upload types
        shutil.rmtree(mirrorInfo.path)
        self.botHelper.mirrorHelper.mirrorInfos.pop(mirrorInfo.uid)

    def onCompleteMirror(self, mirrorInfo: 'MirrorInfo') -> None:
        shutil.rmtree(mirrorInfo.path)
        self.botHelper.mirrorHelper.mirrorInfos.pop(mirrorInfo.uid)
        if mirrorInfo.isGoogleDriveUpload or mirrorInfo.isMegaUpload:
            self.botHelper.bot.sendMessage(text=f'Uploaded: [{mirrorInfo.uid}] [{mirrorInfo.uploadUrl}]',
                                                                  parse_mode='HTML', chat_id=mirrorInfo.chatId, reply_to_message_id=mirrorInfo.msgId)

    def onDownloadQueue(self, mirrorInfo: 'MirrorInfo') -> None:
        self.resetMirrorProgress(mirrorInfo.uid)
        self.checkDownloadQueue()

    def checkDownloadQueue(self) -> None:
        if self.downloadQueueSize > self.downloadQueueActive < len(self.downloadQueue):
            self.updateStatus(self.downloadQueue[self.downloadQueueActive], MirrorStatus.downloadStart)
            self.downloadQueueActive += 1
            self.checkDownloadQueue()

    def onDownloadStart(self, mirrorInfo: 'MirrorInfo') -> None:
        os.mkdir(mirrorInfo.path)
        if mirrorInfo.isAriaDownload:
            self.botHelper.threadingHelper.initThread(target=self.botHelper.ariaHelper.addDownload,
                                                      name=f'{mirrorInfo.uid}-AriaDownload', mirrorInfo=mirrorInfo)
        if mirrorInfo.isGoogleDriveDownload:
            self.botHelper.threadingHelper.initThread(target=self.botHelper.googleDriveHelper.addDownload,
                                                      name=f'{mirrorInfo.uid}-GoogleDriveDownload', mirrorInfo=mirrorInfo)
        if mirrorInfo.isMegaDownload:
            self.botHelper.threadingHelper.initThread(target=self.botHelper.megaHelper.addDownload,
                                                      name=f'{mirrorInfo.uid}-MegaDownload', mirrorInfo=mirrorInfo)
        if mirrorInfo.isTelegramDownload:
            self.botHelper.threadingHelper.initThread(target=self.botHelper.telegramHelper.addDownload,
                                                      name=f'{mirrorInfo.uid}-TelegramDownload', mirrorInfo=mirrorInfo)
        if mirrorInfo.isYouTubeDownload:
            self.botHelper.threadingHelper.initThread(target=self.botHelper.youTubeHelper.addDownload,
                                                      name=f'{mirrorInfo.uid}-YouTubeDownload', mirrorInfo=mirrorInfo)
        self.updateStatus(mirrorInfo.uid, MirrorStatus.downloadProgress)

    def onDownloadProgress(self, mirrorInfo: 'MirrorInfo') -> None:
        pass

    def onDownloadComplete(self, mirrorInfo: 'MirrorInfo') -> None:
        self.downloadQueue.remove(mirrorInfo.uid)
        self.downloadQueueActive -= 1
        self.compressionQueue.append(mirrorInfo.uid)
        self.updateStatus(mirrorInfo.uid, MirrorStatus.compressionQueue)
        self.checkDownloadQueue()

    def onDownloadError(self, mirrorInfo: 'MirrorInfo') -> None:
        self.downloadQueue.remove(mirrorInfo.uid)
        self.downloadQueueActive -= 1
        self.updateStatus(mirrorInfo.uid, MirrorStatus.cancelMirror)
        self.checkDownloadQueue()

    def onCompressionQueue(self, mirrorInfo: 'MirrorInfo') -> None:
        if not mirrorInfo.isCompress:
            self.compressionQueue.remove(mirrorInfo.uid)
            self.decompressionQueue.append(mirrorInfo.uid)
            self.updateStatus(mirrorInfo.uid, MirrorStatus.decompressionQueue)
            return
        self.resetMirrorProgress(mirrorInfo.uid)
        self.checkCompressionQueue()

    def checkCompressionQueue(self) -> None:
        if self.compressionQueueSize > self.compressionQueueActive < len(self.compressionQueue):
            self.updateStatus(self.compressionQueue[self.compressionQueueActive], MirrorStatus.compressionStart)
            self.compressionQueueActive += 1
            self.checkCompressionQueue()

    def onCompressionStart(self, mirrorInfo: 'MirrorInfo') -> None:
        self.botHelper.threadingHelper.initThread(target=self.botHelper.compressionHelper.addCompression,
                                                  name=f'{mirrorInfo.uid}-Compression', mirrorInfo=mirrorInfo)
        self.updateStatus(mirrorInfo.uid, MirrorStatus.compressionProgress)

    def onCompressionProgress(self, mirrorInfo: 'MirrorInfo') -> None:
        pass

    def onCompressionComplete(self, mirrorInfo: 'MirrorInfo') -> None:
        self.compressionQueue.remove(mirrorInfo.uid)
        self.compressionQueueActive -= 1
        self.decompressionQueue.append(mirrorInfo.uid)
        self.updateStatus(mirrorInfo.uid, MirrorStatus.decompressionQueue)
        self.checkCompressionQueue()

    def onCompressionError(self, mirrorInfo: 'MirrorInfo') -> None:
        self.compressionQueue.remove(mirrorInfo.uid)
        self.compressionQueueActive -= 1
        self.updateStatus(mirrorInfo.uid, MirrorStatus.cancelMirror)
        self.checkCompressionQueue()

    def onDecompressionQueue(self, mirrorInfo: 'MirrorInfo') -> None:
        if not mirrorInfo.isDecompress:
            self.decompressionQueue.remove(mirrorInfo.uid)
            self.uploadQueue.append(mirrorInfo.uid)
            self.updateStatus(mirrorInfo.uid, MirrorStatus.uploadQueue)
            return
        self.resetMirrorProgress(mirrorInfo.uid)
        self.checkDecompressionQueue()

    def checkDecompressionQueue(self) -> None:
        if self.decompressionQueueSize > self.decompressionQueueActive < len(self.decompressionQueue):
            self.updateStatus(self.decompressionQueue[self.decompressionQueueActive], MirrorStatus.decompressionStart)
            self.decompressionQueueActive += 1
            self.checkDecompressionQueue()

    def onDecompressionStart(self, mirrorInfo: 'MirrorInfo') -> None:
        self.botHelper.threadingHelper.initThread(target=self.botHelper.decompressionHelper.addDecompression,
                                                  name=f'{mirrorInfo.uid}-Decompression', mirrorInfo=mirrorInfo)
        self.updateStatus(mirrorInfo.uid, MirrorStatus.decompressionProgress)

    def onDecompressionProgress(self, mirrorInfo: 'MirrorInfo') -> None:
        pass

    def onDecompressionComplete(self, mirrorInfo: 'MirrorInfo') -> None:
        self.decompressionQueue.remove(mirrorInfo.uid)
        self.decompressionQueueActive -= 1
        self.uploadQueue.append(mirrorInfo.uid)
        self.updateStatus(mirrorInfo.uid, MirrorStatus.uploadQueue)
        self.checkDecompressionQueue()

    def onDecompressionError(self, mirrorInfo: 'MirrorInfo') -> None:
        self.decompressionQueue.remove(mirrorInfo.uid)
        self.decompressionQueueActive -= 1
        self.updateStatus(mirrorInfo.uid, MirrorStatus.cancelMirror)
        self.checkDecompressionQueue()

    def onUploadQueue(self, mirrorInfo: 'MirrorInfo') -> None:
        self.resetMirrorProgress(mirrorInfo.uid)
        self.checkUploadQueue()

    def checkUploadQueue(self) -> None:
        if self.uploadQueueSize > self.uploadQueueActive < len(self.uploadQueue):
            self.updateStatus(self.uploadQueue[self.uploadQueueActive], MirrorStatus.uploadStart)
            self.uploadQueueActive += 1
            self.checkUploadQueue()

    def onUploadStart(self, mirrorInfo: 'MirrorInfo') -> None:
        if mirrorInfo.isGoogleDriveUpload:
            self.botHelper.threadingHelper.initThread(target=self.botHelper.googleDriveHelper.addUpload,
                                                      name=f'{mirrorInfo.uid}-GoogleDriveUpload', mirrorInfo=mirrorInfo)
        if mirrorInfo.isMegaUpload:
            self.botHelper.threadingHelper.initThread(target=self.botHelper.megaHelper.addUpload,
                                                      name=f'{mirrorInfo.uid}-MegaUpload', mirrorInfo=mirrorInfo)
        if mirrorInfo.isTelegramUpload:
            self.botHelper.threadingHelper.initThread(target=self.botHelper.telegramHelper.addUpload,
                                                      name=f'{mirrorInfo.uid}-TelegramUpload', mirrorInfo=mirrorInfo)
        self.updateStatus(mirrorInfo.uid, MirrorStatus.uploadProgress)

    def onUploadProgress(self, mirrorInfo: 'MirrorInfo') -> None:
        pass

    def onUploadComplete(self, mirrorInfo: 'MirrorInfo') -> None:
        self.uploadQueue.remove(mirrorInfo.uid)
        self.uploadQueueActive -= 1
        self.updateStatus(mirrorInfo.uid, MirrorStatus.completeMirror)
        self.checkUploadQueue()

    def onUploadError(self, mirrorInfo: 'MirrorInfo') -> None:
        self.uploadQueue.remove(mirrorInfo.uid)
        self.uploadQueueActive -= 1
        self.updateStatus(mirrorInfo.uid, MirrorStatus.cancelMirror)
        self.checkUploadQueue()

    def resetMirrorProgress(self, uid: str) -> None:
        self.botHelper.mirrorHelper.mirrorInfos[uid].timeEnd = 0
        self.botHelper.mirrorHelper.mirrorInfos[uid].progressPercent = 0


class MegaApiHelper(BaseHelper):
    def __init__(self, botHelper: BotHelper):
        super().__init__(botHelper)

    def initHelper(self) -> None:
        self.api = mega.MegaApi(self.botHelper.configHelper.configVars[self.botHelper.configHelper.optVars[4]]['apiKey'], None, None, 'tgmb-beta')
        self.executor = MegaAsyncExecutor(self)
        self.listener = MegaApiListener(self)
        self.cloudDriveNode: mega.MegaNode
        self.currWorkDir: mega.MegaNode
        super().initHelper()

    def cd(self, dirName: str, rootNode: mega.MegaNode):
        self.logger.debug('*** start: cd ***')
        dirNode = self.api.getNodeByPath(dirName, rootNode)
        if dirNode is None:
            self.logger.warning(f"No Such Directory: '{dirName}'")
        elif dirNode.getType() == mega.MegaNode.TYPE_FOLDER:
            self.logger.debug(f"cd '{dirName}' in '{rootNode.getName()}'")
            self.currWorkDir = dirNode
        else:
            self.logger.warning(f"Not a Directory: '{dirName}'")
        self.logger.debug('*** done: cd ***')

    def delete(self, sourceName: str, rootNode: mega.MegaNode):
        self.logger.debug('*** start: delete ***')
        sourceNode = self.api.getNodeByPath(sourceName, rootNode)
        if sourceNode is not None:
            self.logger.debug(f"delete '{sourceName}' in '{rootNode.getName()}'")
            self.executor.do(self.api.remove, (sourceNode,))
        else:
            self.logger.warning(f"Node not found: '{sourceName}'")
        self.logger.debug('*** done: delete ***')

    def download(self, fileName: str, rootNode: mega.MegaNode):
        self.logger.debug('*** start: download ***')
        fileNode = self.api.getNodeByPath(fileName, rootNode)
        if fileNode is not None:
            self.logger.debug(f"download '{fileName}' in '{rootNode.getName()}'")
            self.executor.do(self.api.startDownload, (fileNode, fileNode.getName()))
        else:
            self.logger.warning(f"Node Not Found: {fileName}")
        self.logger.debug('*** done: download ***')

    def downloadNode(self, node: mega.MegaNode, dlPath: str):
        self.logger.debug('*** start: download node ***')
        self.executor.do(self.api.startDownload, (node, os.path.join(dlPath, node.getName())))
        self.logger.debug('*** done: download node ***')

    def getNode(self, nodeLink: str):
        self.logger.debug('*** start: get node ***')
        self.executor.do(self.api.getPublicNode, (nodeLink,))
        self.logger.debug('*** done: get node ***')

    def login(self):
        self.logger.debug('*** start: login ***')
        self.executor.do(self.api.login, (self.botHelper.configHelper.configVars[self.botHelper.configHelper.optVars[4]]['emailId'],
                                          self.botHelper.configHelper.configVars[self.botHelper.configHelper.optVars[4]]['passPhrase']))
        self.cloudDriveNode = self.listener.rootNode
        self.currWorkDir = self.cloudDriveNode
        self.logger.debug('*** done: login ***')

    def logout(self):
        self.logger.debug('*** start: logout ***')
        self.executor.do(self.api.logout, ())
        self.listener.rootNode = None
        self.logger.debug('*** done: logout ***')

    def mkdir(self, dirName: str, rootNode: mega.MegaNode):
        self.logger.debug('*** start: mkdir ***')
        checkDirNodeExists = self.api.getNodeByPath(dirName, rootNode)
        if checkDirNodeExists is None:
            self.logger.debug(f"mkdir '{dirName}' in '{rootNode.getName()}'")
            self.executor.do(self.api.createFolder, (dirName, rootNode))
        else:
            self.logger.debug(f'Path already exists: {self.api.getNodePath(checkDirNodeExists)}')
        self.logger.debug('*** done: mkdir ***')

    def update(self, fileName: str, rootNode: mega.MegaNode):
        self.logger.debug('*** start: update ***')
        self.logger.debug(f"update '{fileName}' in '{rootNode.getName()}'")
        oldNode = self.api.getNodeByPath(fileName, rootNode)
        self.executor.do(self.api.startUpload, (fileName, rootNode))
        if oldNode is not None:
            self.executor.do(self.api.remove, (oldNode,))
        else:
            self.logger.debug('No Old File Needs Removing')
        self.logger.debug('*** done: update ***')

    def upload(self, fileName: str, rootNode: mega.MegaNode):
        self.logger.debug('*** start: upload ***')
        self.logger.debug(f"upload '{fileName}' in '{rootNode.getName()}'")
        self.executor.do(self.api.startUpload, (fileName, rootNode))
        self.logger.debug('*** done: upload ***')

    def whoami(self):
        self.logger.debug('*** start: whoami ***')
        self.logger.debug(f'My email: {self.api.getMyEmail()}')
        self.executor.do(self.api.getAccountDetails, ())
        self.logger.debug('*** done: whoami ***')


class MegaApiListener(mega.MegaListener):
    _NO_EVENT_ON = (mega.MegaRequest.TYPE_LOGIN, mega.MegaRequest.TYPE_FETCH_NODES)

    def __init__(self, apiHelper: MegaApiHelper):
        self.apiHelper = apiHelper
        self.logger = self.apiHelper.botHelper.loggingHelper.logger.bind(classname=self.__class__.__name__)
        self.rootNode = None
        self.publicNode = None
        super().__init__()

    def onRequestStart(self, api: mega.MegaApi, request: mega.MegaRequest):
        self.logger.debug(f'Request start ({request})')

    def onRequestFinish(self, api: mega.MegaApi, request: mega.MegaRequest, error: mega.MegaError):
        self.logger.debug(f'Request finished ({request}); Result: {error}')
        requestType = request.getType()
        if requestType == mega.MegaRequest.TYPE_LOGIN:
            api.fetchNodes()
        elif requestType == mega.MegaRequest.TYPE_FETCH_NODES:
            self.rootNode = api.getRootNode()
        elif requestType == mega.MegaRequest.TYPE_GET_PUBLIC_NODE:
            self.publicNode = request.getPublicMegaNode()
        elif requestType == mega.MegaRequest.TYPE_ACCOUNT_DETAILS:
            accountDetails = request.getMegaAccountDetails()
            self.logger.debug('Account details received')
            self.logger.debug(f'Storage: {accountDetails.getStorageUsed()} of {accountDetails.getStorageMax()} '
                              f'({(accountDetails.getStorageUsed() / accountDetails.getStorageMax()) * 100} %)')
            self.logger.debug(f'Pro level: {accountDetails.getProLevel()}')
        if requestType not in self._NO_EVENT_ON:
            self.apiHelper.executor.continueEvent.set()

    def onRequestTemporaryError(self, api: mega.MegaApi, request: mega.MegaRequest, error: mega.MegaError):
        self.logger.debug(f'Request temporary error ({request}); Error: {error}')

    def onTransferFinish(self, api: mega.MegaApi, transfer: mega.MegaTransfer, error: mega.MegaError):
        self.logger.debug(f'Transfer finished ({transfer} {transfer.getFileName()}); Result: {error}')
        self.apiHelper.executor.continueEvent.set()

    def onTransferUpdate(self, api: mega.MegaApi, transfer: mega.MegaTransfer):
        self.logger.debug(f'Transfer update ({transfer} {transfer.getFileName()}); '
                          f'Progress: {transfer.getTransferredBytes() / 1024} KB of {transfer.getTotalBytes() / 1024} KB, '
                          f'{transfer.getSpeed() / 1024} KB/s')

    def onTransferTemporaryError(self, api: mega.MegaApi, transfer: mega.MegaTransfer, error: mega.MegaError):
        self.logger.debug(f'Transfer temporary error ({transfer} {transfer.getFileName()}); Error: {error}')

    def onUsersUpdate(self, api: mega.MegaApi, users: mega.MegaUserList):
        if users is not None:
            self.logger.debug(f'Users updated ({users.size()})')

    def onNodesUpdate(self, api: mega.MegaApi, nodes: mega.MegaNodeList):
        if nodes is not None:
            self.logger.debug(f'Nodes updated ({nodes.size()})')
        self.apiHelper.executor.continueEvent.set()


class MegaAsyncExecutor:
    def __init__(self, apiHelper: MegaApiHelper):
        self.apiHelper = apiHelper
        self.continueEvent = threading.Event()

    def do(self, function: typing.Callable, args):
        self.continueEvent.clear()
        function(*args)
        self.continueEvent.wait()


class MirrorInfo:
    updatableVars: typing.List[str] = ['sizeTotal', 'sizeCurrent', 'speedCurrent', 'timeCurrent',
                                       'isTorrent', 'numSeeders', 'numLeechers']

    def __init__(self, msg: telegram.Message, botHelper: BotHelper):
        self.msg = msg
        self.msgId = msg.message_id
        self.chatId = msg.chat.id
        self.uid: str = botHelper.getHelper.randomString(8)
        self.path: str = os.path.join(botHelper.envVars['dlRootDirPath'], self.uid)
        self.status: str = ''
        self.downloadUrl: str = ''
        self.tag: str = ''
        self.timeStart: int = 0
        self.timeCurrent: int = 0
        self.timeEnd: int = 0
        self.speedCurrent: int = 0
        self.sizeTotal: int = 0
        self.sizeCurrent: int = 0
        self.progressPercent: float = 0.0
        self.isTorrent: bool = False
        self.numSeeders: int = 0
        self.numLeechers: int = 0
        self.uploadUrl: str = ''
        self.googleDriveUploadFolderId: str = ''
        self.isAriaDownload: bool = False
        self.isGoogleDriveDownload: bool = False
        self.isMegaDownload: bool = False
        self.isTelegramDownload: bool = False
        self.isYouTubeDownload: bool = False
        self.isGoogleDriveUpload: bool = False
        self.isMegaUpload: bool = False
        self.isTelegramUpload: bool = False
        self.isCompress: bool = False
        self.isDecompress: bool = False

    def updateVars(self, currVars: typing.Dict[str, typing.Union[int, float, str]]) -> None:
        currVarsKeys = list(currVars.keys())
        if self.updatableVars[0] in currVarsKeys:
            self.sizeTotal = currVars[self.updatableVars[0]]
        if self.updatableVars[1] in currVarsKeys and self.updatableVars[2] in currVarsKeys:
            self.sizeCurrent = currVars[self.updatableVars[1]]
            self.speedCurrent = currVars[self.updatableVars[2]]
            self.timeCurrent = currVars[self.updatableVars[3]]
            if self.sizeTotal != 0:
                self.progressPercent = round(((self.sizeCurrent / self.sizeTotal) * 100), ndigits=2)
            if self.speedCurrent != 0:
                self.timeEnd = self.timeCurrent + int((self.sizeTotal - self.sizeCurrent) / self.speedCurrent)
        if self.updatableVars[4] in currVarsKeys:
            self.isTorrent = True
            self.numSeeders = currVars[self.updatableVars[5]]
            self.numLeechers = currVars[self.updatableVars[6]]


class MirrorStatus:
    addMirror = 'addMirror'
    cancelMirror = 'cancelMirror'
    completeMirror = 'completeMirror'
    downloadQueue = 'downloadQueue'
    downloadStart = 'downloadStart'
    downloadProgress = 'downloadProgress'
    downloadComplete = 'downloadComplete'
    downloadError = 'downloadError'
    compressionQueue = 'compressionQueue'
    compressionStart = 'compressionStart'
    compressionProgress = 'compressionProgress'
    compressionComplete = 'compressionComplete'
    compressionError = 'compressionError'
    decompressionQueue = 'decompressionQueue'
    decompressionStart = 'decompressionStart'
    decompressionProgress = 'decompressionProgress'
    decompressionComplete = 'decompressionComplete'
    decompressionError = 'decompressionError'
    uploadQueue = 'uploadQueue'
    uploadStart = 'uploadStart'
    uploadProgress = 'uploadProgress'
    uploadComplete = 'uploadComplete'
    uploadError = 'uploadError'


class UrlRegex:
    generalUrl = r"(?:(?:https?|ftp)://)?[\w/\-?=%.]+\.[\w/\-?=%.]+"
    bittorrentMagnet = r"magnet:\?xt=urn:btih:[a-zA-Z0-9]*"
    googleDrive = r"https://drive\.google\.com/(drive)?/?u?/?\d?/?(mobile)?/?(file)?(folders)?/?d?/([-\w]+)[?+]?/?(w+)?"
    mega = r"((https|http)://)?(www\.)?mega\.nz/[\w\-]+"
    youTube = r"((https|http)://)?((www|m)\.)?(youtube\.com|youtu\.be)/(watch\?v=)?[\w\-]+"


class WebhookServer:
    def __init__(self, botHelper: BotHelper):
        self.botHelper = botHelper
        self.logger = self.botHelper.loggingHelper.logger.bind(classname=self.__class__.__name__)
        self.listenAddress: str = 'localhost'
        self.listenPort: int = 8448
        self.webhookPath: str = 'mirrorListener'
        self.webhookUrl: str = f'http://{self.listenAddress}:{self.listenPort}/{self.webhookPath}'
        self.handlers = [(rf"/{self.webhookPath}/?", WebhookHandler, {'botHelper': self.botHelper})]
        self.webhookApp = WebhookApp(self.handlers)
        self.httpServer = tornado.httpserver.HTTPServer(self.webhookApp)
        self.loop: typing.Optional[tornado.ioloop.IOLoop] = None
        self.isRunning = False
        self.serverLock = threading.Lock()
        self.shutdownLock = threading.Lock()

    def serveForever(self, forceEventLoop: bool = False, ready: threading.Event = None) -> None:
        with self.serverLock:
            self.isRunning = True
            self.logger.debug('Webhook Server started.')
            self.ensureEventLoop(forceEventLoop=forceEventLoop)
            self.loop = tornado.ioloop.IOLoop.current()
            self.httpServer.listen(self.listenPort, address=self.listenAddress)
            if ready is not None:
                ready.set()
            self.loop.start()
            self.logger.debug('Webhook Server stopped.')
            self.isRunning = False

    def shutdown(self) -> None:
        with self.shutdownLock:
            if not self.isRunning:
                self.logger.warning('Webhook Server already stopped.')
                return
            self.loop.add_callback(self.loop.stop)

    def ensureEventLoop(self, forceEventLoop: bool = False) -> None:
        try:
            loop = asyncio.get_event_loop()
            if (not forceEventLoop and os.name == 'nt' and sys.version_info >= (3, 8)
                    and isinstance(loop, asyncio.ProactorEventLoop)):
                raise TypeError('`ProactorEventLoop` is incompatible with Tornado. Please switch to `SelectorEventLoop`.')
        except RuntimeError:
            if (os.name == 'nt' and sys.version_info >= (3, 8) and hasattr(asyncio, 'WindowsProactorEventLoopPolicy')
                    and (isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy))):
                self.logger.debug('Applying Tornado asyncio event loop fix for Python 3.8+ on Windows')
                loop = asyncio.SelectorEventLoop()
            else:
                loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)


class WebhookApp(tornado.web.Application):
    def __init__(self, handlers: list):
        tornado.web.Application.__init__(self, handlers)

    def log_request(self, handler: tornado.web.RequestHandler) -> None:
        pass


class WebhookHandler(tornado.web.RequestHandler):
    def __init__(self, application: tornado.web.Application, request: tornado.httputil.HTTPServerRequest, **kwargs):
        super().__init__(application, request, **kwargs)

    def data_received(self, chunk: bytes) -> typing.Optional[typing.Awaitable[None]]:
        pass

    def initialize(self, botHelper: BotHelper) -> None:
        self.botHelper = botHelper
        self.logger = self.botHelper.loggingHelper.logger.bind(classname=self.__class__.__name__)

    def set_default_headers(self) -> None:
        self.set_header("Content-Type", 'application/json; charset="utf-8"')

    def post(self) -> None:
        self.logger.debug('Webhook Triggered')
        self._validate_post()
        json_string = self.request.body.decode()
        data = json.loads(json_string)
        self.set_status(200)
        self.logger.debug(f'Webhook Received Data: {data}')
        self.botHelper.threadingHelper.initThread(target=self.botHelper.mirrorListenerHelper.updateStatusCallback,
                                                  name=f"{data['mirrorUid']}-{data['mirrorStatus']}", uid=data['mirrorUid'])

    def _validate_post(self) -> None:
        ct_header = self.request.headers.get("Content-Type", None)
        if ct_header != 'application/json':
            raise tornado.web.HTTPError(403)

    def write_error(self, status_code: int, **kwargs: typing.Any) -> None:
        super().write_error(status_code, **kwargs)
        self.logger.debug("%s - - %s", self.request.remote_ip, "Exception in WebhookHandler", exc_info=kwargs['exc_info'])


class DirectDownloadLinkException(Exception):
    pass


class NotSupportedArchiveFormat(Exception):
    pass


class InlineKeyboardMaker:
    def __init__(self, buttonList: list):
        self.buttonList = buttonList
        self.buttons = []
        self.menu = []
        self.keyboard = []

    def build(self, columns: int) -> telegram.InlineKeyboardMarkup:
        for i in range(len(self.buttonList)):
            self.buttons.append(telegram.InlineKeyboardButton(text=self.buttonList[i], callback_data=str((i + 1))))
        self.menu = [self.buttons[i: i + columns] for i in range(0, len(self.buttons), columns)]
        self.keyboard = telegram.InlineKeyboardMarkup(self.menu)
        return self.keyboard


class InterceptHandler(logging.Handler):
    def __init__(self, logger):
        self.logger = logger
        super().__init__()

    def emit(self, logRecord: logging.LogRecord):
        try:
            level = self.logger.level(logRecord.levelname).name
        except ValueError:
            level = logRecord.levelno
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        self.logger.opt(depth=depth, exception=logRecord.exc_info).log(level, logRecord.getMessage())
