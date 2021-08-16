# TODO: add sufficient documentation to the functions and classes in this module
# TODO: Code for Download from Mega
# TODO: Code for Upload to Mega
# TODO: Helper functions - bot_utils.py, fs_utils.py, message_utils.py
# TODO: Code for user filters
# TODO: Add and Handle Exceptions
# TODO: Code for direct link generation
import aria2p
import asyncio
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
import os
import psutil
import random
import re
import requests
import shutil
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


class MirrorInfo:
    updatableVars: typing.List[str] = ['sizeTotal', 'sizeCurrent', 'speedCurrent', 'timeCurrent',
                                       'isTorrent', 'numSeeders', 'numLeechers']

    def __init__(self, msg: telegram.Message):
        self.msg = msg
        self.msgId = msg.message_id
        self.chatId = msg.chat.id
        self.uid: str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        self.path: str = f'{dlRootDirPath}/{self.uid}'
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
        self.googleDriveDownloadSourceId: str = ''
        self.uploadUrl: str = ''
        self.googleDriveUploadFolderId: str = ''
        self.isUrl: bool = False
        self.isMagnet: bool = False
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

    def updateVars(self, currVars: typing.Dict[str, typing.Union[int, float, str]]):
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


class UrlRegex:
    generalUrl = r"(?:(?:https?|ftp)://)?[\w/\-?=%.]+\.[\w/\-?=%.]+"
    bittorrentMagnet = r"magnet:\?xt=urn:btih:[a-zA-Z0-9]*"
    googleDrive = r"https://drive\.google\.com/(drive)?/?u?/?\d?/?(mobile)?/?(file)?(folders)?/?d?/([-\w]+)[?+]?/?(w+)?"
    youTube = r"((https|http)://)?((www|m)\.)?(youtube\.com|youtu\.be)/(watch\?v=)?[\w\-]+"


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


