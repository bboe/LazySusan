import random
from lazysusan.helpers import (display_exceptions, moderator_required,
                               no_arg_command, single_arg_command)
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
    def auto_skip(self, data):
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
    def play(self, data):
        """Attempt to have the bot dj."""
        if self.is_dj:
            return self.bot.reply('I am already DJing.', data)
        if len(self.bot.dj_ids) < self.bot.max_djs:
            return self.bot.api.addDj()
        self.bot.reply('I can not do that right now.', data)

    @display_exceptions
    @no_arg_command
    def skip_song(self, data):
        """Ask the bot to skip the current song"""
        if not self.is_playing:
            self.bot.reply('I am not currently playing.', data)
        else:
            self.bot.api.skip()
            self.bot.reply(':poop: I was just getting into it.', data)

    @moderator_required
    @no_arg_command
    def stop(self, data):
        """Have the bot step down as a dj."""
        if not self.is_dj:
            return self.bot.reply('I am not currently DJing.', data)
        self.bot.api.remDj()


class BotPlaylist(CommandPlugin):
    COMMANDS = {'/pladd': 'add',
                '/plavailable': 'available',
                '/plclear': 'clear',
                '/pllist': 'list',
                '/plload': 'load',
                '/plupdate': 'update_playlist'}
    PLAYLIST_PREFIX = 'botplaylist.'

    def __init__(self, *args, **kwargs):
        super(BotPlaylist, self).__init__(*args, **kwargs)
        self.playlist = None
        self.register('roomChanged', self.room_init)
        self.room_list = {}
        # Fetch room info if this is a reload
        if self.bot.api._isConnected:
            self.bot.api.roomInfo(self.room_init)

    @display_exceptions
    @no_arg_command
    def add(self, data):
        """Request that the bot add the current song to her playlist."""
        if not self.bot.api.currentSongId:
            self.bot.reply('There is no song playing.', data)
            return
        if self.bot.api.currentSongId in self.playlist:
            self.bot.reply('We already have that song.', data)
        else:
            self.bot.reply('Cool tunes, daddio.', data)
            self.bot.api.playlistAdd(self.bot.api.currentSongId,
                                     len(self.playlist))
            self.playlist.add(self.bot.api.currentSongId)
        self.bot.api.bop()

    @display_exceptions
    @moderator_required
    @no_arg_command
    def available(self, data):
        """Output the names of the available playlists."""
        playlists = []
        for key in self.bot.config:
            if key.startswith(self.PLAYLIST_PREFIX):
                playlists.append(key[len(self.PLAYLIST_PREFIX):])
        reply = 'Available playlists: '
        reply += ', '.join(sorted(playlists))
        self.bot.reply(reply, data)

    @moderator_required
    @no_arg_command
    def clear(self, data):
        """Clear the bot's playlist."""
        if self.playlist:
            self.bot.api.playlistRemove(0, self.clear_callback(data))
        else:
            self.bot.reply('The playlist is already empty.', data)

    def clear_callback(self, caller_data, load_config=None):
        @display_exceptions
        def _closure(data):
            if 'song' not in data:
                return
            self.playlist.remove(data['song']['fileid'])
            if self.playlist:  # While there are songs continue to remove
                self.bot.api.playlistRemove(0, _closure)
            elif load_config:  # Perform possible load action
                self.load_raw(load_config, caller_data)
            else:
                self.bot.reply('Playlist cleared.', caller_data)
        return _closure

    @display_exceptions
    def get_playlist(self, data):
        self.playlist = set(x['_id'] for x in data['list'])

    def get_roomlist(self, skip):
        @display_exceptions
        def _closure(data):
            count = skip
            for room, _ in data['rooms']:
                count += 1
                if count > 10 and room['metadata']['listeners'] < 10:
                    break
                self.room_list[room['shortcut']] = room['roomid']
            else:
                # Python closures are read-only so we have to recreate
                self.bot.api.listRooms(skip=count,
                                       callback=self.get_roomlist(count))
                return
        return _closure

    @moderator_required
    @no_arg_command
    def list(self, data):
        """Output the # of songs in the playlist and the first five songs."""
        self.bot.api.playlistAll(self.list_callback(data))

    def list_callback(self, caller_data):
        @display_exceptions
        def _closure(data):
            count = len(data['list'])
            preview = []
            for item in data['list'][:5]:
                artist = item['metadata']['artist'].encode('utf-8')
                song = item['metadata']['song'].encode('utf-8')
                item = '"{0}" by {1}'.format(song, artist)
                preview.append(item)
            reply = 'There are {0} songs in the playlist. '.format(count)
            if count > 0:
                reply += 'The first {0} are: {1}'.format(len(preview),
                                                         ', '.join(preview))
            self.bot.reply(reply, caller_data)
        return _closure

    @display_exceptions
    @moderator_required
    @single_arg_command
    def load(self, message, data):
        """Load up the specified playlist."""
        config_name = '{0}{1}'.format(self.PLAYLIST_PREFIX, message)
        if config_name not in self.bot.config:
            self.bot.reply('Playlist `{0}` does not exist.'
                           .format(config_name), data)
            return
        if self.playlist:
            self.bot.api.playlistRemove(0,
                                        self.clear_callback(data, config_name))
        else:
            self.load_raw(config_name, data)

    @display_exceptions
    def load_raw(self, config_name, caller_data):
        count = 0
        for song_id in self.bot.config[config_name].split('\n'):
            if song_id not in self.playlist:
                count += 1
                self.bot.api.playlistAdd(song_id, -1)
                self.playlist.add(song_id)
        self.bot.reply('Loaded {0} songs from playlist {1}.'
                       .format(count, config_name), caller_data)

    @display_exceptions
    def room_init(self, _):
        self.bot.api.playlistAll(self.get_playlist)
        self.bot.api.listRooms(skip=0, callback=self.get_roomlist(0))

    @display_exceptions
    @single_arg_command
    def update_playlist(self, message, data):
        """Update the bot's playlist from songs played in the provided room."""
        if message not in self.room_list:
            reply = 'Could not find `{0}` in the room_list. '.format(message)
            reply += 'Perhaps try one of these: '
            reply += ', '.join(sorted(random.sample(self.room_list, 5)))
            self.bot.reply(reply, data)
            return
        room_id = self.room_list[message]
        # Hack room info call
        request = {'api': 'room.info', 'roomid': room_id}
        self.bot.reply('Querying {0}'.format(room_id), data)
        self.bot.api._send(request, self.update_playlist_callback(data))

    def update_playlist_callback(self, caller_data):
        @display_exceptions
        def _closure(data):
            songs = data['room']['metadata']['songlog']
            random.shuffle(songs)
            to_add = []
            for song in songs:
                if song['snaggable'] and song['_id'] not in self.playlist:
                    to_add.append((song.get('score'), song['_id']))
            # Most popular songs will play first (added last)
            for score, song_id in sorted(to_add):
                self.bot.api.playlistAdd(song_id, 0)
                self.playlist.add(song_id)
            self.bot.reply('Added {0} songs'.format(len(to_add)), caller_data)
        return _closure
