"""A set of very simple LazySusan plugins."""

from lazysusan.plugins import CommandPlugin


class Echo(CommandPlugin):

    """A plugin that enables users to `speak` as the bot."""

    COMMANDS = {'/echo': 'echo'}

    def echo(self, message, data):
        """Repeat everything everything after /echo."""
        self.bot.reply(message, data)