class MirrorListener:
    def __init__(self, mirrorHelper: 'MirrorHelper'):
        self.mirrorHelper = mirrorHelper
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

    def startWebhookServer(self, ready=None, forceEventLoop=False):
        self.webhookServer = WebhookServer(self.mirrorHelper)
        threadInit(target=self.webhookServer.serveForever, name='mirrorListener.webhookServer',
                   forceEventLoop=forceEventLoop, ready=ready)

    def stopWebhookServer(self):
        if self.webhookServer:
            self.webhookServer.shutdown()
            self.webhookServer = None

    def updateStatus(self, uid: str, mirrorStatus: str):
        self.mirrorHelper.mirrorInfos[uid].status = mirrorStatus
        data = {'mirrorUid': uid, 'mirrorStatus': mirrorStatus}
        headers = {'Content-Type': 'application/json'}
        requests.post(url=self.webhookServer.webhookUrl, data=json.dumps(data), headers=headers)

    def updateStatusCallback(self, uid: str):
        mirrorInfo: MirrorInfo = self.mirrorHelper.mirrorInfos[uid]
        logger.info(f'{mirrorInfo.uid} : {mirrorInfo.status}')
        self.statusCallBacks[mirrorInfo.status](mirrorInfo)

    def onAddMirror(self, mirrorInfo: MirrorInfo):
        self.downloadQueue.append(mirrorInfo.uid)
        self.updateStatus(mirrorInfo.uid, MirrorStatus.downloadQueue)

    # TODO: improve method and maybe not use onCancelMirror callback in operationErrors and improve onOperationErrors
    def onCancelMirror(self, mirrorInfo: MirrorInfo):
        shutil.rmtree(mirrorInfo.path)
        self.mirrorHelper.mirrorInfos.pop(mirrorInfo.uid)

    def onCompleteMirror(self, mirrorInfo: MirrorInfo):
        shutil.rmtree(mirrorInfo.path)
        self.mirrorHelper.mirrorInfos.pop(mirrorInfo.uid)
        if mirrorInfo.isGoogleDriveUpload or mirrorInfo.isMegaUpload:
            bot.sendMessage(text=f'Uploaded: [{mirrorInfo.uid}] [{mirrorInfo.uploadUrl}]',
                            parse_mode='HTML', chat_id=mirrorInfo.chatId, reply_to_message_id=mirrorInfo.msgId)

    def onDownloadQueue(self, mirrorInfo: MirrorInfo):
        self.resetMirrorProgress(mirrorInfo.uid)
        self.checkDownloadQueue()

    def checkDownloadQueue(self):
        if self.downloadQueueSize > self.downloadQueueActive < len(self.downloadQueue):
            self.updateStatus(self.downloadQueue[self.downloadQueueActive], MirrorStatus.downloadStart)
            self.downloadQueueActive += 1
            self.checkDownloadQueue()

    def onDownloadStart(self, mirrorInfo: MirrorInfo):
        os.mkdir(mirrorInfo.path)
        if mirrorInfo.isAriaDownload:
            threadInit(target=self.mirrorHelper.ariaHelper.addDownload,
                       name=f'{mirrorInfo.uid}-AriaDownload', mirrorInfo=mirrorInfo)
        if mirrorInfo.isGoogleDriveDownload:
            threadInit(target=self.mirrorHelper.googleDriveHelper.addDownload,
                       name=f'{mirrorInfo.uid}-GoogleDriveDownload', mirrorInfo=mirrorInfo)
        if mirrorInfo.isMegaDownload:
            threadInit(target=self.mirrorHelper.megaHelper.addDownload,
                       name=f'{mirrorInfo.uid}-MegaDownload', mirrorInfo=mirrorInfo)
        if mirrorInfo.isTelegramDownload:
            threadInit(target=self.mirrorHelper.telegramHelper.addDownload,
                       name=f'{mirrorInfo.uid}-TelegramDownload', mirrorInfo=mirrorInfo)
        if mirrorInfo.isYouTubeDownload:
            threadInit(target=self.mirrorHelper.youTubeHelper.addDownload,
                       name=f'{mirrorInfo.uid}-YouTubeDownload', mirrorInfo=mirrorInfo)
        self.updateStatus(mirrorInfo.uid, MirrorStatus.downloadProgress)

    def onDownloadProgress(self, mirrorInfo: MirrorInfo):
        pass

    def onDownloadComplete(self, mirrorInfo: MirrorInfo):
        self.downloadQueue.remove(mirrorInfo.uid)
        self.downloadQueueActive -= 1
        self.compressionQueue.append(mirrorInfo.uid)
        self.updateStatus(mirrorInfo.uid, MirrorStatus.compressionQueue)
        self.checkDownloadQueue()

    def onDownloadError(self, mirrorInfo: MirrorInfo):
        self.downloadQueue.remove(mirrorInfo.uid)
        self.downloadQueueActive -= 1
        self.updateStatus(mirrorInfo.uid, MirrorStatus.cancelMirror)
        self.checkDownloadQueue()

    def onCompressionQueue(self, mirrorInfo: MirrorInfo):
        if not mirrorInfo.isCompress:
            self.compressionQueue.remove(mirrorInfo.uid)
            self.decompressionQueue.append(mirrorInfo.uid)
            self.updateStatus(mirrorInfo.uid, MirrorStatus.decompressionQueue)
            return
        self.resetMirrorProgress(mirrorInfo.uid)
        self.checkCompressionQueue()

    def checkCompressionQueue(self):
        if self.compressionQueueSize > self.compressionQueueActive < len(self.compressionQueue):
            self.updateStatus(self.compressionQueue[self.compressionQueueActive], MirrorStatus.compressionStart)
            self.compressionQueueActive += 1
            self.checkCompressionQueue()

    def onCompressionStart(self, mirrorInfo: MirrorInfo):
        threadInit(target=self.mirrorHelper.compressionHelper.addCompression,
                   name=f'{mirrorInfo.uid}-Compression', mirrorInfo=mirrorInfo)
        self.updateStatus(mirrorInfo.uid, MirrorStatus.compressionProgress)

    def onCompressionProgress(self, mirrorInfo: MirrorInfo):
        pass

    def onCompressionComplete(self, mirrorInfo: MirrorInfo):
        self.compressionQueue.remove(mirrorInfo.uid)
        self.compressionQueueActive -= 1
        self.decompressionQueue.append(mirrorInfo.uid)
        self.updateStatus(mirrorInfo.uid, MirrorStatus.decompressionQueue)
        self.checkCompressionQueue()

    def onCompressionError(self, mirrorInfo: MirrorInfo):
        self.compressionQueue.remove(mirrorInfo.uid)
        self.compressionQueueActive -= 1
        self.updateStatus(mirrorInfo.uid, MirrorStatus.cancelMirror)
        self.checkCompressionQueue()

    def onDecompressionQueue(self, mirrorInfo: MirrorInfo):
        if not mirrorInfo.isDecompress:
            self.decompressionQueue.remove(mirrorInfo.uid)
            self.uploadQueue.append(mirrorInfo.uid)
            self.updateStatus(mirrorInfo.uid, MirrorStatus.uploadQueue)
            return
        self.resetMirrorProgress(mirrorInfo.uid)
        self.checkDecompressionQueue()

    def checkDecompressionQueue(self):
        if self.decompressionQueueSize > self.decompressionQueueActive < len(self.decompressionQueue):
            self.updateStatus(self.decompressionQueue[self.decompressionQueueActive], MirrorStatus.decompressionStart)
            self.decompressionQueueActive += 1
            self.checkDecompressionQueue()

    def onDecompressionStart(self, mirrorInfo: MirrorInfo):
        threadInit(target=self.mirrorHelper.decompressionHelper.addDecompression,
                   name=f'{mirrorInfo.uid}-Decompression', mirrorInfo=mirrorInfo)
        self.updateStatus(mirrorInfo.uid, MirrorStatus.decompressionProgress)

    def onDecompressionProgress(self, mirrorInfo: MirrorInfo):
        pass

    def onDecompressionComplete(self, mirrorInfo: MirrorInfo):
        self.decompressionQueue.remove(mirrorInfo.uid)
        self.decompressionQueueActive -= 1
        self.uploadQueue.append(mirrorInfo.uid)
        self.updateStatus(mirrorInfo.uid, MirrorStatus.uploadQueue)
        self.checkDecompressionQueue()

    def onDecompressionError(self, mirrorInfo: MirrorInfo):
        self.decompressionQueue.remove(mirrorInfo.uid)
        self.decompressionQueueActive -= 1
        self.updateStatus(mirrorInfo.uid, MirrorStatus.cancelMirror)
        self.checkDecompressionQueue()

    def onUploadQueue(self, mirrorInfo: MirrorInfo):
        self.resetMirrorProgress(mirrorInfo.uid)
        self.checkUploadQueue()

    def checkUploadQueue(self):
        if self.uploadQueueSize > self.uploadQueueActive < len(self.uploadQueue):
            self.updateStatus(self.uploadQueue[self.uploadQueueActive], MirrorStatus.uploadStart)
            self.uploadQueueActive += 1
            self.checkUploadQueue()

    def onUploadStart(self, mirrorInfo: MirrorInfo):
        if mirrorInfo.isGoogleDriveUpload:
            threadInit(target=self.mirrorHelper.googleDriveHelper.addUpload,
                       name=f'{mirrorInfo.uid}-GoogleDriveUpload', mirrorInfo=mirrorInfo)
        if mirrorInfo.isMegaUpload:
            threadInit(target=self.mirrorHelper.megaHelper.addUpload,
                       name=f'{mirrorInfo.uid}-MegaUpload', mirrorInfo=mirrorInfo)
        if mirrorInfo.isTelegramUpload:
            threadInit(target=self.mirrorHelper.telegramHelper.addUpload,
                       name=f'{mirrorInfo.uid}-TelegramUpload', mirrorInfo=mirrorInfo)
        self.updateStatus(mirrorInfo.uid, MirrorStatus.uploadProgress)

    def onUploadProgress(self, mirrorInfo: MirrorInfo):
        pass

    def onUploadComplete(self, mirrorInfo: MirrorInfo):
        self.uploadQueue.remove(mirrorInfo.uid)
        self.uploadQueueActive -= 1
        self.updateStatus(mirrorInfo.uid, MirrorStatus.completeMirror)
        self.checkUploadQueue()

    def onUploadError(self, mirrorInfo: MirrorInfo):
        self.uploadQueue.remove(mirrorInfo.uid)
        self.uploadQueueActive -= 1
        self.updateStatus(mirrorInfo.uid, MirrorStatus.cancelMirror)
        self.checkUploadQueue()

    def resetMirrorProgress(self, uid: str):
        self.mirrorHelper.mirrorInfos[uid].timeEnd = 0
        self.mirrorHelper.mirrorInfos[uid].progressPercent = 0


