from . import CommandPlugin

class Echo(CommandPlugin):
    COMMANDS = {'/echo': 'echo'}

    def echo(self, bot, message, data):
        """Repeat everything everything after /echo."""
        bot.reply(message, data)
