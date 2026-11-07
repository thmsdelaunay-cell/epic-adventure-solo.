"""Text equivalents of the complete slash-command registry."""
import logging
import shlex

import discord
from discord import app_commands
from discord.ext import commands


def parse_arguments(command, arguments):
    """Apply slash choices, defaults and numeric bounds before any game action."""
    try:
        words = shlex.split(arguments)
    except ValueError as exc:
        raise commands.BadArgument("Guillemets non fermés.") from exc
    values = {}
    parameters = command.parameters
    for index, parameter in enumerate(parameters):
        if not words:
            if parameter.required:
                raise commands.BadArgument(f"Argument requis : {parameter.name}.")
            values[parameter.name] = parameter.default
            continue
        # The last string may contain spaces, e.g. reclamer_quete Chasseur novice.
        raw = " ".join(words) if index == len(parameters)-1 and parameter.type == discord.AppCommandOptionType.string else words[0]
        if index == len(parameters)-1 and parameter.type == discord.AppCommandOptionType.string:
            words.clear()
        else:
            words.pop(0)
        if parameter.type == discord.AppCommandOptionType.integer:
            try:
                value = int(raw)
            except ValueError as exc:
                raise commands.BadArgument(f"{parameter.name} doit être un entier.") from exc
            if ((parameter.min_value is not None and value < parameter.min_value)
                    or (parameter.max_value is not None and value > parameter.max_value)):
                raise commands.BadArgument(
                    f"{parameter.name} doit être entre {parameter.min_value} et {parameter.max_value}.")
        elif parameter.type == discord.AppCommandOptionType.string:
            value = raw
        else:
            raise commands.BadArgument("Type d'argument non pris en charge.")
        if parameter.choices:
            choice = next((c for c in parameter.choices
                           if str(c.value).casefold() == str(value).casefold()
                           or c.name.casefold() == str(value).casefold()), None)
            if choice is None:
                raise commands.BadArgument(
                    f"{parameter.name} : choisis "+", ".join(str(c.value) for c in parameter.choices))
            value = choice
        values[parameter.name] = value
    if words:
        raise commands.BadArgument("Trop d'arguments.")
    return values


def register(bot):
    def make_callback(slash):
        async def invoke(ctx, *, arguments: str = ""):
            values = parse_arguments(slash, arguments)
            # Existing callbacks only need user and respond(); Context supplies send().
            ctx.user = ctx.author
            await slash.callback(ctx, **values)
        return invoke

    for slash in bot.tree.get_commands():
        if not isinstance(slash, app_commands.Command):
            raise TypeError("Ajouter la prise en charge des groupes avant leur enregistrement.")
        bot.add_command(commands.Command(
            make_callback(slash), name=slash.name, help=slash.description))

    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            message = "Commande inconnue. Utilise rpg aide."
        elif isinstance(error, commands.UserInputError):
            message = str(error)
        else:
            logging.getLogger(__name__).error("Échec de commande textuelle", exc_info=error)
            message = "Une erreur est survenue. Réessaie plus tard."
        await ctx.send(message, allowed_mentions=discord.AllowedMentions.none())
