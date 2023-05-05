import discord
import logging as lg
import os
import re
import uuid
from discord.ext import commands
from discord import app_commands
from googletrans import Translator
from googletrans.constants import LANGUAGES
from paddleocr import PaddleOCR
from util.vars.eind_vars import CHANNEL_IGNORE_LIST

translator = Translator()

TRANSLATE_LANGUAGES = [
    app_commands.Choice(name="English", value="english"),
    app_commands.Choice(name="Dutch", value="dutch"),
    app_commands.Choice(name="German", value="german"),
    app_commands.Choice(name="Arabic", value="arabic"),
    app_commands.Choice(name="French", value="french"),
    app_commands.Choice(name="Spanish", value="spanish"),
    app_commands.Choice(name="Esperanto", value="esperanto"),
]

TRANSLATE_PROMPT_REGEX = r"(?:tr|translate) (.+) to (.+)"


class Translate(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.ctx_menu = app_commands.ContextMenu(
            name='Translate Message',
            callback=self.translate_context,
        )
        self.client.tree.add_command(self.ctx_menu)

    @commands.Cog.listener()
    async def on_ready(self):
        lg.info(f"[{__name__}] Cog is ready")

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author == self.client.user:
            return
        if msg.channel.id in CHANNEL_IGNORE_LIST:
            return

        message_content = msg.content.lower()

        calc_pattern = re.compile(TRANSLATE_PROMPT_REGEX)
        matches = calc_pattern.match(message_content)

        if (matches):
            try:
                req = matches.group(1)
                lang = matches.group(2)
                translated = TranslateUtil.translate_text(req, src='auto',
                                                          dst=lang)
            except ValueError as e:
                name = msg.author.name
                lg.error(f'Failed to translate \"{req}\" to {lang} for {name}')
                lg.debug(e)
                await msg.reply('Destination language invalid. Check typos.')
            else:
                await msg.reply(f"{translated.text}")
                lg.info("Translated text for %s", msg.author.name)

    async def translate_context(self, intr: discord.Interaction,
                                msg: discord.Message):
        tr = TranslateUtil.translate_text(msg.content, None)

        lang = LANGUAGES[tr.src]

        translate_msg = "Translation for \"%s\" from (%s):\n\n%s"
        log_msg = "Sent translation to %s for message \"%s\" by %s"

        await intr.response.send_message(
            content=translate_msg % (msg.content, lang.capitalize(), tr.text),
            ephemeral=True)
        lg.info(log_msg % (intr.user.name, msg.content, msg.author.name))

    @commands.command(aliases=[])
    async def tr(self, ctx, *args):
        src = None if not args else args[0]

        if ctx.message.reference:
            translated = TranslateUtil.translate_text(
                ctx.message.reference.resolved.content, src)
            lang = LANGUAGES[translated.src].capitalize()
            payload = f"Translated from ({lang}): {translated.text}"
            await ctx.message.reference.resolved.reply(payload)
            lg.info('Sent translation to %s', ctx.message.author.name)
            return
        await ctx.message.reply(
            "\"!tr\" can only be used as a reply to another message")

    @commands.command(aliases=[])
    async def trimg(self, ctx, *args):
        file_dir = os.getenv('FILE_DIR')
        src = None if not args else args[0]
        ocr = PaddleOCR(use_angle_cls=True, lang='en',
                        det_model_dir=f"{file_dir}/ocr")

        if ctx.message.reference:
            imgs = []
            msg = ""
            for attachment in ctx.message.reference.resolved.attachments:
                if "image" in attachment.content_type:
                    imgname = f"temp/{uuid.uuid4()}{attachment.filename}"
                    os.makedirs(os.path.dirname(imgname), exist_ok=True)
                    await attachment.save(imgname)
                    imgs.append(imgname)
            for idx, img in enumerate(imgs, start=1):
                result = ocr.ocr(img, cls=True)
                lines = []

                for idxres, res in enumerate(result):
                    res = result[idxres]
                    img_txt = '\n'.join(["> " + x[1][0] for x in res])
                    translated = TranslateUtil.translate_text(img_txt, src)
                    lines.append(translated.text)

                lang = LANGUAGES[translated.src].capitalize()
                img_msg = "**Image %s (translated from %s)**\n\n%s\n\n"
                msg += img_msg % (idx, lang, '\n'.join(lines))
                os.remove(img)

            await ctx.message.reference.resolved.reply(msg)
            lg.info("Sent image translation to %s", ctx.message.author.name)

    @app_commands.command(name="translate",
                          description="Translate a specific text.")
    @app_commands.choices(src=TRANSLATE_LANGUAGES, dst=TRANSLATE_LANGUAGES)
    async def translate(self, intr: discord.Interaction,
                        text: str,
                        src: app_commands.Choice[str],
                        dst: app_commands.Choice[str]):
        tr = TranslateUtil.translate_text(text, src.value, dst.value)
        await intr.response.send_message(
            f"Translation of _\"{text}\"_ from"
            f" _{src.name}_ to _{dst.name}_: {tr.text}")
        lg.info("Translated text for %s", intr.user.name)


class TranslateUtil:
    @staticmethod
    def translate_text(message, src, dst=None):
        if not dst:
            dst = 'english'
        translated = translator.translate(message) if not src \
            else translator.translate(message, src=src, dest=dst)

        return translated

    @staticmethod
    def cleanup(text: str):
        text = text.replace("\n\n", "\n---\n")
        text = text.replace("\n", " ")
        text = text.replace("---", "\n---\n")
        return text


async def setup(client: commands.Bot):
    await client.add_cog(Translate(client))
