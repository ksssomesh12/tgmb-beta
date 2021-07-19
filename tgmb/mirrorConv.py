from . import *


# TODO: reduce the code for this function if possible
def getMirrorInfoStr():
    global mirrorInfo
    mirrorInfoStr = f'[uid | {mirrorInfo.uid}]\n'
    if mirrorInfo.isAriaDownload:
        mirrorInfoStr += f'[isAriaDownload | True]\n'
    elif mirrorInfo.isGoogleDriveDownload:
        mirrorInfoStr += f'[isGoogleDriveDownload | True]\n'
    elif mirrorInfo.isMegaDownload:
        mirrorInfoStr += f'[isMegaDownload | True]\n'
    elif mirrorInfo.isTelegramDownload:
        mirrorInfoStr += f'[isTelegramDownload | True]\n'
    elif mirrorInfo.isYouTubeDownload:
        mirrorInfoStr += f'[isYouTubeDownload | True]\n'
    if mirrorInfo.isGoogleDriveUpload:
        mirrorInfoStr += f'[isGoogleDriveUpload | True]\n'
    elif mirrorInfo.isMegaUpload:
        mirrorInfoStr += f'[isMegaUpload | True]\n'
    elif mirrorInfo.isTelegramUpload:
        mirrorInfoStr += f'[isTelegramUpload | True]\n'
    if mirrorInfo.isCompress:
        mirrorInfoStr += f'[isCompress | True]\n'
    elif mirrorInfo.isDecompress:
        mirrorInfoStr += f'[isDecompress | True]\n'
    if mirrorInfo.isGoogleDriveUpload:
        mirrorInfoStr += f'[googleDriveUploadFolderId | {mirrorInfo.googleDriveUploadFolderId}]'
    return mirrorInfoStr


def stageZero(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    global mirrorInfo
    isValidDl, mirrorInfo = mirrorHelper.genMirrorInfo(update.message)
    if isValidDl:
        # <setDefaults>
        mirrorInfo.isGoogleDriveUpload = True
        mirrorInfo.googleDriveUploadFolderId = googleDriveUploadFolderIds[0]
        # </setDefaults>
        update.message.reply_text(text=getMirrorInfoStr(), reply_to_message_id=update.message.message_id,
                                  reply_markup=InlineKeyboardMaker(['Use Defaults', 'Customize']).build(1))
        return FIRST
    else:
        update.message.reply_text(text='No Valid Link Provided !', reply_to_message_id=update.message.message_id)
        return telegram.ext.ConversationHandler.END


def stageOne(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == '1':
        logger.info(f"addMirror - ['{mirrorInfo.url}']")
        mirrorHelper.addMirror(mirrorInfo)
        query.edit_message_text(text='addMirror Succeeded !')
        return telegram.ext.ConversationHandler.END
    elif query.data == '2':
        buttonList = ['Google Drive', 'Mega', 'Telegram']
        query.edit_message_text(text='Choose Upload Location:', reply_markup=InlineKeyboardMaker(buttonList).build(1))
        return SECOND


def stageTwo(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == '1':
        buttonList = [*googleDriveUploadFolderDescriptions]
        query.edit_message_text(text='Choose `googleDriveUploadFolder`:',
                                reply_markup=InlineKeyboardMaker(buttonList).build(1))
        return THIRD
    elif query.data in ['2', '3']:
        mirrorInfo.isGoogleDriveUpload = False
        mirrorInfo.googleDriveUploadFolderId = ''
        if query.data == '2':
            mirrorInfo.isMegaUpload = True
        elif query.data == '3':
            mirrorInfo.isTelegramUpload = True
        buttonList = ['isCompress', 'isDecompress', 'Skip']
        query.edit_message_text(text='Choose:', reply_markup=InlineKeyboardMaker(buttonList).build(1))
        return FOURTH


def stageThree(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    mirrorInfo.googleDriveUploadFolderId = googleDriveUploadFolderIds[(int(query.data) - 1)]
    buttonList = ['isCompress', 'isDecompress', 'Skip']
    query.edit_message_text(text='Choose:', reply_markup=InlineKeyboardMaker(buttonList).build(1))
    return FOURTH


def stageFour(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == '1':
        mirrorInfo.isCompress = True
    elif query.data == '2':
        mirrorInfo.isDecompress = True
    buttonList = ['Proceed', 'Cancel']
    query.edit_message_text(text=getMirrorInfoStr(), reply_markup=InlineKeyboardMaker(buttonList).build(1))
    return FIFTH


def stageFive(update: telegram.Update, _: telegram.ext.CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == '1':
        logger.info(f"addMirror - ['{mirrorInfo.url}']")
        mirrorHelper.addMirror(mirrorInfo)
        query.edit_message_text(text='addMirror Succeeded !')
    elif query.data == '2':
        query.edit_message_text(text='addMirror Cancelled !')
    return telegram.ext.ConversationHandler.END


mirrorInfo: MirrorInfo
FIRST, SECOND, THIRD, FOURTH, FIFTH = range(5)

handler = telegram.ext.ConversationHandler(
    # TODO: filter - restrict to user who sent MirrorCommand
    entry_points=[telegram.ext.CommandHandler(BotCommands.Mirror.command, stageZero)],
    states={
        # ZEROTH
        # Choose to Modify or Use Default Values
        FIRST: [telegram.ext.CallbackQueryHandler(stageOne)],
        # Choose Upload Location
        SECOND: [telegram.ext.CallbackQueryHandler(stageTwo)],
        # Choose googleDriveUploadFolder
        THIRD: [telegram.ext.CallbackQueryHandler(stageThree)],
        # Choose Compress / Decompress
        FOURTH: [telegram.ext.CallbackQueryHandler(stageFour)],
        # Confirm and Proceed / Cancel
        FIFTH: [telegram.ext.CallbackQueryHandler(stageFive)]
    },
    # TODO: filter - restrict to user who sent MirrorCommand
    fallbacks=[telegram.ext.CommandHandler(BotCommands.Config.command, stageZero)],
    conversation_timeout=120,
    run_async=True
)