class MirrorHelper:
    def __init__(self):
        self.mirrorInfos: typing.Dict[str, MirrorInfo] = {}
        self.mirrorListener: MirrorListener = MirrorListener(self)
        self.ariaHelper = AriaHelper(self)
        self.googleDriveHelper = GoogleDriveHelper(self)
        self.megaHelper = MegaHelper(self)
        self.telegramHelper = TelegramHelper(self)
        self.youTubeHelper = YouTubeHelper(self)
        self.compressionHelper = CompressionHelper(self)
        self.decompressionHelper = DecompressionHelper(self)
        self.statusHelper = StatusHelper(self)

    def addMirror(self, mirrorInfo: MirrorInfo):
        logger.debug(vars(mirrorInfo))
        self.mirrorInfos[mirrorInfo.uid] = mirrorInfo
        self.mirrorInfos[mirrorInfo.uid].timeStart = int(time.time())
        self.mirrorListener.updateStatus(mirrorInfo.uid, MirrorStatus.addMirror)
        self.statusHelper.addStatus(mirrorInfo.chatId, mirrorInfo.msgId)

    def cancelMirror(self, msg: telegram.Message):
        if self.mirrorInfos == {}:
            logger.info('No Active Downloads !')
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
            logger.info('No Valid Mirror Found !')
            return
        for uid in uids:
            self.mirrorListener.updateStatus(uid, MirrorStatus.cancelMirror)

    def getStatusMsgTxt(self):
        statusMsgTxt: str = ''
        for uid in self.mirrorInfos.keys():
            mirrorInfo = self.mirrorInfos[uid]
            statusMsgTxt += f'{mirrorInfo.uid} {mirrorInfo.status}\n'
        return statusMsgTxt

    def genMirrorInfo(self, msg: telegram.Message):
        mirrorInfo: MirrorInfo = MirrorInfo(msg)
        isValidDl: bool = True
        try:
            mirrorInfo.downloadUrl = msg.text.split(' ')[1].strip()
            mirrorInfo.tag = msg.from_user.username
            mirrorInfo.googleDriveDownloadSourceId = self.getIdFromUrl(mirrorInfo.downloadUrl)
            if mirrorInfo.googleDriveDownloadSourceId != '':
                mirrorInfo.isGoogleDriveDownload = True
            elif re.findall(UrlRegex.youTube, mirrorInfo.downloadUrl):
                mirrorInfo.isYouTubeDownload = True
            elif re.findall(UrlRegex.bittorrentMagnet, mirrorInfo.downloadUrl):
                mirrorInfo.isMagnet = True
                mirrorInfo.isAriaDownload = True
            elif re.findall(UrlRegex.generalUrl, mirrorInfo.downloadUrl):
                mirrorInfo.isUrl = True
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
            logger.info('No Valid Link Provided !')
        return isValidDl, mirrorInfo

    @staticmethod
    def getIdFromUrl(url: str):
        if 'folders' in url or 'file' in url:
            return re.search(UrlRegex.googleDrive, url).group(5)
        return ''


class AriaHelper:
    def __init__(self, mirrorHelper: 'MirrorHelper'):
        self.mirrorHelper = mirrorHelper
        self.api: aria2p.API = aria2p.API(aria2p.Client(host="http://localhost", port=6800,
                                                        secret=envVars[list(optConfigVars.keys())[1]]))
        self.ariaGids: typing.Dict[str, str] = {}

    def addDownload(self, mirrorInfo: MirrorInfo):
        if mirrorInfo.isMagnet:
            self.ariaGids[mirrorInfo.uid] = self.api.add_magnet(mirrorInfo.downloadUrl, options={'dir': mirrorInfo.path}).gid
        if mirrorInfo.isUrl:
            self.ariaGids[mirrorInfo.uid] = self.api.add_uris([mirrorInfo.downloadUrl], options={'dir': mirrorInfo.path}).gid

    def cancelDownload(self, uid: str):
        self.getDlObj(self.ariaGids[uid]).remove(force=True, files=True)
        self.ariaGids.pop(uid)

    def getUid(self, gid: str):
        for uid in self.ariaGids.keys():
            if gid == self.ariaGids[uid]:
                return uid

    def getDlObj(self, gid: str):
        return self.api.get_download(gid)

    def startListener(self):
        self.api.listen_to_notifications(threaded=True,
                                         on_download_start=self.onDownloadStart,
                                         on_download_pause=self.onDownloadPause,
                                         on_download_complete=self.onDownloadComplete,
                                         on_download_stop=self.onDownloadStop,
                                         on_download_error=self.onDownloadError)

    def updateProgress(self, uid: str):
        if uid in self.ariaGids.keys():
            dlObj = self.getDlObj(self.ariaGids[uid])
            currVars: typing.Dict[str, typing.Union[int, float, str]] \
                = {MirrorInfo.updatableVars[0]: dlObj.total_length,
                   MirrorInfo.updatableVars[1]: dlObj.completed_length,
                   MirrorInfo.updatableVars[2]: dlObj.download_speed,
                   MirrorInfo.updatableVars[3]: int(time.time())}
            if dlObj.is_torrent:
                currVars[MirrorInfo.updatableVars[4]] = True
                currVars[MirrorInfo.updatableVars[5]] = dlObj.num_seeders
                currVars[MirrorInfo.updatableVars[6]] = dlObj.connections
            self.mirrorHelper.mirrorInfos[uid].updateVars(currVars)

    def onDownloadStart(self, _: aria2p.API, gid: str):
        logger.debug(vars(self.getDlObj(gid)))

    def onDownloadPause(self, _: aria2p.API, gid: str):
        logger.debug(vars(self.getDlObj(gid)))

    def onDownloadComplete(self, _: aria2p.API, gid: str):
        logger.debug(vars(self.getDlObj(gid)))
        if self.getDlObj(gid).followed_by_ids:
            self.ariaGids[self.getUid(gid)] = self.getDlObj(gid).followed_by_ids[0]
            return
        self.mirrorHelper.mirrorListener.updateStatus(self.getUid(gid), MirrorStatus.downloadComplete)

    def onDownloadStop(self, _: aria2p.API, gid: str):
        logger.debug(vars(self.getDlObj(gid)))

    def onDownloadError(self, _: aria2p.API, gid: str):
        logger.debug(vars(self.getDlObj(gid)))


