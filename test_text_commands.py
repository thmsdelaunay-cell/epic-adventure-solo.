import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

os.environ["DISCORD_TOKEN"] = ""
os.environ["OWNER_ID"] = "0"
import bot
from discord.ext import commands
from text_commands import parse_arguments


class TextCommandsTests(unittest.TestCase):
    def test_registry_and_arguments(self):
        slash = bot.bot.tree.get_commands()
        self.assertEqual({c.name for c in slash}, {c.name for c in bot.bot.commands})
        for command in slash:
            arguments = []
            for p in command.parameters:
                if not p.required:
                    continue
                arguments.append(str(p.choices[0].value) if p.choices else
                                 str(p.min_value or 1) if p.type.name == "integer" else "armure")
            parse_arguments(command, " ".join(arguments))
        self.assertEqual(parse_arguments(bot.bot.tree.get_command("equiper"), "armure"), {"objet": "armure"})
        self.assertEqual(parse_arguments(bot.bot.tree.get_command("reclamer_quete"), "Chasseur novice"), {"nom": "Chasseur novice"})
        for name, args in [("acheter", "potion 0"), ("acheter", "potion -1"),
                           ("acheter", "potion 101"), ("bestiary", "11"),
                           ("exercer", "inconnu"), ("equiper", ""), ("hunt", "extra")]:
            with self.subTest(name=name, args=args), self.assertRaises(commands.BadArgument):
                parse_arguments(bot.bot.tree.get_command(name), args)
        self.assertEqual(parse_arguments(bot.bot.tree.get_command("exercer"), "mineur")["metier"].value, "mineur")

    def test_shared_game_and_owner(self):
        async def run():
            ctx = Mock(spec=commands.Context)
            ctx.author = SimpleNamespace(id=123, display_name="Test", send=AsyncMock())
            ctx.send = AsyncMock()
            with tempfile.TemporaryDirectory() as directory:
                bot.DB = str(Path(directory) / "test.db")
                bot.init_db()
                for name, args in [("commencer", ""), ("profil", ""), ("inventaire", ""),
                                   ("hunt", ""), ("boss", "")]:
                    await bot.bot.get_command(name).callback(ctx, arguments=args)
                with bot.connection() as db:
                    bot.give(db, 123, "armure", 1)
                    before = dict(bot.player(db, 123))
                await bot.bot.get_command("equiper").callback(ctx, arguments="armure")
                with bot.connection() as db:
                    self.assertEqual(bot.item_qty(db, 123, "armure"), 0)
                    self.assertEqual(bot.player(db, 123)["defense"], before["defense"]+2)
                bot.OWNER_ID = 456
                await bot.bot.get_command("equiper").callback(ctx, arguments="armure")
                ctx.author.send.assert_awaited_once()
                bot.OWNER_ID = 0
            await bot.bot.close()
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
