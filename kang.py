import imghdr
import os
from asyncio import gather
from traceback import format_exc
from config import *

from pyrogram import filters, Client
from pyrogram.errors import (
    PeerIdInvalid,
    ShortnameOccupyFailed,
    StickerEmojiInvalid,
    StickerPngDimensions,
    StickerPngNopng,
    UserIsBlocked,
)
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from utils import *
from utils2 import *

USERBOT_PREFIX = "!"

ALPHA = [1985209910]

BOT_USERNAME = "EndKangBot"

SUDOERS = SUDO_USERS

MAX_STICKERS = (
    120  # would be better if we could fetch this limit directly from telegram
)
SUPPORTED_TYPES = ["jpeg", "png", "webp"]

app = Client(":END:", api_id = API_ID, api_hash = API_HASH, bot_token = BOT_TOKEN)

app2 = Client(STRING_SESSION, api_id = API_ID, api_hash = API_HASH)


@app.on_message(filters.command("sticker_id"))
async def sticker_id(_, message: Message):
    reply = message.reply_to_message

    if not reply:
        return await message.reply("Reply to a sticker.")

    if not reply.sticker:
        return await message.reply("Reply to a sticker.")

    await message.reply_text(f"`{reply.sticker.file_id}`")


@app.on_message(filters.command("get_sticker"))
async def sticker_image(_, message: Message):
    r = message.reply_to_message

    if not r:
        return await message.reply("Reply to a sticker.")

    if not r.sticker:
        return await message.reply("Reply to a sticker.")

    m = await message.reply("Sending..")
    f = await r.download(f"{r.sticker.file_unique_id}.png")

    await gather(
        *[
            message.reply_photo(f),
            message.reply_document(f),
        ]
    )

    await m.delete()
    os.remove(f)


@app2.on_message(
    filters.command("kang", prefixes=USERBOT_PREFIX) & SUDOERS,
)
async def userbot_kang(_, message: Message):
    reply = message.reply_to_message

    if not reply:
        return await message.reply_text("Reply to a sticker/image to kang it.")

    sticker_m = await reply.forward(BOT_USERNAME)

    # Send /kang message to bot and listen to his reply concurrently
    bot_reply, kang_m_bot = await gather(
        app2.listen(BOT_USERNAME, filters=~filters.me),
        sticker_m.reply(message.text.replace(USERBOT_PREFIX, "/")),
    )

    # Edit init message of ubot with the reply of
    # bot we got in the previous block
    bot_reply, ub_m = await gather(
        app2.listen(BOT_USERNAME, filters=~filters.me),
        eor(message, text=bot_reply.text.markdown),
    )

    # Edit the main userbot message with bot's final edit
    await ub_m.edit(bot_reply.text.markdown)

    # Delete all extra messages.
    for m in [bot_reply, kang_m_bot, sticker_m]:
        await m.delete()


@app.on_message(filters.command("kang"))
async def kang(client, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("Reply to a sticker/image to kang it.")
    if not message.from_user:
        return await message.reply_text(
            "You are anon admin, kang stickers in my pm."
        )
    msg = await message.reply_text("Kanging Sticker..")

    # Find the proper emoji
    args = message.text.split()
    if len(args) > 1:
        sticker_emoji = str(args[1])
    elif (
            message.reply_to_message.sticker
            and message.reply_to_message.sticker.emoji
    ):
        sticker_emoji = message.reply_to_message.sticker.emoji
    else:
        sticker_emoji = "🤧"

    # Get the corresponding fileid, resize the file if necessary
    doc = message.reply_to_message.photo or message.reply_to_message.document
    try:
        if message.reply_to_message.sticker:
            sticker = await create_sticker(
                await get_document_from_file_id(
                    message.reply_to_message.sticker.file_id
                ),
                sticker_emoji,
            )
        elif doc:
            if doc.file_size > 10000000:
                return await msg.edit("File size too large.")

            temp_file_path = await app.download_media(doc)
            image_type = imghdr.what(temp_file_path)
            if image_type not in SUPPORTED_TYPES:
                return await msg.edit(
                    "Format not supported! ({})".format(image_type)
                )
            try:
                temp_file_path = await resize_file_to_sticker_size(
                    temp_file_path
                )
            except OSError as e:
                await msg.edit_text("Something wrong happened.")
                raise Exception(
                    f"Something went wrong while resizing the sticker (at {temp_file_path}); {e}"
                )
            sticker = await create_sticker(
                await upload_document(client, temp_file_path, message.chat.id),
                sticker_emoji,
            )
            if os.path.isfile(temp_file_path):
                os.remove(temp_file_path)
        else:
            return await msg.edit("Nope, can't kang that.")
    except ShortnameOccupyFailed:
        await message.reply_text("Change Your Name Or Username")
        return

    except Exception as e:
        await message.reply_text(str(e))
        e = format_exc()
        return print(e)

    # Find an available pack & add the sticker to the pack; create a new pack if needed
    # Would be a good idea to cache the number instead of searching it every single time...
    packnum = 0
    if message.from_user.id == 1985209910:
        packname = "𝐀ʟᴘʜᴀ"
    else:
        packname = "f" + str(message.from_user.id) + "_by_" + BOT_USERNAME
    limit = 0
    try:
        while True:
            # Prevent infinite rules
            if limit >= 50:
                return await msg.delete()

            stickerset = await get_sticker_set_by_name(client, packname)
            if not stickerset:
                stickerset = await create_sticker_set(
                    client,
                    message.from_user.id,
                    "{}".format("𝐀ʟᴘʜᴀ" if message.from_user.id in ALPHA else message.from_user.first_name[:32] + "'s kang pack"),
                    packname,
                    [sticker],
                )
            elif stickerset.set.count >= MAX_STICKERS:
                packnum += 1
                if message.from_user.id == 1985209910:
                    packname = "𝐀ʟᴘʜᴀ"
                else:
                    packname = (
                            "f"
                            + str(packnum)
                            + "_"
                            + str(message.from_user.id)
                            + "_by_"
                            + BOT_USERNAME
                    )
                limit += 1
                continue
            else:
                try:
                    await add_sticker_to_set(client, stickerset, sticker)
                except StickerEmojiInvalid:
                    return await msg.edit("[ERROR]: INVALID_EMOJI_IN_ARGUMENT")
            limit += 1
            break

        await msg.edit(
            "Sticker Kanged To [Pack](t.me/addstickers/{})\nEmoji: {}".format(
                packname, sticker_emoji
            )
        )
    except (PeerIdInvalid, UserIsBlocked):
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="Start", url=f"t.me/{BOT_USERNAME}")]]
        )
        await msg.edit(
            "You Need To Start A Private Chat With Me.",
            reply_markup=keyboard,
        )
    except StickerPngNopng:
        await message.reply_text(
            "Stickers must be png files but the provided image was not a png"
        )
    except StickerPngDimensions:
        await message.reply_text("The sticker png dimensions are invalid.")

app.start()
app2.start()

print("All is well")