class GoogleDriveHelper:
    def __init__(self, mirrorHelper: 'MirrorHelper'):
        self.mirrorHelper = mirrorHelper
        self.oauthScopes: typing.List[str] = ['https://www.googleapis.com/auth/drive']
        self.baseFileDownloadUrl: str = 'https://drive.google.com/uc?id={}&export=download'
        self.baseFolderDownloadUrl: str = 'https://drive.google.com/drive/folders/{}'
        self.googleDriveFolderMimeType: str = 'application/vnd.google-apps.folder'
        self.chunkSize: int = 32 * 1024 * 1024
        self.service: typing.Any = None
        if useSaAuth:
            self.oauthCreds: google.oauth2.service_account.Credentials \
                = google.oauth2.service_account.Credentials.from_service_account_file(saJsonFile)
        else:
            self.oauthCreds: google.oauth2.credentials.Credentials \
                = google.oauth2.credentials.Credentials.from_authorized_user_file(tokenJsonFile, self.oauthScopes)

    def addDownload(self, mirrorInfo: MirrorInfo):
        sourceId = mirrorInfo.googleDriveDownloadSourceId
        self.mirrorHelper.mirrorInfos[mirrorInfo.uid].sizeTotal = self.getSizeById(sourceId)
        isFolder = False
        if self.getMetadataById(sourceId, 'mimeType') == self.googleDriveFolderMimeType:
            isFolder = True
        if mirrorInfo.isGoogleDriveUpload and not (mirrorInfo.isCompress or mirrorInfo.isDecompress):
            if isFolder:
                folderId = self.cloneFolder(sourceFolderId=sourceId, parentFolderId=mirrorInfo.googleDriveUploadFolderId)
                self.mirrorHelper.mirrorInfos[mirrorInfo.uid].uploadUrl = self.baseFolderDownloadUrl.format(folderId)
            else:
                fileId = self.cloneFile(sourceFileId=sourceId, parentFolderId=mirrorInfo.googleDriveUploadFolderId)
                self.mirrorHelper.mirrorInfos[mirrorInfo.uid].uploadUrl = self.baseFileDownloadUrl.format(fileId)
        else:
            if isFolder:
                self.downloadFolder(sourceFolderId=sourceId, dlPath=mirrorInfo.path)
            else:
                self.downloadFile(sourceFileId=sourceId, dlPath=mirrorInfo.path)
        self.mirrorHelper.mirrorListener.updateStatus(mirrorInfo.uid, MirrorStatus.downloadComplete)

    def cancelDownload(self, uid: str):
        raise NotImplementedError

    def addUpload(self, mirrorInfo: MirrorInfo):
        if not (mirrorInfo.isGoogleDriveDownload and not (mirrorInfo.isCompress or mirrorInfo.isDecompress)):
            uploadPath = os.path.join(mirrorInfo.path, os.listdir(mirrorInfo.path)[0])
            if os.path.isdir(uploadPath):
                folderId = self.uploadFolder(folderPath=uploadPath, parentFolderId=mirrorInfo.googleDriveUploadFolderId)
                self.mirrorHelper.mirrorInfos[mirrorInfo.uid].uploadUrl = self.baseFolderDownloadUrl.format(folderId)
            if os.path.isfile(uploadPath):
                fileId = self.uploadFile(filePath=uploadPath, parentFolderId=mirrorInfo.googleDriveUploadFolderId)
                self.mirrorHelper.mirrorInfos[mirrorInfo.uid].uploadUrl = self.baseFileDownloadUrl.format(fileId)
        else:
            time.sleep(self.mirrorHelper.statusHelper.statusUpdateInterval)
        self.mirrorHelper.mirrorListener.updateStatus(mirrorInfo.uid, MirrorStatus.uploadComplete)

    def cancelUpload(self, uid: str):
        raise NotImplementedError

    def authorizeApi(self):
        if not useSaAuth:
            if not self.oauthCreds.valid:
                if self.oauthCreds.expired and self.oauthCreds.refresh_token:
                    self.oauthCreds.refresh(google.auth.transport.requests.Request())
                    logger.info('Google Drive API Token Refreshed !')
                    with open(tokenJsonFile, 'w') as token:
                        token.write(self.oauthCreds.to_json())
                    if envVars['dynamicConfig'] == 'true':
                        # build service for patching tokenJsonFile
                        self.buildService()
                        logger.info(self.patchFile(f"{envVars['currWorkDir']}/{tokenJsonFile}"))
                        updateFileidJson()
                        return
                else:
                    logger.info('Google Drive API User Token Needs to Refreshed Manually ! Exiting...')
                    exit(1)
        self.buildService()

    def buildService(self):
        self.service = googleapiclient.discovery.build(serviceName='drive', version='v3', credentials=self.oauthCreds,
                                                       cache_discovery=False)

    def uploadFile(self, filePath: str, parentFolderId: str):
        upStatus: googleapiclient.http.MediaUploadProgress
        fileName, fileMimeType, fileMetadata, mediaBody = self.getUpData(filePath, isResumable=True)
        fileMetadata['parents'] = [parentFolderId]
        fileOp = self.service.files().create(supportsAllDrives=True, body=fileMetadata, media_body=mediaBody)
        upResponse = None
        while not upResponse:
            upStatus, upResponse = fileOp.next_chunk()
        return upResponse['id']

    def uploadFolder(self, folderPath: str, parentFolderId: str):
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

    def cloneFile(self, sourceFileId: str, parentFolderId: str):
        fileMetadata = {'parents': [parentFolderId]}
        return self.service.files().copy(supportsAllDrives=True, fileId=sourceFileId, body=fileMetadata).execute()['id']

    def cloneFolder(self, sourceFolderId: str, parentFolderId: str):
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

    def downloadFile(self, sourceFileId: str, dlPath: str):
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

    def downloadFolder(self, sourceFolderId: str, dlPath: str):
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

    def createFolder(self, folderName: str, parentFolderId: str):
        folderMetadata = {'name': folderName, 'parents': [parentFolderId], 'mimeType': self.googleDriveFolderMimeType}
        folderOp = self.service.files().create(supportsAllDrives=True, body=folderMetadata).execute()
        return folderOp['id']

    def deleteByUrl(self, url: str):
        contentId = self.mirrorHelper.getIdFromUrl(url)
        if contentId != '':
            self.service.files().delete(fileId=contentId, supportsAllDrives=True).execute()
            return f'Deleted: [{url}]'
        return 'Not a Valid Google Drive Link !'

    def getUpData(self, filePath: str, isResumable: bool):
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

    def getMetadataById(self, sourceId: str, field: str):
        return self.service.files().get(supportsAllDrives=True, fileId=sourceId, fields=field).execute().get(field)

    def getFolderContentsById(self, folderId: str):
        query = f"'{folderId}' in parents"
        pageToken = None
        folderContents = []
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

    def getSizeById(self, sourceId: str):
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

    def patchFile(self, filePath: str, fileId: str = ''):
        fileName, fileMimeType, fileMetadata, mediaBody = self.getUpData(filePath, isResumable=False)
        if fileId == '':
            fileId = envVars[getFileNameEnv(fileName)]
        fileOp = self.service.files().update(fileId=fileId, body=fileMetadata, media_body=mediaBody).execute()
        return f"Patched: [{fileOp['id']}] [{fileName}] [{os.path.getsize(fileName)} bytes]"


class MegaHelper:
    def __init__(self, mirrorHelper: 'MirrorHelper'):
        self.mirrorHelper = mirrorHelper

    def addDownload(self, mirrorInfo: MirrorInfo):
        raise NotImplementedError

    def cancelDownload(self, uid: str):
        raise NotImplementedError

    def addUpload(self, mirrorInfo: MirrorInfo):
        raise NotImplementedError

    def cancelUpload(self, uid: str):
        raise NotImplementedError


