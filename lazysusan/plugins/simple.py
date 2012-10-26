from lazysusan.plugins import CommandPlugin


class Echo(CommandPlugin):
    COMMANDS = {'/echo': 'echo'}

    def echo(self, message, data):
        """Repeat everything everything after /echo."""
        self.bot.reply(message, data)
