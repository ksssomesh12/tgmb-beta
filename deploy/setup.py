import googleapiclient.discovery
import googleapiclient.http
import google.auth.transport.requests
import google.oauth2.credentials
import google_auth_oauthlib.flow
import hashlib
import magic
import os
import re
import shutil
import subprocess
import time


def fileReformat(fileName: str):
    formatted = ''
    for line in open(fileName, 'r').readlines():
        commented = re.findall("^#", line)
        newline = re.findall("^\n", line)
        if not commented and not newline:
            formatted += line
    if open(fileName, 'r').read() != formatted:
        open(fileName, 'w').write(formatted)
        print(f"Reformatted '{fileName}'")


def fileBak(fileName: str):
    fileBakName = fileName + '.bak'
    try:
        shutil.copy(os.path.join(os.getcwd(), fileName), os.path.join(os.getcwd(), fileBakName))
        print(f"Copied: '{fileName}' -> '{fileBakName}'")
    except FileNotFoundError:
        print(FileNotFoundError)
        exit(1)


def loadDict(fileName: str):
    lines = open(fileName, 'r').readlines()
    envDict = {}
    for i in range(len(lines)):
        lineDat = lines[i].replace('\n', '').replace('"', '').split(' = ')
        envDict[lineDat[0]] = lineDat[1]
    return envDict


def getFileHash(fileName: str):
    hashSum = hashlib.sha256()
    blockSize = 128 * hashSum.block_size
    fileStream = open(fileName, 'rb')
    fileChunk = fileStream.read(blockSize)
    while fileChunk:
        hashSum.update(fileChunk)
        fileChunk = fileStream.read(blockSize)
    return hashSum.hexdigest()