class TelegramHelper:
    def __init__(self, mirrorHelper: 'MirrorHelper'):
        self.mirrorHelper = mirrorHelper
        self.uploadMaxSize: int = 2 * 1024 * 1024 * 1024
        self.maxTimeout: int = 24 * 60 * 60

    def addDownload(self, mirrorInfo: MirrorInfo):
        replyTo = mirrorInfo.msg.reply_to_message
        for media in [replyTo.document, replyTo.audio, replyTo.video]:
            if media:
                self.mirrorHelper.mirrorInfos[mirrorInfo.uid].sizeTotal = media.file_size
                self.downloadMedia(media, mirrorInfo.path)
                break
        self.mirrorHelper.mirrorListener.updateStatus(mirrorInfo.uid, MirrorStatus.downloadComplete)

    def cancelDownload(self, uid: str):
        raise NotImplementedError

    def addUpload(self, mirrorInfo: MirrorInfo):
        uploadPath = os.path.join(mirrorInfo.path, os.listdir(mirrorInfo.path)[0])
        upResponse: bool = True
        if os.path.isfile(uploadPath):
            if not self.uploadFile(uploadPath, mirrorInfo.chatId, mirrorInfo.msgId):
                upResponse = False
                bot.sendMessage(text='Files Larger Than 2GB Cannot Be Uploaded Yet !', parse_mode='HTML',
                                chat_id=mirrorInfo.chatId, reply_to_message_id=mirrorInfo.msgId)
        if os.path.isdir(uploadPath):
            if not self.uploadFolder(uploadPath, mirrorInfo.chatId, mirrorInfo.msgId):
                upResponse = False
        if upResponse:
            self.mirrorHelper.mirrorListener.updateStatus(mirrorInfo.uid, MirrorStatus.uploadComplete)
        if not upResponse:
            self.mirrorHelper.mirrorListener.updateStatus(mirrorInfo.uid, MirrorStatus.cancelMirror)

    def cancelUpload(self, uid: str):
        raise NotImplementedError

    def downloadMedia(self, media: typing.Union[telegram.Document, telegram.Audio, telegram.Video], mirrorInfoPath: str):
        shutil.move(src=media.get_file(timeout=self.maxTimeout).file_path,
                    dst=os.path.join(mirrorInfoPath, media.file_name))

    def uploadFile(self, filePath: str, chatId: int, msgId: int):
        if os.path.getsize(filePath) < self.uploadMaxSize:
            bot.sendDocument(document=f'file://{filePath}', filename=filePath.split('/')[-1],
                             chat_id=chatId, reply_to_message_id=msgId, timeout=self.maxTimeout)
            return True
        return False

    def uploadFolder(self, folderPath: str, chatId: int, msgId: int):
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
            bot.sendMessage(text=skippedContentsMsg, parse_mode='HTML', chat_id=chatId, reply_to_message_id=msgId)
        return True


class YouTubeHelper:
    def __init__(self, mirrorHelper: 'MirrorHelper'):
        self.mirrorHelper = mirrorHelper

    def addDownload(self, mirrorInfo: MirrorInfo):
        ytdlOpts: dict = {'format': 'best/bestvideo+bestaudio', 'logger': logger,
                          'outtmpl': f'{mirrorInfo.path}/%(title)s-%(id)s.f%(format_id)s.%(ext)s'}
        self.downloadVideo(mirrorInfo.downloadUrl, ytdlOpts)
        self.mirrorHelper.mirrorListener.updateStatus(mirrorInfo.uid, MirrorStatus.downloadComplete)

    def cancelDownload(self, uid: str):
        raise NotImplementedError

    @staticmethod
    def downloadVideo(videoUrl: str, ytdlOpts: dict):
        with youtube_dl.YoutubeDL(ytdlOpts) as ytdl:
            ytdl.download([videoUrl])


class CompressionHelper:
    def __init__(self, mirrorHelper: 'MirrorHelper'):
        self.mirrorHelper = mirrorHelper

    def addCompression(self, mirrorInfo: MirrorInfo):
        self.compressSource(os.path.join(mirrorInfo.path, os.listdir(mirrorInfo.path)[0]))
        self.mirrorHelper.mirrorListener.updateStatus(mirrorInfo.uid, MirrorStatus.compressionComplete)

    def cancelCompression(self, uid: str):
        raise NotImplementedError

    @staticmethod
    def compressSource(sourcePath: str):
        archiveFormat = list(archiveFormats.keys())[3]
        sourceTempPath = sourcePath + 'temp'
        sourceName = sourcePath.split('/')[-1]
        os.mkdir(sourceTempPath)
        shutil.move(src=sourcePath, dst=os.path.join(sourceTempPath, sourceName))
        shutil.move(src=sourceTempPath, dst=sourcePath)
        shutil.make_archive(sourcePath, archiveFormat, sourcePath)
        shutil.rmtree(sourcePath) if os.path.isdir(sourcePath) else os.remove(sourcePath)


class DecompressionHelper:
    def __init__(self, mirrorHelper: 'MirrorHelper'):
        self.mirrorHelper = mirrorHelper

    def addDecompression(self, mirrorInfo: MirrorInfo):
        self.decompressArchive(os.path.join(mirrorInfo.path, os.listdir(mirrorInfo.path)[0]))
        self.mirrorHelper.mirrorListener.updateStatus(mirrorInfo.uid, MirrorStatus.decompressionComplete)

    def cancelDecompression(self, uid: str):
        raise NotImplementedError

    @staticmethod
    def decompressArchive(archivePath: str):
        archiveFormat = ''
        for archiveFileExtension in archiveFormats.values():
            if archivePath.endswith(archiveFileExtension):
                for archiveFileFormat in archiveFormats.keys():
                    if archiveFormats[archiveFileFormat] == archiveFileExtension:
                        archiveFormat = archiveFileFormat
                        break
                break
        if archiveFormat == '':
            return
        folderPath = archivePath.replace(archiveFormats[archiveFormat], '')
        shutil.unpack_archive(archivePath, folderPath, archiveFormat)
        os.remove(archivePath)


