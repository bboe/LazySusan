"""A set of very simple LazySusan plugins."""

from lazysusan.plugins import CommandPlugin


class Talk(CommandPlugin):

    """A plugin that enables users to `speak` as the bot."""

    COMMANDS = {'/echo': 'echo',
                '/say': 'say'}

    def echo(self, message, data):
        """Repeat everything after /echo to the same stream."""
        self.bot.reply(message, data)

    def say(self, message, data):
        """Repeat everything after /speak to the bot's current room."""
        self.bot.api.speak(message)
