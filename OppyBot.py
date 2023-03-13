import argparse
import datetime
import json
import os
import sys
from dataclasses import dataclass
from threading import Lock
from typing import List, Dict

import discord
from discord.message import Message

os.environ["LOGURU_AUTOINIT"] = "0"
from loguru import logger
from opencc import OpenCC
from revChatGPT.V3 import Chatbot


@dataclass
class ConfigKeys:
    OpenAI_API_Key = "api_key"
    DiscordBotToken = "discord_token"
    TargetChannels = "target_channels"
    Delimeters = "delim"
    EmojiPending = "emoji_pending"
    EmojiDone = "emoji_done"
    MessageReset = "message_reset"
    MessageWaiting = "message_waiting"
    MessageOnError = "message_on_error"
    MessageNoResponse = "message_no_resp"
    ResetDelta = "reset_delta"
    CommandPrefix = "command_prefix"
    HelpCommand = "help_command"
    ResetCommand = "reset_command"
    HelpMessage = "help_message"
    ConverterType = "converter_type"


class OppyBot(discord.Client):
    def __init__(self, config_path, *args, **kwargs) -> None:
        # Init Discord Client
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(*args, **kwargs, intents=intents)

        # Load Params
        with open(config_path, "rt", encoding="UTF-8") as f:
            config = json.load(f)

        self.discord_bot_token = config[ConfigKeys.DiscordBotToken]
        self.target_chs: list = config[ConfigKeys.TargetChannels]
        self.delimeters: str = config[ConfigKeys.Delimeters]
        self.emoji_pending: str = config[ConfigKeys.EmojiPending]
        self.emoji_done: str = config[ConfigKeys.EmojiDone]
        self.message_reset: str = config[ConfigKeys.MessageReset]
        self.message_waiting: str = config[ConfigKeys.MessageWaiting]
        self.message_on_error: str = config[ConfigKeys.MessageOnError]
        self.message_no_resp: str = config[ConfigKeys.MessageNoResponse]
        reset_delta_kwargs: dict = config[ConfigKeys.ResetDelta]
        self.reset_delta = datetime.timedelta(**reset_delta_kwargs)
        self.command_prefix: List[str] = config[ConfigKeys.CommandPrefix]
        self.prefix = self.command_prefix[0]
        self.help_command: List[str] = config[ConfigKeys.HelpCommand]
        self.reset_command: List[str] = config[ConfigKeys.ResetCommand]
        self.help_message: List[str] = config[ConfigKeys.HelpMessage]
        conv_type = config[ConfigKeys.ConverterType]
        self.conv = OpenCC(conv_type)

        # Init Chatbot
        self.chatbot: Dict[int, Chatbot] = {
            t: Chatbot(config[ConfigKeys.OpenAI_API_Key])
            for t in self.target_chs
        }

        # Init Core Module
        self.b_using: Dict[int, bool] = {t: False for t in self.target_chs}
        self.mutex_lock: Dict[int, Lock] = {t: Lock() for t in self.target_chs}
        self.last_timestamp = None

    async def on_ready(self):
        logger.info(f"{self.user} | Ready!")

    async def on_message(self, message: Message):
        # Commands
        if await self.ProcessCommands(message):
            return

        # Process Prompts
        logger.info(f"Incoming Message: {message.content}")

        await self.CheckReset(message)

        self.ToggleUsing(True, message.channel.id)
        async with message.channel.typing():
            try:
                resp_msg = await self.SendResponse(message)
                logger.info(f"Response: {resp_msg}")
            except Exception as e:
                logger.error(f"Error: {e}")
                await message.channel.send(content=self.message_on_error)
            finally:
                self.ToggleUsing(False, message.channel.id)

        await message.add_reaction(self.emoji_done)

    def Run(self):
        self.run(self.discord_bot_token)

    async def ProcessCommands(self, message: Message):
        if message.channel.id not in self.target_chs:
            return True

        if message.author == self.user:
            return True

        msg = message.content.lower()
        for prefix in self.command_prefix:
            msg = msg.replace(prefix, self.prefix)

        # Send Help Message
        if self.CheckCommand(msg, self.help_command):
            self.SendHelp(message)
            return True

        # Reset Chat
        if self.CheckCommand(msg, self.reset_command):
            self.chatbot[message.channel.id].reset()
            await message.channel.send(self.message_reset)
            return True

        # Skip Other Commands
        if msg.startswith(self.prefix):
            return True

        # Skip Server Emoji
        if msg.startswith("<") and msg.endswith(">"):
            return True

        if self.IsUsing(message.channel.id):
            await message.add_reaction(self.emoji_pending)
            return True

        return False

    async def SendHelp(self, message: Message):
        help_str = BacktickConcat(self.help_command)
        reset_str = BacktickConcat(self.reset_command)
        msg_params = (self.emoji_done, self.emoji_pending, help_str, reset_str)
        await message.channel.send(self.help_message % msg_params)

    def CheckCommand(self, msg, cmds):
        for c in cmds:
            if self.prefix + c == msg:
                return True
        return False

    async def CheckReset(self, message: Message):
        curr_ts = datetime.datetime.now()
        if self.last_timestamp is None:
            self.last_timestamp = datetime.datetime.now()

        if curr_ts - self.last_timestamp > self.reset_delta:
            self.chatbot[message.channel.id].reset()
            await message.channel.send(self.message_reset)

        self.last_timestamp = curr_ts

    async def SendResponse(self, message: Message):
        # Iteration of Each Response
        msg: Message = await message.channel.send(self.message_waiting)
        collect_msg = list()
        for resp in self.chatbot[message.channel.id].ask(message.content):
            collect_msg.append(resp)
            resp_msg = self.ProcessMessage(collect_msg)
            if self.EndsWithDelim(resp_msg):
                await msg.edit(content=resp_msg)

        # Send Final Respone
        if resp_msg != "":
            await msg.edit(content=resp_msg)
        else:
            await msg.edit(content=self.message_no_resp)

        return "".join(collect_msg)

    def ProcessMessage(self, msg: List[str]):
        resp_msg = "".join(msg)
        resp_msg = self.conv.convert(resp_msg)
        while "\n\n" in resp_msg:
            resp_msg = resp_msg.replace("\n\n", "\n")
        resp_msg = DoEscape(resp_msg)

        return resp_msg

    def EndsWithDelim(self, msg: str):
        for d in self.delimeters:
            if msg.endswith(d):
                return True
        return False

    def ToggleUsing(self, b: bool, cid: int):
        with self.mutex_lock[cid]:
            self.b_using[cid] = b

    def IsUsing(self, cid: int):
        with self.mutex_lock[cid]:
            return self.b_using[cid]