class StatusHelper:
    def __init__(self, mirrorHelper: 'MirrorHelper'):
        self.mirrorHelper = mirrorHelper
        self.isInitThread: bool = False
        self.isUpdateStatus: bool = False
        self.statusUpdateInterval: int = int(envVars[list(optConfigVars.keys())[3]])
        self.msgId: int = 0
        self.chatId: int = 0
        self.lastStatusMsgId: int = 0
        self.lastStatusMsgTxt: str = ''

    def addStatus(self, chatId: int, msgId: int):
        if self.mirrorHelper.mirrorInfos != {}:
            self.isUpdateStatus = True
        else:
            self.isUpdateStatus = False
        if self.lastStatusMsgId == 0:
            self.isInitThread = True
        if self.lastStatusMsgId != 0:
            bot.deleteMessage(chat_id=self.chatId, message_id=self.lastStatusMsgId)
            self.lastStatusMsgId = -1
        self.chatId = chatId
        self.msgId = msgId
        self.lastStatusMsgId = bot.sendMessage(text='...', parse_mode='HTML', chat_id=self.chatId,
                                               reply_to_message_id=self.msgId).message_id
        if self.isInitThread:
            self.isInitThread = False
            threadInit(target=self.updateStatusMsg, name='statusUpdater')

    def getMirrorStatusStr(self, uid: str):
        mirrorInfo: MirrorInfo = self.mirrorHelper.mirrorInfos[uid]
        mirrorStatusStr = f'{mirrorInfo.uid} | {mirrorInfo.status}\n'
        if mirrorInfo.status == MirrorStatus.downloadProgress and mirrorInfo.isAriaDownload:
            if mirrorInfo.uid in self.mirrorHelper.ariaHelper.ariaGids.keys():
                self.mirrorHelper.ariaHelper.updateProgress(mirrorInfo.uid)
                mirrorStatusStr += f'S: {getReadableSize(mirrorInfo.sizeCurrent)} | ' \
                                   f'{getReadableSize(mirrorInfo.sizeTotal)} | ' \
                                   f'{getReadableSize(mirrorInfo.sizeTotal - mirrorInfo.sizeCurrent)}\n' \
                                   f'P: {getProgressBar(mirrorInfo.progressPercent)} | ' \
                                   f'{mirrorInfo.progressPercent}% | ' \
                                   f'{getReadableSize(mirrorInfo.speedCurrent / 8)}/s\n' \
                                   f'T: {getReadableTime(mirrorInfo.timeCurrent - mirrorInfo.timeStart)} | ' \
                                   f'{getReadableTime(mirrorInfo.timeEnd - mirrorInfo.timeCurrent)}\n'
                if mirrorInfo.isTorrent:
                    mirrorStatusStr += f'nS: {mirrorInfo.numSeeders} nL: {mirrorInfo.numLeechers}\n'
        return mirrorStatusStr

    def updateStatusMsg(self):
        if not self.isUpdateStatus:
            bot.editMessageText(text='No Active Downloads !', parse_mode='HTML',
                                chat_id=self.chatId, message_id=self.lastStatusMsgId)
            self.resetAllDat()
            return
        while self.isUpdateStatus:
            if self.lastStatusMsgId == -1:
                time.sleep(0.1)
                continue
            if self.mirrorHelper.mirrorInfos != {}:
                statusMsgTxt = ''
                for uid in self.mirrorHelper.mirrorInfos.keys():
                    statusMsgTxt += self.getMirrorStatusStr(uid)
                if statusMsgTxt != self.lastStatusMsgTxt:
                    bot.editMessageText(text=statusMsgTxt, parse_mode='HTML', chat_id=self.chatId,
                                        message_id=self.lastStatusMsgId)
                    self.lastStatusMsgTxt = statusMsgTxt
                    time.sleep(self.statusUpdateInterval)
                time.sleep(1)
            if self.mirrorHelper.mirrorInfos == {}:
                self.isUpdateStatus = False
                self.updateStatusMsg()

    def resetAllDat(self):
        self.isInitThread: bool = False
        self.isUpdateStatus = False
        self.msgId = 0
        self.chatId = 0
        self.lastStatusMsgId = 0
        self.lastStatusMsgTxt = ''


class WebhookServer:
    def __init__(self, mirrorHelper: 'MirrorHelper'):
        self.mirrorHelper = mirrorHelper
        self.listenAddress: str = 'localhost'
        self.listenPort: int = 8448
        self.webhookPath: str = 'mirrorListener'
        self.webhookUrl: str = f'http://{self.listenAddress}:{self.listenPort}/{self.webhookPath}'
        self.handlers = [(rf"/{self.webhookPath}/?", WebhookHandler, {'mirrorHelper': self.mirrorHelper})]
        self.webhookApp = WebhookApp(self.handlers)
        self.httpServer = tornado.httpserver.HTTPServer(self.webhookApp)
        self.loop: typing.Optional[tornado.ioloop.IOLoop] = None
        self.isRunning = False
        self.serverLock = threading.Lock()
        self.shutdownLock = threading.Lock()

    def serveForever(self, forceEventLoop: bool = False, ready: threading.Event = None) -> None:
        with self.serverLock:
            self.isRunning = True
            logger.debug('Webhook Server started.')
            self.ensureEventLoop(forceEventLoop=forceEventLoop)
            self.loop = tornado.ioloop.IOLoop.current()
            self.httpServer.listen(self.listenPort, address=self.listenAddress)
            if ready is not None:
                ready.set()
            self.loop.start()
            logger.debug('Webhook Server stopped.')
            self.isRunning = False

    def shutdown(self) -> None:
        with self.shutdownLock:
            if not self.isRunning:
                logger.warning('Webhook Server already stopped.')
                return
            self.loop.add_callback(self.loop.stop)

    @staticmethod
    def ensureEventLoop(forceEventLoop: bool = False) -> None:
        try:
            loop = asyncio.get_event_loop()
            if (not forceEventLoop and os.name == 'nt' and sys.version_info >= (3, 8)
                    and isinstance(loop, asyncio.ProactorEventLoop)):
                raise TypeError('`ProactorEventLoop` is incompatible with Tornado.'
                                'Please switch to `SelectorEventLoop`.')
        except RuntimeError:
            if (os.name == 'nt' and sys.version_info >= (3, 8) and hasattr(asyncio, 'WindowsProactorEventLoopPolicy')
                    and (isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy))):
                logger.debug('Applying Tornado asyncio event loop fix for Python 3.8+ on Windows')
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

    def initialize(self, mirrorHelper: 'MirrorHelper'):
        self.mirrorHelper = mirrorHelper

    def set_default_headers(self) -> None:
        self.set_header("Content-Type", 'application/json; charset="utf-8"')

    def post(self) -> None:
        logger.debug('Webhook Triggered')
        self._validate_post()
        json_string = self.request.body.decode()
        data = json.loads(json_string)
        self.set_status(200)
        logger.debug(f'Webhook Received Data: {data}')
        threadInit(target=self.mirrorHelper.mirrorListener.updateStatusCallback,
                   name=f"{data['mirrorUid']}-{data['mirrorStatus']}", uid=data['mirrorUid'])

    def _validate_post(self) -> None:
        ct_header = self.request.headers.get("Content-Type", None)
        if ct_header != 'application/json':
            raise tornado.web.HTTPError(403)

    def write_error(self, status_code: int, **kwargs: typing.Any) -> None:
        super().write_error(status_code, **kwargs)
        logger.debug("%s - - %s", self.request.remote_ip, "Exception in WebhookHandler", exc_info=kwargs['exc_info'])


class DirectDownloadLinkException(Exception):
    pass


class NotSupportedArchiveFormat(Exception):
    pass


class BotCommands:
    Start = telegram.BotCommand(command='start',
                                description='StartCommand')
    Help = telegram.BotCommand(command='help',
                               description='HelpCommand')
    Stats = telegram.BotCommand(command='stats',
                                description='StatsCommand')
    Ping = telegram.BotCommand(command='ping',
                               description='PingCommand')
    Restart = telegram.BotCommand(command='restart',
                                  description='RestartCommand')
    Logs = telegram.BotCommand(command='logs',
                               description='LogsCommand')
    Mirror = telegram.BotCommand(command='mirror',
                                 description='MirrorCommand')
    Status = telegram.BotCommand(command='status',
                                 description='StatusCommand')
    Cancel = telegram.BotCommand(command='cancel',
                                 description='CancelCommand')
    List = telegram.BotCommand(command='list',
                               description='ListCommand')
    Delete = telegram.BotCommand(command='delete',
                                 description='DeleteCommand')
    Authorize = telegram.BotCommand(command='authorize',
                                    description='AuthorizeCommand')
    Unauthorize = telegram.BotCommand(command='unauthorize',
                                      description='UnauthorizeCommand')
    Sync = telegram.BotCommand(command='sync',
                               description='SyncCommand')
    Top = telegram.BotCommand(command='top',
                              description='TopCommand')
    Config = telegram.BotCommand(command='config',
                                 description='ConfigCommand')


