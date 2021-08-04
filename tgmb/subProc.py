from . import *

ariaDaemon: subprocess.Popen
botApiServer: subprocess.Popen

botApiServerStartCmd = [f"telegram-bot-api", f"--local", f"--verbosity=9",
                        f"--api-id={envVarDict['telegramApiId']}", f"--api-hash={envVarDict['telegramApiHash']}",
                        f"--log={os.path.join(envVarDict['cwd'], logFiles[1])}"]
ariaDaemonStartCmd = [f"aria2c", "--daemon", "--enable-rpc", f"--rpc-secret={envVarDict['ariaRpcSecret']}",
                      f"--follow-torrent=mem", f"--check-certificate=false", f"--max-connection-per-server=10",
                      f"--rpc-max-request-size=1024M", f"--min-split-size=10M", f"--allow-overwrite=true",
                      f"--bt-max-peers=0", f"--seed-time=0.01", f"--split=10", f"--max-overall-upload-limit=1K",
                      f"--bt-tracker=$(aria2c 'https://trackerslist.com/all_aria2.txt' --quiet=true"
                      f"--allow-overwrite=true --out=trackerslist.txt --check-certificate=false; cat trackerslist.txt)",
                      f"--log={os.path.join(envVarDict['cwd'], logFiles[2])}"]


def botApiServerStart():
    global botApiServer
    botApiServer = subprocess.Popen(botApiServerStartCmd)
    logger.info(f"botApiServer started (pid {botApiServer.pid})")


def ariaDaemonStart():
    global ariaDaemon
    ariaDaemon = subprocess.Popen(ariaDaemonStartCmd)
    logger.info(f"ariaDaemon started (pid {ariaDaemon.pid})")


def botApiServerStop():
    global botApiServer
    botApiServer.terminate()
    logger.info(f"botApiServer terminated (pid {botApiServer.pid})")


def ariaDaemonStop():
    global ariaDaemon
    ariaDaemon.terminate()
    logger.info(f"ariaDaemon terminated (pid {ariaDaemon.pid})")


def delLogFiles():
    for file in logFiles[1:]:
        if os.path.exists(file):
            os.remove(file)
            logger.debug(f"Deleted: '{file}'")


def procKill(procList: list):
    for procName in procList:
        stdout = subprocess.run(['pkill', procName, '-e'],
                                stdout=subprocess.PIPE).stdout.decode('utf-8').replace('\n', ' ')
        if stdout not in ['', ' ']:
            logger.debug(stdout)


def init():
    procKill(['aria2c', 'telegram-bot-a'])
    delLogFiles()
    botApiServerStart()
    ariaDaemonStart()


def term():
    ariaDaemonStop()
    botApiServerStop()
    delLogFiles()
    procKill(['aria2c'])
