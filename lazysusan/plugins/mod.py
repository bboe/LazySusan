from lazysusan.helpers import moderator_required
from lazysusan.plugins import CommandPlugin


class BotDJ(CommandPlugin):
    COMMANDS = {'/botdj': 'play', '/unbotdj': 'stop'}

    def __init__(self):
        super(BotDJ, self).__init__()

    def is_dj(self, bot):
        return bot.bot_id in bot.dj_ids

    @moderator_required
    def play(self, bot, message, data):
        """Attempt to have the bot dj for the room."""
        if self.is_dj(bot):
            return bot.reply('I am already DJing.', data)
        if len(bot.dj_ids) < bot.max_djs:
            bot.bot.addDj()
        else:
            bot.reply('I can not do that right now.', data)

    @moderator_required
    def stop(self, bot, message, data):
        """Have the bot step down as a dj for the room."""
        if not self.is_dj(bot):
            return bot.reply('I am not currently DJing.', data)
        bot.bot.remDj()