class InlineKeyboardMaker:
    def __init__(self, buttonList: list):
        self.buttonList = buttonList
        self.buttons = []
        self.menu = []
        self.keyboard = []

    def build(self, columns: int):
        for i in range(len(self.buttonList)):
            self.buttons.append(telegram.InlineKeyboardButton(text=self.buttonList[i], callback_data=str((i + 1))))
        self.menu = [self.buttons[i: i + columns] for i in range(0, len(self.buttons), columns)]
        self.keyboard = telegram.InlineKeyboardMarkup(self.menu)
        return self.keyboard


class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def threadInit(target: typing.Callable, name: str, *args: object, **kwargs: object) -> None:
    thread = threading.Thread(target=threadWrapper, name=name, args=(target,) + args, kwargs=kwargs, )
    thread.start()


def threadWrapper(target: typing.Callable, *args: object, **kwargs: object) -> None:
    global runningThreads
    threadName = threading.current_thread().name
    runningThreads.append(threading.current_thread())
    logger.debug(f'Thread Started: {threadName} [runningThreads - {len(runningThreads)}]')
    try:
        target(*args, **kwargs)
    except Exception:
        logger.exception(f'Unhandled Exception in Thread: {threadName}')
        raise
    runningThreads.remove(threading.current_thread())
    logger.debug(f'Thread Ended: {threadName} [runningThreads - {len(runningThreads)}]')


def ariaDl(fileName: str):
    logger.debug(f"Starting Download: '{fileName}'...")
    fileUrl = 'https://docs.google.com/uc?export=download&id={}'.format(envVars[getFileNameEnv(fileName)])
    if os.path.exists(fileName):
        os.remove(fileName)
    subprocess.run(['aria2c', fileUrl, '--quiet=true', '--out=' + fileName])
    # intentional thread switching
    time.sleep(0.1)
    timeLapsed = 0.1
    while timeLapsed <= float(envVars['dlWaitTime']):
        if os.path.exists(fileName):
            logger.debug(f"Downloaded '{fileName}'")
            break
        else:
            time.sleep(0.1)
            timeLapsed += 0.1


def checkBotApiStart():
    global bot
    conSuccess = False
    while not conSuccess:
        try:
            bot.getMe()
            conSuccess = True
        except telegram.error.NetworkError:
            time.sleep(0.1)
            continue


def checkConfigVars():
    global configJsonFile, envVars, optConfigVars, reqConfigVars
    envVars = {**envVars, **optConfigVars, **jsonFileLoad(configJsonFile)}
    for reqConfigVar in reqConfigVars:
        try:
            if envVars[reqConfigVar] in ['', ' ', {}]:
                raise KeyError
        except KeyError:
            logger.error(f"Required Environment Variable Missing: '{reqConfigVar}' ! Exiting...")
            exit(1)


def checkRestart():
    global bot
    if os.path.exists(restartJsonFile):
        restartJsonDict = jsonFileLoad(restartJsonFile)
        bot.editMessageText(text='Bot Restarted Successfully !', parse_mode='HTML',
                            chat_id=restartJsonDict['chatId'], message_id=restartJsonDict['msgId'])
        os.remove(restartJsonFile)


def configHandler():
    global configFiles, envVars, runningThreads, useSaAuth
    if os.path.exists(dynamicJsonFile):
        envVars['dynamicConfig'] = 'true'
        logger.info('Using Dynamic Config...')
        envVars = {**envVars, **jsonFileLoad(dynamicJsonFile)}
        ariaDl(fileidJsonFile)
        if not os.path.exists(fileidJsonFile):
            logger.error(f"Config File Missing: '{fileidJsonFile}' ! Exiting...")
            exit(1)
        envVars = {**envVars, **jsonFileLoad(fileidJsonFile)}
        for configFile in configFiles:
            if getFileNameEnv(configFile) in envVars.keys():
                fileHashInDict = envVars[getFileNameEnv(configFile) + 'Hash']
                if not (os.path.exists(configFile) and fileHashInDict == getFileHash(configFile)):
                    threadInit(target=ariaDl, name=f'{configFile}-ariaDl', fileName=configFile)
        while runningThreads:
            time.sleep(0.1)
    else:
        envVars['dynamicConfig'] = 'false'
        logger.info('Using Static Config...')
        envVars['dlWaitTime'] = '5'
    if os.path.exists(saJsonFile):
        useSaAuth = True
        configFiles.remove(tokenJsonFile)
    else:
        useSaAuth = False
        configFiles.remove(saJsonFile)
    for configFile in configFiles:
        if not os.path.exists(configFile):
            logger.error(f"Config File Missing: '{configFile}' ! Exiting...")
            exit(1)


def fileBak(fileName: str):
    fileBakName = fileName + '.bak'
    try:
        shutil.copy(os.path.join(envVars['currWorkDir'], fileName), os.path.join(envVars['currWorkDir'], fileBakName))
        logger.info(f"Copied: '{fileName}' -> '{fileBakName}'")
    except FileNotFoundError:
        logger.error(FileNotFoundError)
        # TODO: remove exit maybe?
        exit(1)


def getChatDetails(update: telegram.Update):
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        return user.id, user.first_name, 'private'
    else:
        chat = update.effective_chat
        return chat.id, (chat.first_name if chat.type == 'private' else chat.title), chat.type


def getFileNameEnv(fileName: str):
    splitList = fileName.split('.')
    fileIdEnvName = splitList[0]
    if len(splitList) > 1:
        for i in range(1, len(splitList)):
            fileIdEnvName += splitList[i].capitalize()
    return fileIdEnvName


def getFileHash(filePath: str):
    hashSum = hashlib.sha256()
    blockSize = 128 * hashSum.block_size
    fileStream = open(filePath, 'rb')
    fileChunk = fileStream.read(blockSize)
    while fileChunk:
        hashSum.update(fileChunk)
        fileChunk = fileStream.read(blockSize)
    return hashSum.hexdigest()