def authorizeGoogleDriveApi():
    global creds, SCOPES
    if os.path.exists(tokenJsonFile):
        creds = google.oauth2.credentials.Credentials.from_authorized_user_file(tokenJsonFile, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(credsJsonFile, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(tokenJsonFile, 'w') as token:
            token.write(creds.to_json())


def ariaDl(fileName: str):
    global envVarDict
    isDownloaded = False
    fileUrl = f"https://docs.google.com/uc?export=download&id={envVarDict[fileName.upper().replace('.', '_')]}"
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
    global creds, envVarDict
    service = googleapiclient.discovery.build(serviceName='drive', version='v3',
                                              credentials=creds, cache_discovery=False)
    fileMimetype = magic.Magic(mime=True).from_file(fileName)
    fileMetadata = {'name': fileName, 'mimeType': fileMimetype, 'parents': [envVarDict['CONFIG_FOLDER_ID']]}
    mediaBody = googleapiclient.http.MediaFileUpload(filename=fileName, mimetype=fileMimetype, resumable=False)
    fileOp = service.files().create(body=fileMetadata, media_body=mediaBody).execute()
    print(f"Uploaded: [{fileOp['id']}] [{fileName}] [{os.path.getsize(fileName)} bytes]")
    return fileOp['id']


def filePatch(fileName: str):
    global creds, envVarDict
    fileId = envVarDict[fileName.upper().replace('.', '_')]
    service = googleapiclient.discovery.build(serviceName='drive', version='v3',
                                              credentials=creds, cache_discovery=False)
    fileMimetype = magic.Magic(mime=True).from_file(fileName)
    fileMetadata = {'name': fileName, 'mimeType': fileMimetype}
    mediaBody = googleapiclient.http.MediaFileUpload(filename=fileName, mimetype=fileMimetype, resumable=False)
    fileOp = service.files().update(fileId=fileId, body=fileMetadata, media_body=mediaBody).execute()
    print(f"Synced: [{fileOp['id']}] [{fileName}] [{os.path.getsize(fileName)} bytes]")
    return fileOp['id']


def syncHandler():
    global configSyncList, envVarDict, isUpdateConfig
    authorizeGoogleDriveApi()
    for file in [dynamicEnvFile, fileidEnvFile, configEnvBakFile]:
        if os.path.exists(file):
            os.remove(file)
    fileBak(configEnvFile)
    fileReformat(configEnvFile)
    fileidEnvFileDat = ''
    for fileName in configSyncList[0:4]:
        varName = fileName.upper().replace(".", "_")
        if isUpdateConfig:
            fileidEnvFileDat += f'{varName} = "{filePatch(fileName)}"\n'
        else:
            fileidEnvFileDat += f'{varName} = "{fileUpload(fileName)}"\n'
        fileidEnvFileDat += f'{varName}_HASH = "{getFileHash(fileName)}"\n'
    open(fileidEnvFile, 'w').write(fileidEnvFileDat)
    dynamicEnvFileDat = f'CONFIG_FOLDER_ID = "{envVarDict["CONFIG_FOLDER_ID"]}"\n'
    dynamicEnvFileDat += f'DL_WAIT_TIME = "{input("Enter DL_WAIT_TIME (default is 5): ")}"\n'
    if isUpdateConfig:
        dynamicEnvFileDat += f'{fileidEnvFile.upper().replace(".", "_")} = "{filePatch(fileidEnvFile)}"\n'
    else:
        dynamicEnvFileDat += f'{fileidEnvFile.upper().replace(".", "_")} = "{fileUpload(fileidEnvFile)}"\n'
    open(dynamicEnvFile, 'w').write(dynamicEnvFileDat)
    if isUpdateConfig:
        filePatch(dynamicEnvFile)
    else:
        fileUpload(dynamicEnvFile)


configEnvFile = 'config.env'
configEnvBakFile = configEnvFile + '.bak'
credsJsonFile = 'creds.json'
tokenJsonFile = 'token.json'
dynamicEnvFile = 'dynamic.env'
fileidEnvFile = 'fileid.env'
configSyncList = [configEnvFile, configEnvBakFile, credsJsonFile, tokenJsonFile, fileidEnvFile, dynamicEnvFile]
creds = None
SCOPES = ['https://www.googleapis.com/auth/drive']
envVarDict = {}
isUpdateConfig = False

if input('Do You Want to Use Dynamic Config? (y/n): ').lower() == 'y':
    if input('Do You Want to Update Existing Config? (y/n): ').lower() == 'y':
        isUpdateConfig = True
        envVarDict[dynamicEnvFile.upper().replace('.', '_')] = input(f"Enter FileId of '{dynamicEnvFile}': ")
        ariaDl(dynamicEnvFile)
        envVarDict = {**envVarDict, **loadDict(dynamicEnvFile)}
        ariaDl(fileidEnvFile)
        envVarDict = {**envVarDict, **loadDict(fileidEnvFile)}
        for file in configSyncList[0:4]:
            ariaDl(file)
        if input('Make Necessary Changes to the Config Files in this Directory.\nContinue? (y/n): ').lower() != 'y':
            exit(1)
    else:
        envVarDict['CONFIG_FOLDER_ID'] = input('Enter Google Drive Parent Folder ID: ')
    syncHandler()
    if input('Do You Want to Delete the Local Config Files? (y/n): ').lower() == 'y':
        for file in configSyncList:
            os.remove(file)
else:
    authorizeGoogleDriveApi()
print('Setup Completed !')
exit(0)

# sample - dynamic.env
# --- BEGINS --- #
# CONFIG_FOLDER_ID = ""
# DL_WAIT_TIME = ""
# FILEID_ENV = ""
# --- ENDS --- #

# sample - fileid.env
# --- BEGINS --- #
# CONFIG_ENV = ""
# CONFIG_ENV_HASH = ""
# CONFIG_ENV_BAK = ""
# CONFIG_ENV_BAK_HASH = ""
# CREDENTIALS_JSON = ""
# CREDENTIALS_JSON_HASH = ""
# TOKEN_JSON = ""
# TOKEN_JSON_HASH = ""
# --- ENDS --- #
