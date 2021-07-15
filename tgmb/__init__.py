# TODO: add sufficient documentation to the functions and classes in this module
# TODO: Code for Download from Telegram
# TODO: Code for Download from YouTube
# TODO: Code for Upload to Telegram
# TODO: Code for CompressionHelper and DecompressionHelper
# TODO: Helper functions - bot_utils.py, fs_utils.py, message_utils.py
# TODO: Code for user filters
# TODO: Add and Handle Exceptions
# TODO: Code for direct link generation
# TODO: may be add glances and run it on http port 80
# TODO: maybe customise garbage collection
import aria2p
import asyncio
import googleapiclient.discovery
import googleapiclient.errors
import googleapiclient.http
import google.auth.transport.requests
import google.oauth2.credentials
import google_auth_oauthlib.flow
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


class MirrorInfo:
    def __init__(self, msgId: int, chatId: int):
        self.msgId = msgId
        self.chatId = chatId
        self.uid: str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        self.path: str = f'{dlRootDirPath}/{self.uid}'
        self.status: str = ''
        self.url: str = ''
        self.tag: str = ''
        self.eta: float = 0
        self.progress: float = 0
        self.totalSize: int = 0
        self.totalSizeStr: str = '0B'
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

    def initTotalSize(self, totalSize: int):
        self.totalSize = totalSize
        self.totalSizeStr = getReadableSize(totalSize)


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
        self.downloadQueue: list[str] = []
        self.compressionQueueSize: int = 1
        self.compressionQueueActive: int = 0
        self.compressionQueue: list[str] = []
        self.decompressionQueueSize: int = 1
        self.decompressionQueueActive: int = 0
        self.decompressionQueue: list[str] = []
        self.uploadQueueSize: int = 3
        self.uploadQueueActive: int = 0
        self.uploadQueue: list[str] = []
        self.statusCallBackDict: typing.Dict[str, typing.Callable] \
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
        initThread(target=self.webhookServer.serveForever, name='mirrorListener.webhookServer',
                   forceEventLoop=forceEventLoop, ready=ready)

    def stopWebhookServer(self):
        if self.webhookServer:
            self.webhookServer.shutdown()
            self.webhookServer = None

    def updateStatus(self, uid: str, mirrorStatus: str):
        self.mirrorHelper.mirrorInfoDict[uid].status = mirrorStatus
        data = {'mirrorUid': uid, 'mirrorStatus': mirrorStatus}
        headers = {'Content-Type': 'application/json'}
        requests.post(url=self.webhookServer.webhookUrl, data=json.dumps(data), headers=headers)

    def updateStatusCallback(self, uid: str):
        mirrorInfo: MirrorInfo = self.mirrorHelper.mirrorInfoDict[uid]
        logger.info(f'{mirrorInfo.uid} : {mirrorInfo.status}')
        self.statusCallBackDict[mirrorInfo.status](mirrorInfo)

    def onAddMirror(self, mirrorInfo: MirrorInfo):
        self.downloadQueue.append(mirrorInfo.uid)
        self.updateStatus(mirrorInfo.uid, MirrorStatus.downloadQueue)

    # TODO: improve method and maybe not use onCancelMirror callback in operationErrors and improve onOperationErrors
    def onCancelMirror(self, mirrorInfo: MirrorInfo):
        shutil.rmtree(mirrorInfo.path)
        self.mirrorHelper.mirrorInfoDict.pop(mirrorInfo.uid)

    def onCompleteMirror(self, mirrorInfo: MirrorInfo):
        shutil.rmtree(mirrorInfo.path)
        self.mirrorHelper.mirrorInfoDict.pop(mirrorInfo.uid)
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
            initThread(target=self.mirrorHelper.ariaHelper.addDownload,
                       name=f'{mirrorInfo.uid}-AriaDownload', mirrorInfo=mirrorInfo)
        if mirrorInfo.isGoogleDriveDownload:
            initThread(target=self.mirrorHelper.googleDriveHelper.addDownload,
                       name=f'{mirrorInfo.uid}-GoogleDriveDownload', mirrorInfo=mirrorInfo)
        if mirrorInfo.isMegaDownload:
            initThread(target=self.mirrorHelper.megaHelper.addDownload,
                       name=f'{mirrorInfo.uid}-MegaDownload', mirrorInfo=mirrorInfo)
        if mirrorInfo.isTelegramDownload:
            initThread(target=self.mirrorHelper.telegramHelper.addDownload,
                       name=f'{mirrorInfo.uid}-TelegramDownload', mirrorInfo=mirrorInfo)
        if mirrorInfo.isYouTubeDownload:
            initThread(target=self.mirrorHelper.youTubeHelper.addDownload,
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
        initThread(target=self.mirrorHelper.compressionHelper.addCompression,
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
        initThread(target=self.mirrorHelper.decompressionHelper.addDecompression,
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
            initThread(target=self.mirrorHelper.googleDriveHelper.addUpload,
                       name=f'{mirrorInfo.uid}-GoogleDriveUpload', mirrorInfo=mirrorInfo)
        if mirrorInfo.isMegaUpload:
            initThread(target=self.mirrorHelper.megaHelper.addUpload,
                       name=f'{mirrorInfo.uid}-MegaUpload', mirrorInfo=mirrorInfo)
        if mirrorInfo.isTelegramUpload:
            initThread(target=self.mirrorHelper.telegramHelper.addUpload,
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
        self.mirrorHelper.mirrorInfoDict[uid].eta = 0
        self.mirrorHelper.mirrorInfoDict[uid].progress = 0


class MirrorHelper:
    def __init__(self):
        self.mirrorInfoDict: typing.Dict[str, MirrorInfo] = {}
        self.mirrorListener: MirrorListener = MirrorListener(self)
        self.ariaHelper = AriaHelper(self)
        self.googleDriveHelper = GoogleDriveHelper(self)
        self.megaHelper = MegaHelper(self)
        self.telegramHelper = TelegramHelper(self)
        self.youTubeHelper = YouTubeHelper(self)
        self.compressionHelper = CompressionHelper(self)
        self.decompressionHelper = DecompressionHelper(self)
        self.statusHelper = StatusHelper(self)
        self.regexMagnet = r"magnet:\?xt=urn:btih:[a-zA-Z0-9]*"
        self.regexUrl = r"(?:(?:https?|ftp):\/\/)?[\w/\-?=%.]+\.[\w/\-?=%.]+"
        self.regexGoogleDriveUrl = r"https://drive\.google\.com/(drive)?/?u?/?\d?/?(mobile)?/?(file)?(folders)?/?d?/([-\w]+)[?+]?/?(w+)?"

    def addMirror(self, msg: telegram.Message):
        isDl: bool
        mirrorInfo: MirrorInfo
        isDl, mirrorInfo = self.genMirrorInfo(msg)
        logger.info(f'addMirror - [{isDl}] [{mirrorInfo.url}]')
        if isDl:
            logger.debug(vars(mirrorInfo))
            self.mirrorInfoDict[mirrorInfo.uid] = mirrorInfo
            self.mirrorListener.updateStatus(mirrorInfo.uid, MirrorStatus.addMirror)
            self.statusHelper.addStatus(msg)

    def cancelMirror(self, msg: telegram.Message):
        if self.mirrorInfoDict == {}:
            logger.info('No Active Downloads !')
            return
        uids: typing.List[str] = []
        try:
            msgTxt = msg.text.split(' ')[1].strip()
            if msgTxt == 'all':
                uids = list(self.mirrorInfoDict.keys())
            if msgTxt in self.mirrorInfoDict.keys():
                uids.append(msgTxt)
        except IndexError:
            replyTo = msg.reply_to_message
            if replyTo:
                msgId = replyTo.message_id
                for mirrorInfo in self.mirrorInfoDict.values():
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
        for uid in self.mirrorInfoDict.keys():
            mirrorInfo = self.mirrorInfoDict[uid]
            statusMsgTxt += f'{mirrorInfo.uid} {mirrorInfo.status}\n'
        return statusMsgTxt

    def genMirrorInfo(self, msg: telegram.Message):
        mirrorInfo: MirrorInfo = MirrorInfo(msg.message_id, msg.chat.id)
        mirrorInfo.isGoogleDriveUpload = True
        mirrorInfo.googleDriveUploadFolderId = envVarDict['googleDriveUploadFolderId']
        isDl: bool = True
        try:
            mirrorInfo.url = msg.text.split(' ')[1].strip()
            mirrorInfo.tag = msg.from_user.username
            mirrorInfo.googleDriveDownloadSourceId = self.getIdFromUrl(mirrorInfo.url)
            if mirrorInfo.googleDriveDownloadSourceId != '':
                mirrorInfo.isGoogleDriveDownload = True
            elif re.findall(self.regexMagnet, mirrorInfo.url):
                mirrorInfo.isMagnet = True
                mirrorInfo.isAriaDownload = True
            elif re.findall(self.regexUrl, mirrorInfo.url):
                mirrorInfo.isUrl = True
                mirrorInfo.isAriaDownload = True
            else:
                isDl = False
                logger.info('No Valid Link Provided !')
        except IndexError:
            replyTo = msg.reply_to_message
            if replyTo:
                mirrorInfo.tag = replyTo.from_user.username
                for media in [replyTo.document, replyTo.audio, replyTo.video]:
                    if media:
                        if media.mime_type == 'application/x-bittorrent':
                            mirrorInfo.isAriaDownload = True
                            mirrorInfo.url = media.get_file().file_path
                        else:
                            mirrorInfo.isTelegramDownload = True
                        break
            else:
                isDl = False
                logger.info('No Link Provided !')
        return isDl, mirrorInfo

    # TODO: check this method
    def getIdFromUrl(self, url: str):
        if 'folders' in url or 'file' in url:
            result = re.search(self.regexGoogleDriveUrl, url)
            return result.group(5)
        return ''


class AriaHelper:
    def __init__(self, mirrorHelper: 'MirrorHelper'):
        self.mirrorHelper = mirrorHelper
        self.api: aria2p.API = aria2p.API(aria2p.Client(host="http://localhost", port=6800,
                                                        secret=envVarDict['ariaRpcSecret']))
        self.ariaGidDict: typing.Dict[str, str] = {}

    def addDownload(self, mirrorInfo: MirrorInfo):
        if mirrorInfo.isMagnet:
            self.ariaGidDict[mirrorInfo.uid] = self.api.add_magnet(mirrorInfo.url, options={'dir': mirrorInfo.path}).gid
        if mirrorInfo.isUrl:
            self.ariaGidDict[mirrorInfo.uid] = self.api.add_uris([mirrorInfo.url], options={'dir': mirrorInfo.path}).gid

    def cancelDownload(self, uid: str):
        self.getDlObj(self.ariaGidDict[uid]).remove(force=True, files=True)
        self.ariaGidDict.pop(uid)

    def getUid(self, gid: str):
        for uid in self.ariaGidDict.keys():
            if gid == self.ariaGidDict[uid]:
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

    def onDownloadStart(self, _: aria2p.API, gid: str):
        self.mirrorHelper.mirrorInfoDict[self.getUid(gid)].initTotalSize(self.getDlObj(gid).total_length)

    def onDownloadPause(self, _: aria2p.API, gid: str):
        pass

    def onDownloadComplete(self, _: aria2p.API, gid: str):
        self.mirrorHelper.mirrorListener.updateStatus(self.getUid(gid), MirrorStatus.downloadComplete)

    def onDownloadStop(self, _: aria2p.API, gid: str):
        pass

    def onDownloadError(self, _: aria2p.API, gid: str):
        pass


class GoogleDriveHelper:
    def __init__(self, mirrorHelper: 'MirrorHelper'):
        self.mirrorHelper = mirrorHelper
        self.oauthCreds: google.oauth2.credentials.Credentials
        self.oauthScopes: typing.List[str] = ['https://www.googleapis.com/auth/drive']
        self.baseFileDownloadUrl: str = 'https://drive.google.com/uc?id={}&export=download'
        self.baseFolderDownloadUrl: str = 'https://drive.google.com/drive/folders/{}'
        self.googleDriveFolderMimeType: str = 'application/vnd.google-apps.folder'
        self.chunkSize: int = 32 * 1024 * 1024

    def addDownload(self, mirrorInfo: MirrorInfo):
        sourceId = mirrorInfo.googleDriveDownloadSourceId
        isFolder = False
        if self.getMetadataById(sourceId, 'mimeType') == self.googleDriveFolderMimeType:
            isFolder = True
        if isFolder:
            self.mirrorHelper.mirrorInfoDict[mirrorInfo.uid].initTotalSize(self.getSizeFolder(sourceId))
            if mirrorInfo.isGoogleDriveUpload:
                folderId = self.cloneFolder(sourceFolderId=sourceId, parentFolderId=mirrorInfo.googleDriveUploadFolderId)
                self.mirrorHelper.mirrorInfoDict[mirrorInfo.uid].uploadUrl = self.baseFolderDownloadUrl.format(folderId)
            else:
                self.downloadFolder(sourceFolderId=sourceId, dlPath=mirrorInfo.path)
        else:
            self.mirrorHelper.mirrorInfoDict[mirrorInfo.uid].initTotalSize(self.getSizeFile(sourceId))
            if mirrorInfo.isGoogleDriveUpload:
                fileId = self.cloneFile(sourceFileId=sourceId, parentFolderId=mirrorInfo.googleDriveUploadFolderId)
                self.mirrorHelper.mirrorInfoDict[mirrorInfo.uid].uploadUrl = self.baseFileDownloadUrl.format(fileId)
            else:
                self.downloadFile(sourceFileId=sourceId, dlPath=mirrorInfo.path)
        self.mirrorHelper.mirrorListener.updateStatus(mirrorInfo.uid, MirrorStatus.downloadComplete)

    def cancelDownload(self, uid: str):
        raise NotImplementedError

    def addUpload(self, mirrorInfo: MirrorInfo):
        if not mirrorInfo.isGoogleDriveDownload:
            uploadPath = os.path.join(mirrorInfo.path, os.listdir(mirrorInfo.path)[0])
            if os.path.isdir(uploadPath):
                folderId = self.uploadFolder(folderPath=uploadPath, parentFolderId=mirrorInfo.googleDriveUploadFolderId)
                self.mirrorHelper.mirrorInfoDict[mirrorInfo.uid].uploadUrl = self.baseFolderDownloadUrl.format(folderId)
            if os.path.isfile(uploadPath):
                fileId = self.uploadFile(filePath=uploadPath, parentFolderId=mirrorInfo.googleDriveUploadFolderId)
                self.mirrorHelper.mirrorInfoDict[mirrorInfo.uid].uploadUrl = self.baseFileDownloadUrl.format(fileId)
        else:
            time.sleep(self.mirrorHelper.statusHelper.statusUpdateInterval)
        self.mirrorHelper.mirrorListener.updateStatus(mirrorInfo.uid, MirrorStatus.uploadComplete)

    def cancelUpload(self, uid: str):
        raise NotImplementedError

    def authorizeApi(self):
        self.oauthCreds = google.oauth2.credentials.Credentials.from_authorized_user_file(tokenJsonFile,
                                                                                          self.oauthScopes)
        if not self.oauthCreds.valid:
            if self.oauthCreds.expired and self.oauthCreds.refresh_token:
                self.oauthCreds.refresh(google.auth.transport.requests.Request())
                logger.info('Google Drive API Token Refreshed !')
            else:
                logger.info('Google Drive API Token Needs to Refreshed Manually !')
                flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(credsJsonFile,
                                                                                           self.oauthScopes)

                self.oauthCreds = flow.run_local_server(port=0)
            with open(tokenJsonFile, 'w') as token:
                token.write(self.oauthCreds.to_json())
            if envVarDict['dynamicConfig'] == 'true':
                logger.info(self.patchFile(f"{envVarDict['CWD']}/{tokenJsonFile}"))
                updateFileidEnv()

    def buildService(self):
        return googleapiclient.discovery.build(serviceName='drive', version='v3', credentials=self.oauthCreds,
                                               cache_discovery=False)

    def uploadFile(self, filePath: str, parentFolderId: str):
        upStatus: googleapiclient.http.MediaUploadProgress
        service, fileName, fileMimeType, fileMetadata, mediaBody = self.getUpData(filePath, isResumable=True)
        fileMetadata['parents'] = [parentFolderId]
        fileOp = service.files().create(supportsAllDrives=True, body=fileMetadata, media_body=mediaBody)
        upResponse = None
        while upResponse is None:
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
        service = self.buildService()
        return service.files().copy(supportsAllDrives=True, fileId=sourceFileId, body=fileMetadata).execute()['id']

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
        service = self.buildService()
        fileOp = googleapiclient.http.MediaIoBaseDownload(fd=open(filePath, 'wb'), chunksize=self.chunkSize,
                                                          request=service.files().get_media(fileId=sourceFileId,
                                                                                            supportsAllDrives=True))
        downResponse = None
        while downResponse is None:
            downStatus, downResponse = fileOp.next_chunk()
        return downResponse['id']

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
        service = self.buildService()
        folderOp = service.files().create(supportsAllDrives=True, body=folderMetadata).execute()
        return folderOp['id']

    def deleteByUrl(self, url: str):
        contentId = self.mirrorHelper.getIdFromUrl(url)
        if contentId != '':
            service = self.buildService()
            service.files().delete(fileId=contentId, supportsAllDrives=True).execute()
            return f'Deleted: [{url}]'
        return 'Not a Valid Google Drive Link !'

    def getUpData(self, filePath: str, isResumable: bool):
        fileName = filePath.split('/')[-1]
        service = self.buildService()
        fileMimeType = magic.Magic(mime=True).from_file(filePath)
        fileMetadata = {'name': fileName, 'mimeType': fileMimeType}
        if isResumable:
            mediaBody = googleapiclient.http.MediaIoBaseUpload(fd=open(filePath, 'rb'), mimetype=fileMimeType,
                                                               resumable=True, chunksize=self.chunkSize)
        else:
            mediaBody = googleapiclient.http.MediaIoBaseUpload(fd=open(filePath, 'rb'), mimetype=fileMimeType,
                                                               resumable=False)
        return service, fileName, fileMimeType, fileMetadata, mediaBody

    def getMetadataById(self, sourceId: str, field: str):
        service = self.buildService()
        return service.files().get(supportsAllDrives=True, fileId=sourceId, fields=field).execute().get(field)

    def getFolderContentsById(self, folderId: str):
        service = self.buildService()
        query = f"'{folderId}' in parents"
        pageToken = None
        folderContents = []
        while True:
            result = service.files().list(supportsAllDrives=True, includeTeamDriveItems=True, spaces='drive',
                                          fields='nextPageToken, files(name, id, mimeType, size)',
                                          q=query, pageSize=200, pageToken=pageToken).execute()
            for content in result.get('files', []):
                folderContents.append(content)
            pageToken = result.get('nextPageToken', None)
            if not pageToken:
                break
        return folderContents

    def getSizeFile(self, fileId: str):
        sizeFile = int(self.getMetadataById(fileId, 'size'))
        return sizeFile

    def getSizeFolder(self, folderId: str):
        sizeFolder: int = 0
        folderContents = self.getFolderContentsById(folderId)
        if len(folderContents) != 0:
            for content in folderContents:
                if content.get('mimeType') == self.googleDriveFolderMimeType:
                    sizeFolder += self.getSizeFolder(content.get('id'))
                else:
                    sizeFolder += self.getSizeFile(content.get('id'))
        return sizeFolder

    def patchFile(self, filePath: str, fileId: str = ''):
        service, fileName, fileMimeType, fileMetadata, mediaBody = self.getUpData(filePath, isResumable=False)
        if fileId == '':
            fileId = envVarDict[getFileNameEnv(fileName)]
        fileOp = service.files().update(fileId=fileId, body=fileMetadata, media_body=mediaBody).execute()
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

    def addDownload(self, mirrorInfo: MirrorInfo):
        raise NotImplementedError

    def cancelDownload(self, uid: str):
        raise NotImplementedError

    def addUpload(self, mirrorInfo: MirrorInfo):
        raise NotImplementedError

    def cancelUpload(self, uid: str):
        raise NotImplementedError


class YouTubeHelper:
    def __init__(self, mirrorHelper: 'MirrorHelper'):
        self.mirrorHelper = mirrorHelper

    def addDownload(self, mirrorInfo: MirrorInfo):
        raise NotImplementedError

    def cancelDownload(self, uid: str):
        raise NotImplementedError


class CompressionHelper:
    def __init__(self, mirrorHelper: 'MirrorHelper'):
        self.mirrorHelper = mirrorHelper

    def addCompression(self, mirrorInfo: MirrorInfo):
        pass
        self.mirrorHelper.mirrorListener.updateStatus(mirrorInfo.uid, MirrorStatus.compressionComplete)

    def cancelCompression(self, uid: str):
        raise NotImplementedError


class DecompressionHelper:
    def __init__(self, mirrorHelper: 'MirrorHelper'):
        self.mirrorHelper = mirrorHelper

    def addDecompression(self, mirrorInfo: MirrorInfo):
        pass
        self.mirrorHelper.mirrorListener.updateStatus(mirrorInfo.uid, MirrorStatus.decompressionComplete)

    def cancelDecompression(self, uid: str):
        raise NotImplementedError


class StatusHelper:
    def __init__(self, mirrorHelper: 'MirrorHelper'):
        self.mirrorHelper = mirrorHelper
        self.isInitThread: bool = False
        self.isUpdateStatus: bool = False
        self.statusUpdateInterval: int = int(envVarDict['statusUpdateInterval'])
        self.msgId: int = 0
        self.chatId: int = 0
        self.lastStatusMsgId: int = 0
        self.lastStatusMsgTxt: str = ''

    def addStatus(self, msg: telegram.Message):
        if self.mirrorHelper.mirrorInfoDict != {}:
            self.isUpdateStatus = True
        else:
            self.isUpdateStatus = False
        if self.lastStatusMsgId == 0:
            self.isInitThread = True
        if self.lastStatusMsgId != 0:
            bot.deleteMessage(chat_id=self.chatId, message_id=self.lastStatusMsgId)
            self.lastStatusMsgId = -1
        self.msgId = msg.message_id
        self.chatId = msg.chat.id
        self.lastStatusMsgId = bot.sendMessage(text='...', parse_mode='HTML', chat_id=self.chatId,
                                               reply_to_message_id=self.msgId).message_id
        if self.isInitThread:
            self.isInitThread = False
            initThread(target=self.updateStatusMsg, name='statusUpdater')

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
            if self.mirrorHelper.mirrorInfoDict != {}:
                statusMsgTxt = ''
                for uid in self.mirrorHelper.mirrorInfoDict.keys():
                    mirrorInfo: MirrorInfo = self.mirrorHelper.mirrorInfoDict[uid]
                    statusMsgTxt += f'{uid} {mirrorInfo.status}\n{mirrorInfo.totalSizeStr}\n'
                if statusMsgTxt != self.lastStatusMsgTxt:
                    bot.editMessageText(text=statusMsgTxt, parse_mode='HTML', chat_id=self.chatId,
                                        message_id=self.lastStatusMsgId)
                    self.lastStatusMsgTxt = statusMsgTxt
                    time.sleep(self.statusUpdateInterval)
                time.sleep(1)
            if self.mirrorHelper.mirrorInfoDict == {}:
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
        initThread(target=self.mirrorHelper.mirrorListener.updateStatusCallback,
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
    Config = telegram.BotCommand(command='Config',
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


def initThread(target: typing.Callable, name: str, *args: object, **kwargs: object) -> None:
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
    fileUrl = 'https://docs.google.com/uc?export=download&id={}'.format(envVarDict[getFileNameEnv(fileName)])
    if os.path.exists(fileName):
        os.remove(fileName)
    subprocess.run(['aria2c', fileUrl, '--quiet=true', '--out=' + fileName])
    # intentional thread switching
    time.sleep(0.1)
    timeLapsed = 0.1
    while timeLapsed <= float(envVarDict['dlWaitTime']):
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


def checkEnvVar():
    global authorizedChatsList, configEnvFile, envVarDict, optEnvVarList, optEnvVarValList, reqEnvVarList
    fileReformat(configEnvFile)
    envVarDict = {**envVarDict, **loadDict(configEnvFile)}
    for reqEnvVar in reqEnvVarList:
        try:
            if envVarDict[reqEnvVar] in ['', ' ']:
                raise KeyError
        except KeyError:
            logger.error(f"Required Environment Variable Missing: '{reqEnvVar}' ! Exiting...")
    for i in range(len(optEnvVarList)):
        try:
            if envVarDict[optEnvVarList[i]] in ['', ' ']:
                raise KeyError
        except KeyError:
            envVarDict[optEnvVarList[i]] = optEnvVarValList[i]
    if envVarDict[optEnvVarList[0]] != '':
        for authorizedChat in envVarDict[optEnvVarList[0]].split(' '):
            authorizedChatsList.append(int(authorizedChat))


def checkRestart():
    global bot
    if os.path.exists(restartDumpFile):
        msgId, chatId = open(restartDumpFile, 'rt').readlines()[0].replace('\n', '').split(' ')
        bot.editMessageText(text='Bot Restarted Successfully !', parse_mode='HTML', chat_id=chatId, message_id=msgId)
        os.remove(restartDumpFile)


def configHandler():
    global configFileList, envVarDict, runningThreads
    if os.path.exists(dynamicEnvFile):
        envVarDict['dynamicConfig'] = 'true'
        logger.info('Using Dynamic Config...')
        envVarDict = {**envVarDict, **loadDict(dynamicEnvFile)}
        ariaDl(fileidEnvFile)
        envVarDict = {**envVarDict, **loadDict(fileidEnvFile)}
        for file in configFileList:
            fileHashInDict = envVarDict[getFileNameEnv(file) + 'Hash']
            if not (os.path.exists(file) and fileHashInDict == getFileHash(file)):
                initThread(target=ariaDl, name=f'{file}-ariaDl', fileName=file)
        while runningThreads:
            time.sleep(0.1)
    else:
        envVarDict['dynamicConfig'] = 'false'
        logger.info('Using Static Config...')
        envVarDict['dlWaitTime'] = '5'
    for file in configFileList:
        if not os.path.exists(file):
            logger.error(f"Config File Missing: '{file}' ! Exiting...")
            exit(1)


def fileBak(fileName: str):
    fileBakName = fileName + '.bak'
    try:
        shutil.copy(os.path.join(envVarDict['CWD'], fileName), os.path.join(envVarDict['CWD'], fileBakName))
        logger.info(f"Copied: '{fileName}' -> '{fileBakName}'")
    except FileNotFoundError:
        logger.error(FileNotFoundError)
        # TODO: remove exit maybe?
        exit(1)


def fileReformat(fileName: str):
    formatted = ''
    for line in open(fileName, 'r').readlines():
        commented = re.findall("^#", line)
        newline = re.findall("^\n", line)
        if not commented and not newline:
            formatted += line
    if open(fileName, 'r').read() != formatted:
        open(fileName, 'w').write(formatted)
        logger.info(f"Reformatted '{fileName}'")


def getChatUserId(update: telegram.Update):
    if update.message.reply_to_message:
        chatUserId = update.message.reply_to_message.from_user.id
        chatUserName = update.message.reply_to_message.from_user.first_name
    else:
        chatUserId = update.effective_chat.id
        chatUserName = update.effective_chat.first_name
    return chatUserId, chatUserName


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
    return f'{round(numBytes, 2)}{sizeUnits[i]}'


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


def initBotApi():
    global bot, dispatcher, updater
    updater = telegram.ext.Updater(token=envVarDict['botToken'], base_url="http://localhost:8081/bot")
    bot = updater.bot
    dispatcher = updater.dispatcher


def loadDat(fileName: str):
    lines = open(fileName, 'r').readlines()
    envName = []
    envValue = []
    for i in range(len(lines)):
        lineDat = lines[i].replace('\n', '').replace('"', '').split(' = ')
        envName.append(lineDat[0])
        envValue.append(lineDat[1])
    return envName, envValue


def loadDict(fileName: str):
    envName, envValue = loadDat(fileName)
    envDict = {}
    for i in range(len(envName)):
        envDict[envName[i]] = envValue[i]
    return envDict


def updateAuthorizedChats(chatUserId: int, auth: bool = None, unauth: bool = None):
    global authorizedChatsList
    if auth:
        authorizedChatsList.append(chatUserId)
    if unauth:
        authorizedChatsList.remove(chatUserId)
    authorizedChatsStr = ''
    for authorizedChat in authorizedChatsList:
        authorizedChatsStr += str(authorizedChat) + ' '
    authorizedChatsStr = authorizedChatsStr.strip()
    envVarDict[optEnvVarList[0]] = authorizedChatsStr
    updateConfigEnvFiles([optEnvVarList[0]], [envVarDict[optEnvVarList[0]]])


def updateConfigEnvFiles(newKeys: list, newVals: list):
    fileBak(configEnvFile)
    fileReformat(configEnvFile)
    updateDat(configEnvFile, newKeys, newVals)
    if envVarDict['dynamicConfig'] == 'true':
        logger.info(mirrorHelper.googleDriveHelper.patchFile(f"{envVarDict['CWD']}/{configEnvFile}"))
        logger.info(mirrorHelper.googleDriveHelper.patchFile(f"{envVarDict['CWD']}/{configEnvBakFile}"))
        updateFileidEnv()


def updateDat(fileName: str, newKeys: list, newVals: list):
    keyExists = False
    fileReformat(fileName)
    datKeys, datVals = loadDat(fileName)
    for n in range(len(newKeys)):
        for i in range(len(datKeys)):
            if datKeys[i] == newKeys[n]:
                keyExists = True
                datVals[i] = newVals[n]
        if not keyExists:
            datKeys.append(newKeys[n])
            datVals.append(newVals[n])
    datNew = ''
    for i in range(len(datKeys)):
        datNew += f'{datKeys[i]} = "{datVals[i]}"\n'
    open(fileName, 'w').write(datNew)


def updateFileidEnv():
    global configFileList, envVarDict, fileidEnvFile
    fileidEnvDat = ''
    for file in configFileList:
        fileNameEnv = getFileNameEnv(file)
        fileHashEnv = fileNameEnv + 'Hash'
        envVarDict[fileHashEnv] = getFileHash(os.path.join(envVarDict['CWD'], file))
        fileidEnvDat += f'{fileNameEnv} = "{envVarDict[fileNameEnv]}"\n'
        fileidEnvDat += f'{fileHashEnv} = "{envVarDict[fileHashEnv]}"\n'
    open(fileidEnvFile, 'wt').write(fileidEnvDat)
    logger.info(mirrorHelper.googleDriveHelper.patchFile(f"{envVarDict['CWD']}/{fileidEnvFile}"))


# loguru default format
# '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | '
# '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>'

runningThreads: typing.List[threading.Thread] = []
botStartTime: float = time.time()
bot: telegram.Bot
dispatcher: telegram.ext.Dispatcher
updater: telegram.ext.Updater
configEnvFile = 'config.env'
configEnvBakFile = configEnvFile + '.bak'
credsJsonFile = 'creds.json'
restartDumpFile = 'restart.dump'
tokenJsonFile = 'token.json'
dynamicEnvFile = 'dynamic.env'
fileidEnvFile = 'fileid.env'
configFileList: [str] = [configEnvFile, configEnvBakFile, credsJsonFile, tokenJsonFile]
reqEnvVarList: [str] = ['botToken', 'botOwnerId', 'telegramApiId', 'telegramApiHash', 'googleDriveUploadFolderId']
optEnvVarList: [str] = ['authorizedChats', 'ariaRpcSecret', 'dlRootDir', 'statusUpdateInterval']
optEnvVarValList: [str] = ['', 'tgmb-beta', 'dl', '5']
envVarDict: {str: str} = {'CWD': os.getcwd()}
logFiles: [str] = ['bot.log', 'botApi.log', 'aria.log', 'tqueue.binlog', 'webhooks_db.binlog']
logInfoFormat = '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <6}</level> | <k>{message}</k>'
logDebugFormat = '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | ' \
                 '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <k>{message}</k>'
authorizedChatsList: [int] = []
sizeUnits: [str] = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

warnings.filterwarnings("ignore")

if os.path.exists(logFiles[0]):
    os.remove(logFiles[0])

logger = loguru.logger
logger.remove()
logger.add(sys.stderr, level='INFO', format=logInfoFormat)
logger.add(logFiles[0], level='DEBUG', format=logDebugFormat, rotation='24h')
logger.disable('apscheduler')

logging.basicConfig(handlers=[InterceptHandler()], level=0)

configHandler()
checkEnvVar()
initBotApi()

mirrorHelper = MirrorHelper()

mirrorHelper.googleDriveHelper.authorizeApi()

dlRootDirPath = os.path.join(envVarDict['CWD'], envVarDict['dlRootDir'])

if os.path.exists(dlRootDirPath):
    shutil.rmtree(dlRootDirPath)
os.mkdir(dlRootDirPath)