def getProgressBar(progress: float):
    progressRounded = round(progress)
    numFull = progressRounded // 8
    numEmpty = (100 // 8) - numFull
    partIndex = (progressRounded % 8) - 1
    return f"{progressUnits[-1] * numFull}{(progressUnits[partIndex] if partIndex >= 0 else '')}{' ' * numEmpty}"


# TODO: typecheck numBytes
def getReadableSize(numBytes: float):
    global sizeUnits
    i = 0
    if numBytes is not None:
        while numBytes >= 1024:
            numBytes /= 1024
            i += 1
    else:
        numBytes = 0
    return f'{round(numBytes, 2)} {sizeUnits[i]}'


def getReadableTime(seconds: float):
    readableTime = ''
    (numDays, remainderHours) = divmod(seconds, 86400)
    numDays = int(numDays)
    if numDays != 0:
        readableTime += f'{numDays}d'
    (numHours, remainderMins) = divmod(remainderHours, 3600)
    numHours = int(numHours)
    if numHours != 0:
        readableTime += f'{numHours}h'
    (numMins, remainderSecs) = divmod(remainderMins, 60)
    numMins = int(numMins)
    if numMins != 0:
        readableTime += f'{numMins}m'
    numSecs = int(remainderSecs)
    readableTime += f'{numSecs}s'
    return readableTime


def getStatsMsg():
    botUpTime = getReadableTime(time.time() - botStartTime)
    cpuUsage = psutil.cpu_percent(interval=0.5)
    memoryUsage = psutil.virtual_memory().percent
    diskUsageTotal, diskUsageUsed, diskUsageFree, diskUsage = psutil.disk_usage('.')
    statsMsg = f'botUpTime: {botUpTime}\n' \
               f'cpuUsage: {cpuUsage}%\n' \
               f'memoryUsage: {memoryUsage}%\n' \
               f'diskUsage: {diskUsage}%\n' \
               f'Total: {getReadableSize(diskUsageTotal)} | ' \
               f'Used: {getReadableSize(diskUsageUsed)} | ' \
               f'Free: {getReadableSize(diskUsageFree)}\n' \
               f'dataDown: {getReadableSize(psutil.net_io_counters().bytes_recv)} | ' \
               f'dataUp: {getReadableSize(psutil.net_io_counters().bytes_sent)}\n'
    return statsMsg


def jsonFileLoad(jsonFileName: str):
    return json.loads(open(jsonFileName, 'rt', encoding='utf-8').read())


def jsonFileWrite(jsonFileName: str, jsonDict: dict):
    open(jsonFileName, 'wt', encoding='utf-8').write(json.dumps(jsonDict, indent=2) + '\n')


def initBotApi():
    global bot, dispatcher, updater
    updater = telegram.ext.Updater(token=envVars[reqConfigVars[0]], base_url="http://localhost:8081/bot")
    bot = updater.bot
    dispatcher = updater.dispatcher


def updateAuthorizedChatsDict(chatId: int, chatName: str, chatType: str, auth: bool = None, unauth: bool = None):
    if auth:
        envVars[list(optConfigVars.keys())[0]][str(chatId)] = {"chatType": chatType, "chatName": chatName}
    if unauth:
        envVars[list(optConfigVars.keys())[0]].pop(str(chatId))
    updateConfigJson({list(optConfigVars.keys())[0]: envVars[list(optConfigVars.keys())[0]]})


def updateConfigJson(updateDict: typing.Dict[str, typing.Union[str, typing.Dict[str, typing.Union[str, typing.Dict[str, str]]]]]):
    fileBak(configJsonFile)
    jsonFileWrite(configJsonFile, {**jsonFileLoad(configJsonFile), **updateDict})
    if envVars['dynamicConfig'] == 'true':
        logger.info(mirrorHelper.googleDriveHelper.patchFile(f"{envVars['currWorkDir']}/{configJsonFile}"))
        logger.info(mirrorHelper.googleDriveHelper.patchFile(f"{envVars['currWorkDir']}/{configJsonBakFile}"))
        updateFileidJson()


def updateFileidJson():
    global configFiles, envVars, fileidJsonFile
    fileidJsonDict: typing.Dict[str, str] = {}
    for file in configFiles:
        fileNameEnv = getFileNameEnv(file)
        fileHashEnv = fileNameEnv + 'Hash'
        envVars[fileHashEnv] = getFileHash(os.path.join(envVars['currWorkDir'], file))
        fileidJsonDict[fileNameEnv] = envVars[fileNameEnv]
        fileidJsonDict[fileHashEnv] = envVars[fileHashEnv]
    jsonFileWrite(fileidJsonFile, fileidJsonDict)
    logger.info(mirrorHelper.googleDriveHelper.patchFile(f"{envVars['currWorkDir']}/{fileidJsonFile}"))


# loguru default format
# '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | '
# '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>'

runningThreads: typing.List[threading.Thread] = []
botStartTime: float = time.time()
bot: telegram.Bot
dispatcher: telegram.ext.Dispatcher
updater: telegram.ext.Updater
useSaAuth: bool
configJsonFile = 'config.json'
configJsonBakFile = configJsonFile + '.bak'
restartJsonFile = 'restart.json'
saJsonFile = 'sa.json'
tokenJsonFile = 'token.json'
dynamicJsonFile = 'dynamic.json'
fileidJsonFile = 'fileid.json'
configFiles: [str] = [configJsonFile, configJsonBakFile, saJsonFile, tokenJsonFile]
reqConfigVars: [str] = ['botToken', 'botOwnerId', 'telegramApiId', 'telegramApiHash', 'googleDriveUploadFolderIds']
optConfigVars: typing.Dict[str, typing.Union[str, typing.Dict[str, typing.Union[str, typing.Dict[str, str]]]]] = \
    {'authorizedChats': {}, 'ariaRpcSecret': 'tgmb-beta', 'dlRootDir': 'dl', 'statusUpdateInterval': '5'}
envVars: typing.Dict[str, typing.Union[str, typing.Dict[str, typing.Union[str, typing.Dict[str, str]]]]] = \
    {'currWorkDir': os.getcwd()}
logFiles: [str] = ['bot.log', 'botApi.log', 'aria.log', 'tqueue.binlog', 'webhooks_db.binlog']
logInfoFormat = '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <6}</level> | <k>{message}</k>'
logDebugFormat = '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | ' \
                 '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <k>{message}</k>'
sizeUnits: [str] = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
progressUnits: typing.List[str] = ['▏', '▎', '▍', '▌', '▋', '▊', '▉', '█']
archiveFormats: typing.Dict[str, str] = {'zip': '.zip', 'tar': '.tar', 'bztar': '.tar.bz2',
                                         'gztar': '.tar.gz', 'xztar': '.tar.xz'}

warnings.filterwarnings("ignore")

if os.path.exists(logFiles[0]):
    os.remove(logFiles[0])

logger = loguru.logger
logger.remove()
logger.add(sys.stderr, level='DEBUG', format=logDebugFormat)
logger.add(logFiles[0], level='DEBUG', format=logDebugFormat, rotation='24h')
logger.disable('apscheduler')

logging.basicConfig(handlers=[InterceptHandler()], level=0)

configHandler()
checkConfigVars()
initBotApi()

mirrorHelper = MirrorHelper()

mirrorHelper.googleDriveHelper.authorizeApi()

dlRootDirPath = os.path.join(envVars['currWorkDir'], envVars[list(optConfigVars.keys())[2]])

if os.path.exists(dlRootDirPath):
    shutil.rmtree(dlRootDirPath)
os.mkdir(dlRootDirPath)
