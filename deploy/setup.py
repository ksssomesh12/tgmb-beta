import googleapiclient.discovery
import googleapiclient.http
import google.auth.transport.requests
import google.oauth2.credentials
import google.oauth2.service_account
import google_auth_oauthlib.flow
import hashlib
import json
import magic
import os
import shutil
import subprocess
import time
import typing


def fileBak(fileName: str):
    fileBakName = fileName + '.bak'
    try:
        shutil.copy(os.path.join(os.getcwd(), fileName), os.path.join(os.getcwd(), fileBakName))
        print(f"Copied: '{fileName}' -> '{fileBakName}'")
    except FileNotFoundError:
        print(FileNotFoundError)
        exit(1)


def getFileHash(fileName: str):
    hashSum = hashlib.sha256()
    blockSize = 128 * hashSum.block_size
    fileStream = open(fileName, 'rb')
    fileChunk = fileStream.read(blockSize)
    while fileChunk:
        hashSum.update(fileChunk)
        fileChunk = fileStream.read(blockSize)
    return hashSum.hexdigest()


def jsonFileLoad(jsonFileName: str):
    return json.loads(open(jsonFileName, 'rt', encoding='utf-8').read())


def jsonFileWrite(jsonFileName: str, jsonDict: dict):
    open(jsonFileName, 'wt', encoding='utf-8').write(json.dumps(jsonDict, indent=2) + '\n')


def authorizeGoogleDriveApi():
    global oauthCreds, oauthScopes, useSaAuth
    if not useSaAuth:
        if not oauthCreds or not oauthCreds.valid:
            if oauthCreds and oauthCreds.expired and oauthCreds.refresh_token:
                oauthCreds.refresh(google.auth.transport.requests.Request())
            else:
                flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(credsJsonFile, oauthScopes)
                oauthCreds = flow.run_local_server(port=0)
            with open(tokenJsonFile, 'w') as token:
                token.write(oauthCreds.to_json())


def ariaDl(fileName: str):
    global envVars
    isDownloaded = False
    fileUrl = 'https://docs.google.com/uc?export=download&id={}'.format(envVars[getFileNameEnv(fileName)])
    if os.path.exists(fileName):
        os.remove(fileName)
    subprocess.run(['aria2c', fileUrl, '--quiet=true', '--out=' + fileName])
    timeLapsed = 0
    while timeLapsed <= 5.0:
        if os.path.exists(fileName):
            isDownloaded = True
            print(f"Downloaded '{fileName}'")
            break
        else:
            time.sleep(0.1)
            timeLapsed += 0.1
    if not isDownloaded:
        print(f"Can't Download File: '{fileName}' ! Exiting...")
        exit(1)


def fileUpload(fileName: str):
    global oauthCreds, envVars
    service = googleapiclient.discovery.build(serviceName='drive', version='v3',
                                              credentials=oauthCreds, cache_discovery=False)
    fileMimetype = magic.Magic(mime=True).from_file(fileName)
    fileMetadata = {'name': fileName, 'mimeType': fileMimetype, 'parents': [envVars['configFolderId']]}
    mediaBody = googleapiclient.http.MediaFileUpload(filename=fileName, mimetype=fileMimetype, resumable=False)
    fileOp = service.files().create(body=fileMetadata, media_body=mediaBody).execute()
    print(f"Uploaded: [{fileOp['id']}] [{fileName}] [{os.path.getsize(fileName)} bytes]")
    return fileOp['id']


def filePatch(fileName: str):
    global oauthCreds, envVars
    fileId = envVars[getFileNameEnv(fileName)]
    service = googleapiclient.discovery.build(serviceName='drive', version='v3',
                                              credentials=oauthCreds, cache_discovery=False)
    fileMimetype = magic.Magic(mime=True).from_file(fileName)
    fileMetadata = {'name': fileName, 'mimeType': fileMimetype}
    mediaBody = googleapiclient.http.MediaFileUpload(filename=fileName, mimetype=fileMimetype, resumable=False)
    fileOp = service.files().update(fileId=fileId, body=fileMetadata, media_body=mediaBody).execute()
    print(f"Synced: [{fileOp['id']}] [{fileName}] [{os.path.getsize(fileName)} bytes]")
    return fileOp['id']


def getFileNameEnv(fileName: str):
    splitList = fileName.split('.')
    fileIdEnvName = splitList[0]
    if len(splitList) > 1:
        for i in range(1, len(splitList)):
            fileIdEnvName += splitList[i].capitalize()
    return fileIdEnvName


