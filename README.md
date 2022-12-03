# tgmb-beta

[![build-docker-image](https://github.com/ksssomesh12/tgmb-beta/actions/workflows/build-docker-image.yml/badge.svg)](https://github.com/ksssomesh12/tgmb-beta/actions/workflows/build-docker-image.yml)

# Description

A Telegram Bot to Mirror Files to Cloud Drives

# Credits

- This project is a full rewrite from scratch of the following independent project.

  > [python-aria-mirror-bot](https://github.com/lzzy12/python-aria-mirror-bot)

  All credits go to the maintainers of this project.


- Few additional features have been implemented on top of the above project.

# Dependencies

- This project uses the following C++ projects as build dependencies.

  > [megasdk](https://github.com/meganz/sdk)

  > [qbittorrent](https://github.com/qbittorrent/qBittorrent)

  > [telegram-bot-api](https://github.com/tdlib/telegram-bot-api)

- This project uses the following Python projects as package dependencies.

  > [aria2p](https://github.com/pawamoy/aria2p)

  > [google-auth-httplib2](https://github.com/GoogleCloudPlatform/google-auth-library-python-httplib2)

  > [google-auth-oauthlib](https://github.com/GoogleCloudPlatform/google-auth-library-python-oauthlib)

  > [google-api-python-client](https://github.com/googleapis/google-api-python-client/)

  > [psutil](https://github.com/giampaolo/psutil)

  > [python-magic](http://github.com/ahupp/python-magic)

  > [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)

  > [qbittorrent-api](https://github.com/rmartin16/qbittorrent-api)

  > [torrentool](https://github.com/idlesign/torrentool)

  > [youtube_dl](https://github.com/ytdl-org/youtube-dl)

# Features

## Basic

- mirror direct links
- mirror metalinks
- mirror torrents
- mirror telegram files
- mirror files after archiving/unarchiving
- download and upload progress, connection speeds and eta(s)
- docker support
- support for service accounts and team drives in google drive
- mirror 'youtube-dl' supported urls

## Additional

- support for editing config file dynamically on-the-fly
- sync config files to google drive at every restart
- helper processes { aria2c, qbittorrent-nox, telegram-bot-api } are started as child processes self-handled by the python module
- support for using custom tracker list for qbittorrent

# Configuration

## Required

- **botToken** - botToken
- **botOwnerId** - botOwnerId
- **telegramApiId** - telegramApiId
- **telegramApiHash** - telegramApiHash
- **googledriveAuth** - googleDriveAuth
- **googleDriveUploadFolderIds** - googleDriveUploadFolderIds

## Optional

- **ariaConf** - ariaConf
- **authorizedChats** - authorizedChats
- **dlRootDir** - dlRootDir
- **logLevel** - logLevel
- **megaAuth** - megaAuth
- **qbitTorrentConf** - qbitTorrentConf
- **statusUpdateInterval** - statusUpdateInterval
- **trackersListUrl** - trackersListUrl
- **ytdlFormat** - ytdlFormat

# Samples

## `config.json`

```json
{
  "botToken": "",
  "botOwnerId": "",
  "telegramApiId": "",
  "telegramApiHash": "",
  "googleDriveAuth": {
    "authType": "",
    "authInfos": {
      "credsJson": {
        "installed": {
          "client_id": "",
          "project_id": "",
          "auth_uri": "",
          "token_uri": "",
          "auth_provider_x509_cert_url": "",
          "client_secret": "",
          "redirect_uris": [
            "",
            ""
          ]
        }
      },
      "saJson": {
        "type": "",
        "project_id": "",
        "private_key_id": "",
        "private_key": "",
        "client_email": "",
        "client_id": "",
        "auth_uri": "",
        "token_uri": "",
        "auth_provider_x509_cert_url": "",
        "client_x509_cert_url": ""
      },
      "tokenJson": {
        "token": "",
        "refresh_token": "",
        "token_uri": "",
        "client_id": "",
        "client_secret": "",
        "scopes": [
          ""
        ],
        "expiry": ""
      }
    }
  },
  "googleDriveUploadFolderIds": {
    "#folderId-01": "#folderDescription-01",
    "#folderId-02": "#folderDescription-02",
    "#folderId-03": "#folderDescription-03",
    "#folderId-04": "#folderDescription-04",
    "#folderId-05": "#folderDescription-05"
  },
  "ariaConf": {
    "allow-overwrite": "true",
    "follow-torrent": "false",
    "max-connection-per-server": "8",
    "min-split-size": "8M",
    "split": "8"
  },
  "authorizedChats": {
    "#chatId-01": {
      "chatType": "#chatType-01",
      "chatName": "#chatName-01"},
    "#chatId-02": {
      "chatType": "#chatType-02",
      "chatName": "#chatName-02"},
    "#chatId-03": {
      "chatType": "#chatType-03",
      "chatName": "#chatName-03"},
    "#chatId-04": {
      "chatType": "#chatType-04",
      "chatName": "#chatName-04"},
    "#chatId-05": {
      "chatType": "#chatType-05",
      "chatName": "#chatName-05"}
  },
  "dlRootDir": "dl",
  "logLevel": "INFO",
  "megaAuth": {
    "apiKey": "",
    "emailId": "",
    "passPhrase": ""
  },
  "qbitTorrentConf": {
    "BitTorrent": {
      "Session": {
        "AsyncIOThreadsCount": "8",
        "MultiConnectionsPerIp": "true",
        "SlowTorrentsDownloadRate": "100",
        "SlowTorrentsInactivityTimer": "600"
      }
    },
    "LegalNotice": {
      "": {
        "Accepted": "true"
      }
    },
    "Preferences": {
      "Advanced": {
        "AnnounceToAllTrackers": "true",
        "AnonymousMode": "false",
        "IgnoreLimitsLAN": "true",
        "RecheckOnCompletion": "true",
        "LtTrackerExchange": "true"
      },
      "Bittorrent": {
        "AddTrackers": "false",
        "DHT": "true",
        "DHTPort": "6881",
        "LSD": "true",
        "MaxConnecs": "-1",
        "MaxConnecsPerTorrent": "-1",
        "MaxUploads": "-1",
        "MaxUploadsPerTorrent": "-1",
        "PeX": "true",
        "sameDHTPortAsBT": "true"
      },
      "Downloads": {
        "DiskWriteCacheSize": "32",
        "PreAllocation": "true",
        "UseIncompleteExtension": "true"
      },
      "General": {
        "PreventFromSuspendWhenDownloading": "true"
      },
      "Queueing": {
        "IgnoreSlowTorrents": "true",
        "MaxActiveDownloads": "100",
        "MaxActiveTorrents": "50",
        "MaxActiveUploads": "50",
        "QueueingEnabled": "false"
      },
      "WebUI": {
        "Enabled": "true",
        "Port": "8400",
        "LocalHostAuth": "false"
      }
    }
  },
  "statusUpdateInterval": "5",
  "trackersListUrl": "https://trackerslist.com/all.txt",
  "ytdlFormat": "best/bestvideo+bestaudio"
}
```

## `dynamic.json`

```json
{
  "configFolderId": "",
  "dlWaitTime": "",
  "fileidJsonId": ""
}
```

## `fileid.json`

```json
{
  "configJsonId": "",
  "configJsonHash": "",
  "configJsonBakId": "",
  "configJsonBakHash": ""
}
```

# Deployment

## Bot Commands

```text
start - start the bot
help - show the help message
stats - show the statistics of the bot host machine
ping - ping the bot host machine
restart - restart the bot
log - send the log files of the bot
mirror - mirror any url/torrent/metalink to cloud drive
status - show the status of all mirrors in progress
cancel - cancel a mirror in progress
list - list contents of a folder in cloud drive
delete - delete
authorize - authorize a user/group to use the bot
unauthorize - unauthorize a user/group to use the bot
sync - sync config file to cloud drive
config - edit config file
```

**NOTE**: The above listed command with descriptions can be copied and pasted in 'edit bot commands' section prompt, when editing the bot settings with [@BotFather](https://t.me/botfather)
