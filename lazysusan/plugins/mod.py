from lazysusan.helpers import display_exceptions, moderator_required
from lazysusan.plugins import CommandPlugin


class BotDJ(CommandPlugin):
    COMMANDS = {'/djdown': 'stop', '/djup': 'play'}

    @property
    def is_dj(self):
        return self.bot.bot_id in self.bot.dj_ids

    def __init__(self, *args, **kwargs):
        super(BotDJ, self).__init__(*args, **kwargs)
        self.bot.bot.on('add_dj', self.dj_update)
        self.bot.bot.on('deregistered', self.dj_update)
        self.bot.bot.on('registered', self.dj_update)
        self.bot.bot.on('rem_dj', self.dj_update)

    @display_exceptions
    def dj_update(self, data):
        # Ignore updates from the bot
        for user in data['user']:
            if self.bot.bot_id == user['userid']:
                return

        num_djs = len(self.bot.dj_ids)
        num_listeners = len(self.bot.listener_ids)

        if self.is_dj:  # Auto leave conditions
            # Leave the table if there is no space left or when there is no one
            # else in the room
            if num_djs >= self.bot.max_djs or num_listeners <= 1:
                print 'Leaving the table'
                self.bot.bot.remDj()
        else:  # Auto join conditions
            # Join the table when there are others in the room and there are
            # fewer than 2 djs (don't fill a small table)
            if num_listeners > 1 and num_djs < 2 and self.bot.max_djs > 2:
                print 'Stepping up to DJ'
                self.bot.bot.addDj()

    @moderator_required
    def play(self, message, data):
        """Attempt to have the bot dj."""
        if message:
            return
        if self.is_dj:
            return self.bot.reply('I am already DJing.', data)
        if len(self.bot.dj_ids) < self.bot.max_djs:
            return self.bot.bot.addDj()
        self.bot.reply('I can not do that right now.', data)

    @moderator_required
    def stop(self, message, data):
        """Have the bot step down as a dj."""
        if message:
            return
        if not self.is_dj:
            return self.bot.reply('I am not currently DJing.', data)
        self.bot.bot.remDj()
