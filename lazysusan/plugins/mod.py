from lazysusan.helpers import moderator_required
from lazysusan.plugins import CommandPlugin


class BotDJ(CommandPlugin):
    COMMANDS = {'/botdjdown': 'stop', '/botdjup': 'play'}

    @property
    def is_dj(self):
        return self.bot.bot_id in self.bot.dj_ids

    def __init__(self, *args, **kwargs):
        super(BotDJ, self).__init__(*args, **kwargs)
        self.bot.bot.on('add_dj', self.handle_dj_update)
        self.bot.bot.on('rem_dj', self.handle_dj_update)

    def handle_dj_update(self, data):
        # Ignore updates from the bot
        for user in data['user']:
            if self.bot.bot_id == user['userid']:
                return

        if self.is_dj:  # Auto leave conditions
            # Leave the table if there is no space left
            if len(self.bot.dj_ids) == self.bot.max_djs:
                self.bot.bot.remDj()
        else:  # Auto join conditions
            # Make sure music is playing for everyone
            if self.bot.max_djs > 2 and len(self.bot.dj_ids) < 2:
                self.bot.bot.addDj()

    @moderator_required
    def play(self, message, data):
        """Attempt to have the bot dj."""
        if self.is_dj:
            return self.bot.reply('I am already DJing.', data)
        if len(self.bot.dj_ids) < self.bot.max_djs:
            return self.bot.bot.addDj()
        self.bot.reply('I can not do that right now.', data)

    @moderator_required
    def stop(self, message, data):
        """Have the bot step down as a dj."""
        if not self.is_dj:
            return self.bot.reply('I am not currently DJing.', data)
        self.bot.bot.remDj()