def syncHandler():
    global configFiles, envVars, isUpdateConfig
    authorizeGoogleDriveApi()
    for file in [dynamicJsonFile, fileidJsonFile, configJsonBakFile]:
        if os.path.exists(file):
            os.remove(file)
    fileBak(configJsonFile)
    fileidJsonDict: typing.Dict[str, str] = {}
    for configFile in configFiles:
        varName = getFileNameEnv(configFile)
        fileidJsonDict[varName] = (filePatch(configFile) if isUpdateConfig else fileUpload(configFile))
        fileidJsonDict[varName + 'Hash'] = getFileHash(configFile)
    jsonFileWrite(fileidJsonFile, fileidJsonDict)
    dynamicJsonDict: typing.Dict[str, str] = \
        {'configFolderId': envVars['configFolderId'], 'dlWaitTime': input("Enter dlWaitTime (default is 5): "),
         getFileNameEnv(fileidJsonFile): (filePatch(fileidJsonFile) if isUpdateConfig else fileUpload(fileidJsonFile))}
    jsonFileWrite(dynamicJsonFile, dynamicJsonDict)
    (filePatch(dynamicJsonFile) if isUpdateConfig else fileUpload(dynamicJsonFile))


configJsonFile = 'config.json'
configJsonBakFile = configJsonFile + '.bak'
credsJsonFile = 'creds.json'
saJsonFile = 'sa.json'
tokenJsonFile = 'token.json'
dynamicJsonFile = 'dynamic.json'
fileidJsonFile = 'fileid.json'
configFiles: typing.List[str] = [configJsonFile, configJsonBakFile, credsJsonFile, saJsonFile, tokenJsonFile]
useSaAuth: bool
oauthCreds = None
oauthScopes: typing.List[str] = ['https://www.googleapis.com/auth/drive']
envVars: typing.Dict[str, str] = {}
isUpdateConfig = False

if os.path.exists(saJsonFile):
    useSaAuth = True
    for configFile in [credsJsonFile, tokenJsonFile]:
        configFiles.remove(configFile)
    oauthCreds = google.oauth2.service_account.Credentials.from_service_account_file(saJsonFile)
else:
    useSaAuth = False
    configFiles.remove(saJsonFile)
    if os.path.exists(tokenJsonFile):
        oauthCreds = google.oauth2.credentials.Credentials.from_authorized_user_file(tokenJsonFile, oauthScopes)

if input('Do You Want to Use Dynamic Config? (y/n): ').lower() == 'y':
    if input('Do You Want to Update Existing Config? (y/n): ').lower() == 'y':
        isUpdateConfig = True
        envVars[getFileNameEnv(dynamicJsonFile)] = input(f"Enter FileId of '{dynamicJsonFile}': ")
        ariaDl(dynamicJsonFile)
        envVars = {**envVars, **jsonFileLoad(dynamicJsonFile)}
        ariaDl(fileidJsonFile)
        envVars = {**envVars, **jsonFileLoad(fileidJsonFile)}
        for configFile in configFiles:
            if getFileNameEnv(configFile) in envVars.keys():
                ariaDl(configFile)
        if input('Make Necessary Changes to the Config Files in this Directory.\nContinue? (y/n): ').lower() != 'y':
            exit(1)
    else:
        envVars['configFolderId'] = input('Enter Google Drive Parent Folder ID: ')
    syncHandler()
    if input('Do You Want to Delete the Local Config Files? (y/n): ').lower() == 'y':
        for configFile in [*configFiles, fileidJsonFile, dynamicJsonFile]:
            os.remove(configFile)
else:
    authorizeGoogleDriveApi()
print('Setup Completed !')
exit(0)

# sample - dynamic.json
# ----- BEGINS ----- #
# {
#   "configFolderId": "",
#   "dlWaitTime": "",
#   "fileidJson": ""
# }
# ------ ENDS ------ #

# sample - fileid.json
# ----- BEGINS ----- #
# {
#   "configJson": "",
#   "configJsonHash": "",
#   "configJsonBak": "",
#   "configJsonBakHash": "",
# <-------------->
#   "credsJson": "",
#   "credsJsonHash": "",
#   "tokenJson": "",
#   "tokenJsonHash": ""
# <------or------>
#   "saJson": "",
#   "saJsonHash": ""
# <-------------->
# }
# ------ ENDS ------ #
