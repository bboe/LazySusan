from . import CommandPlugin

class BotDJ(CommandPlugin):
    COMMANDS = {'/botdj': 'play', '/unbotdj': 'stop'}
    REQUIRE_ADMIN = True

    def __init__(self):
        super(BotDJ, self).__init__()
        self.is_dj = False

    def play(self, bot, message, data):
        """Attempt to have the bot dj for the room."""
        if self.is_dj:
            return bot.reply('I am already DJing.', data)
        bot.reply('This feature is not yet implemented.', data)

    def stop(self, bot, message, data):
        """Have the bot step down as a dj for the room."""
        if not self.is_dj:
            return bot.reply('I am not currently DJing.', data)
        bot.reply('This feature is not yet implemented.', data)
