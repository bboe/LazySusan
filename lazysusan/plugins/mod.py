from lazysusan.helpers import (display_exceptions, moderator_required,
                               no_arg_command)
from lazysusan.plugins import CommandPlugin


class BotDJ(CommandPlugin):
    COMMANDS = {'/autoskip': 'auto_skip',
                '/djdown': 'stop',
                '/djup': 'play',
                '/skip': 'skip_song'}

    @property
    def is_dj(self):
        return self.bot.bot_id in self.bot.dj_ids

    @property
    def is_playing(self):
        return self.bot.bot_id == self.bot.api.currentDjId

    def __init__(self, *args, **kwargs):
        super(BotDJ, self).__init__(*args, **kwargs)
        self.should_auto_skip = False
        self.register('add_dj', self.dj_update)
        self.register('deregistered', self.dj_update)
        self.register('newsong', self.new_song)
        self.register('registered', self.dj_update)
        self.register('rem_dj', self.dj_update)

    @display_exceptions
    @no_arg_command
    def auto_skip(self, message, data):
        """Toggle whether the bot should play anything."""
        self.should_auto_skip = not self.should_auto_skip
        if self.should_auto_skip:
            self.bot.reply('I\'ll just keep this seat warm for you.', data)
            if self.is_playing and len(self.bot.dj_ids) > 1:
                self.bot.api.skip()
        else:
            self.bot.reply('I\'m back baby!', data)

    @display_exceptions
    def dj_update(self, data):
        for user in data['user']:
            if self.bot.bot_id == user['userid']:
                if data['command'] == 'rem_dj':
                    self.should_auto_skip = False
                return  # Ignore updates from the bot

        num_djs = len(self.bot.dj_ids)
        num_listeners = len(self.bot.listener_ids)

        if self.is_dj:  # Auto leave conditions
            # Leave the table if there is no space left or when there is no one
            # else in the room
            if num_djs >= self.bot.max_djs or num_listeners <= 1:
                print 'Leaving the table'
                self.bot.api.remDj()
        else:  # Auto join conditions
            # Join the table when there are others in the room and there are
            # fewer than 2 djs (don't fill a small table)
            if num_listeners > 1 and num_djs < 2 and self.bot.max_djs > 2:
                print 'Stepping up to DJ'
                self.bot.api.addDj()

    @display_exceptions
    def new_song(self, data):
        """Called when a new song starts playing."""
        num_djs = len(self.bot.dj_ids)
        if self.is_playing and self.should_auto_skip and num_djs > 1:
            self.bot.api.skip()

    @moderator_required
    @no_arg_command
    def play(self, message, data):
        """Attempt to have the bot dj."""
        if self.is_dj:
            return self.bot.reply('I am already DJing.', data)
        if len(self.bot.dj_ids) < self.bot.max_djs:
            return self.bot.api.addDj()
        self.bot.reply('I can not do that right now.', data)

    @display_exceptions
    @no_arg_command
    def skip_song(self, message, data):
        """Ask the bot to skip the current song"""
        if not self.is_playing:
            self.bot.reply('I am not currently playing.', data)
        else:
            self.bot.api.skip()
            self.bot.reply(':poop: I was just getting into it.', data)

    @moderator_required
    @no_arg_command
    def stop(self, message, data):
        """Have the bot step down as a dj."""
        if not self.is_dj:
            return self.bot.reply('I am not currently DJing.', data)
        self.bot.api.remDj()


class BotPlaylist(CommandPlugin):
    COMMANDS = {'/botq': 'queue_song'}

    @display_exceptions
    @no_arg_command
    def queue_song(self, message, data):
        """Request that the bot add the current song to her playlist."""
        self.bot.reply("Cool tunes, daddio.", data)
        self.bot.api.playlistAdd(self.bot.api.currentSongId, -1)
        self.bot.api.bop()