def DoEscape(msg):
    s = list()
    do_escape = True
    backtick = "`"
    tri_backticks = "```"

    for c in msg:
        if c == backtick:
            do_escape = not do_escape
            s.append(c)
            continue

        if do_escape:
            s.append(discord.utils.escape_markdown(c))
        else:
            s.append(c)

    s = "".join(s)

    if s.count(tri_backticks) % 2 == 1:
        if s.endswith("\n"):
            s += f"\n{tri_backticks}\n"
        else:
            s += f"\n{tri_backticks}"

    elif s.count(backtick) % 2 == 1:
        s += backtick

    return s


def BacktickConcat(a):
    return BacktickWrap(BacktickJoin(a))


def BacktickJoin(a):
    return "`, `".join(a)


def BacktickWrap(s):
    return f"`{s}`"


def InitLogger(log_path):
    log_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | <lvl>{level: ^9}</lvl> | {message}"
    )
    logger.add(sys.stderr, level="INFO", format=log_format)
    logger.add(
        log_path,
        rotation="1 day",
        retention="7 days",
        level="INFO",
        encoding="UTF-8",
        compression="gz",
        format=log_format,
    )


def Main():
    parser = argparse.ArgumentParser()
    parser.add_argument("Config")
    parser.add_argument("--LogFile", default="Logs/Oppy.log")
    args: Args = parser.parse_args()
    InitLogger(args.LogFile)
    OppyBot(args.Config).Run()


@dataclass
class Args:
    Config: str
    LogFile: str


if __name__ == "__main__":
    Main()
