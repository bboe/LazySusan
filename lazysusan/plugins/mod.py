from lazysusan.helpers import moderator_required
from lazysusan.plugins import CommandPlugin


class BotDJ(CommandPlugin):
    COMMANDS = {'/botdj': 'play', '/unbotdj': 'stop'}

    def __init__(self):
        super(BotDJ, self).__init__()
        self.is_dj = False

    @moderator_required
    def play(self, bot, message, data):
        """Attempt to have the bot dj for the room."""
        if self.is_dj:
            return bot.reply('I am already DJing.', data)
        bot.reply('This feature is not yet implemented.', data)

    @moderator_required
    def stop(self, bot, message, data):
        """Have the bot step down as a dj for the room."""
        if not self.is_dj:
            return bot.reply('I am not currently DJing.', data)
        bot.reply('This feature is not yet implemented.', data)
