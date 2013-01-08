#!/usr/bin/env python
import heapq
import logging
import os
import sys
import time
from ConfigParser import ConfigParser
from datetime import datetime
from lazysusan.helpers import (admin_required, display_exceptions,
                               get_sender_id, no_arg_command,
                               single_arg_command)
from lazysusan.plugins import CommandPlugin
from optparse import OptionParser
from ttapi import Bot
from update_checker import pretty_date, update_check

__version__ = '0.1rc10'


def handle_error(*args, **kwargs):
    print args
    print kwargs


class LazySusanException(Exception):
    pass


class LazySusan(object):
    update_checked = False

    @staticmethod
    def _get_config(section):
        config = ConfigParser()
        if 'APPDATA' in os.environ:  # Windows
            os_config_path = os.environ['APPDATA']
        elif 'XDG_CONFIG_HOME' in os.environ:  # Modern Linux
            os_config_path = os.environ['XDG_CONFIG_HOME']
        elif 'HOME' in os.environ:  # Legacy Linux
            os_config_path = os.path.join(os.environ['HOME'], '.config')
        else:
            os_config_path = None
        locations = ['lazysusan.ini']
        if os_config_path is not None:
            locations.insert(0, os.path.join(os_config_path, 'lazysusan.ini'))
        if not config.read(locations):
            raise LazySusanException('No lazysusan.ini found.')
        if not config.has_section(section) and section != 'DEFAULT':
            raise LazySusanException('No section `{0}` found in lazysusan.ini.'
                                     .format(section))
        return dict(config.items(section))

    def __init__(self, config_section, plugin_dir, enable_logging):
        if not self.update_checked:
            update_check(__name__, __version__)
            self.update_checked = True

        self.start_time = datetime.utcnow()

        if plugin_dir:
            if os.path.isdir(plugin_dir):
                sys.path.append(plugin_dir)
            else:
                print('`{0}` is not a directory.'.format(plugin_dir))

        config = self._get_config(config_section)
        self._delayed_events = []
        self._loaded_plugins = {}
        self.api = Bot(config['auth_id'], config['user_id'], rate_limit=0.575)
        self.api.debug = enable_logging
        self.api.on('add_dj', self.handle_add_dj)
        self.api.on('booted_user', self.handle_booted_user)
        self.api.on('deregistered', self.handle_user_leave)
        self.api.on('new_moderator', self.handle_add_moderator)
        self.api.on('post_message', self.run_delayed_events)
        self.api.on('pmmed', self.handle_pm)
        self.api.on('ready', self.handle_ready)
        self.api.on('registered', self.handle_user_join)
        self.api.on('rem_dj', self.handle_remove_dj)
        self.api.on('rem_moderator', self.handle_remove_moderator)
        self.api.on('roomChanged', self.handle_room_change)
        self.api.on('speak', self.handle_room_message)
        self.bot_id = config['user_id']
        self.commands = {'/about': self.cmd_about,
                         '/commands': self.cmd_commands,
                         '/help': self.cmd_help,
                         '/join': self.cmd_join,
                         '/leave': self.cmd_leave,
                         '/pgload': self.cmd_plugin_load,
                         '/pgreload': self.cmd_plugin_reload,
                         '/pgunload': self.cmd_plugin_unload,
                         '/plugins': self.cmd_plugins,
                         '/uptime': self.cmd_uptime}
        self.config = config
        self.dj_ids = set()
        self.listener_ids = set()
        self.max_djs = None
        self.moderator_ids = set()
        self.username = None

        # Load plugins after everything has been initialized
        for plugin in config['plugins'].split('\n'):
            self.load_plugin(plugin)

        self.api.connect(config['room_id'])
        self.api.ws.on_error = handle_error

    def _load_command_plugin(self, plugin):
        to_add = {}
        for command, func_name in plugin.COMMANDS.items():
            if command in self.commands:
                other = self.commands[command]
                if isinstance(other.im_self, CommandPlugin):
                    print('`{0}` conflicts with `{1}` for command `{2}`.'
                          .format(plugin.NAME, other.im_self.NAME, command))
                else:
                    print('`{0}` cannot use the reserved command `{1}`.'
                          .format(plugin.NAME, command))
                print('Not loading plugin `{0}`.'.format(plugin.NAME))
                return False
            to_add[command] = getattr(plugin, func_name)
        self.commands.update(to_add)
        return True

    def _unload_command_plugin(self, plugin):
        for command in plugin.COMMANDS:
            del self.commands[command]

    @no_arg_command
    def cmd_about(self, data):
        """Display information about this bot."""
        reply = ('I am powered by LazySusan version {0}. '
                 'https://github.com/bboe/LazySusan'.format(__version__))
        self.reply(reply, data)

    @no_arg_command
    def cmd_commands(self, data):
        """List the available commands."""

        admin_cmds = []
        admin_or_moderator_cmds = []
        moderator_cmds = []
        no_priv_cmds = []

        for command, func in self.commands.items():
            if func.func_dict.get('admin_required'):
                admin_cmds.append(command)
            elif func.func_dict.get('admin_or_moderator_required'):
                admin_or_moderator_cmds.append(command)
            elif func.func_dict.get('moderator_required'):
                moderator_cmds.append(command)
            else:
                no_priv_cmds.append(command)
        reply = 'Available commands: '
        reply += ', '.join(sorted(no_priv_cmds))
        self.reply(reply, data)

        user_id = get_sender_id(data)
        if moderator_cmds and self.is_moderator(user_id):
            reply = 'Moderator commands: '
            reply += ', '.join(sorted(moderator_cmds))
            self.api.pm(reply, user_id)
        if admin_or_moderator_cmds and (self.is_moderator(user_id)
                                        or self.is_admin(user_id)):
            reply = 'Priviliged commands: '
            reply += ', '.join(sorted(admin_or_moderator_cmds))
            self.api.pm(reply, user_id)
        if admin_cmds and self.is_admin(user_id):
            reply = 'Admin commands: '
            reply += ', '.join(sorted(admin_cmds))
            self.api.pm(reply, user_id)

    def _connect(self, room_id, when_connected=True):
        if self.api.roomId == room_id or (self.api.roomId
                                          and not when_connected):
            return
        print('Joining {0}'.format(room_id))
        self.api.roomRegister(room_id)

    def cmd_help(self, message, data):
        """With no arguments, display this message. Otherwise, display the help
        for the given command. Type /commands to see the list of commands."""
        def docstr(item):
            lines = []
            for line in item.__doc__.split('\n'):
                line = line.strip()
                if line:
                    lines.append(line)
            return ' '.join(lines)

        if not message:
            reply = docstr(self.cmd_help)
        elif ' ' not in message:
            if message in self.commands:
                tmp = self.commands[message].func_dict
                if tmp.get('admin_required') and not self.is_admin(data) or \
                        tmp.get('moderator_required') and \
                        not self.is_moderator(data):
                    return
                reply = docstr(self.commands[message])
            else:
                reply = '`{0}` is not a valid command.'.format(message)
        else:
            return
        self.reply(reply, data)

    @admin_required
    def cmd_join(self, message, data):
        """Join the room by room_id.

        With no arguments, join the room specified in lazysusan.ini."""
        if ' ' in message:
            return
        room_id = message if message else self.config['room_id']
        if room_id == self.api.roomId:
            self.reply('I am already in that room.', data)
        else:
            self._connect(room_id)

    @admin_required
    @no_arg_command
    def cmd_leave(self, data):
        """Leave the current room and remain connected to the chat server."""
        def callback(cb_data):
            user_id = get_sender_id(data)
            if cb_data['success']:
                # Schedule an event to possibly rejoin after 1 minute
                self.schedule(60, self._connect, self.config['room_id'], False)
                self.api.pm('I have left the room. If I remain roomless after '
                            '~1 minute, I will rejoin the default room.',
                            user_id)
            else:
                self.api.pm('Leaving the room failed.', user_id)
        print('Leaving {0}'.format(self.api.roomId))
        self.api.roomDeregister(callback)

    @admin_required
    @single_arg_command
    def cmd_plugin_load(self, message, data):
        """Load the specified plugin."""
        if message in self._loaded_plugins:
            reply = 'Plugin `{0}` is already loaded.'.format(message)
        elif self.load_plugin(message, attempt_reload=True):
            reply = 'Plugin `{0}` loaded.'.format(message)
        else:
            reply = 'Plugin `{0}` could not be loaded.'.format(message)
        self.reply(reply, data)

    @admin_required
    @single_arg_command
    def cmd_plugin_reload(self, message, data):
        """Reoad the specified plugin."""
        if message not in self._loaded_plugins:
            reply = 'Plugin `{0}` is not loaded.'.format(message)
        elif not (self.unload_plugin(message) and
                  self.load_plugin(message, attempt_reload=True)):
            reply = 'Plugin `{0}` could not be reloaded.'.format(message)
        else:
            reply = 'Plugin `{0}` reloaded.'.format(message)
        self.reply(reply, data)

    @admin_required
    @single_arg_command
    def cmd_plugin_unload(self, message, data):
        """Unload the specified plugin."""
        if message not in self._loaded_plugins:
            reply = 'Plugin `{0}` is not loaded.'.format(message)
        elif self.unload_plugin(message):
            reply = 'Plugin `{0}` unloaded.'.format(message)
        else:
            reply = 'Plugin `{0}` could not be unloaded.'.format(message)
        self.reply(reply, data)

    @admin_required
    @no_arg_command
    def cmd_plugins(self, data):
        """Display the list of loaded plugins."""
        reply = 'Loaded plugins: '
        reply += ', '.join(sorted(self._loaded_plugins.keys()))
        self.reply(reply, data)

    @no_arg_command
    def cmd_uptime(self, data):
        """Display how long since LazySusan was started."""
        msg = 'LazySusan was started {0}'.format(pretty_date(self.start_time))
        self.reply(msg, data)

    def is_admin(self, item):
        """item can be either the user_id, or a dictionary from a message."""
        if isinstance(item, dict):
            item = get_sender_id(item)
        return item in self.config['admin_ids']

    def is_moderator(self, item):
        """item can be either the user_id, or a dictionary from a message."""
        if isinstance(item, dict):
            item = get_sender_id(item)
        return item in self.moderator_ids

    def handle_add_dj(self, data):
        for user in data['user']:
            self.dj_ids.add(user['userid'])

    def handle_booted_user(self, data):
        if data['userid'] == self.bot_id:
            # Try to rejoin the default room after 30 seconds.
            self.api.roomId = None
            self.schedule(30, self._connect, self.config['room_id'], False)

    def handle_add_moderator(self, data):
        self.moderator_ids.add(data['userid'])

    def handle_pm(self, data):
        self.process_message(data)

    def handle_ready(self, _):
        self.api.userInfo(self.set_username)

    @display_exceptions
    def handle_remove_dj(self, data):
        for user in data['user']:
            self.dj_ids.remove(user['userid'])

    @display_exceptions
    def handle_remove_moderator(self, data):
        self.moderator_ids.remove(data['userid'])

    def handle_room_change(self, data):
        if not data['success']:
            if data['errno'] == 3:
                print('You are banned from that room. Retrying in 3 minutes.')
                self.schedule(180, self._connect, self.config['room_id'],
                              False)
                return
            print('Error changing rooms.')
            # Try to rejoin the default room
            self.api.roomId = None
            self._connect(self.config['room_id'])
            return
        self.dj_ids = set(data['room']['metadata']['djs'])
        self.listener_ids = set(x['userid'] for x in data['users'])
        self.max_djs = data['room']['metadata']['max_djs']
        self.moderator_ids = set(data['room']['metadata']['moderator_id'])

    @display_exceptions
    def handle_room_message(self, data):
        if self.username and self.username != data['name']:
            self.process_message(data)

    def handle_user_join(self, data):
        for user in data['user']:
            self.listener_ids.add(user['userid'])

    @display_exceptions
    def handle_user_leave(self, data):
        for user in data['user']:
            self.listener_ids.remove(user['userid'])

    def load_plugin(self, plugin_name, attempt_reload=False):
        parts = plugin_name.split('.')
        if len(parts) > 1:
            module_name = '.'.join(parts[:-1])
            class_name = parts[-1]
        else:
            # Use the titlecase format of the module name as the class name
            module_name = parts[0]
            class_name = parts[0].title()

        # First try to load plugins from the passed in plugins_dir and then
        # from the lazysusan.plugins package.
        module = None
        for package in (None, 'lazysusan.plugins'):
            if package:
                module_name = '{0}.{1}'.format(package, module_name)

            if attempt_reload and module_name in sys.modules:
                module = reload(sys.modules[module_name])
            else:
                try:
                    module = __import__(module_name, fromlist=[class_name])
                except ImportError:
                    pass
            if module:
                break
        if not module:
            print('Cannot find plugin `{0}`.'.format(plugin_name))
            return False
        try:
            plugin = getattr(module, class_name)(self)
        except AttributeError:
            print('Cannot find plugin `{0}`.'.format(plugin_name))
            return False

        plugin.__class__.NAME = plugin_name
        if isinstance(plugin, CommandPlugin):
            if not self._load_command_plugin(plugin):
                return
        self._loaded_plugins[plugin_name] = plugin
        print('Loaded plugin `{0}`.'.format(plugin_name))
        return True

    def process_message(self, data):
        parts = data['text'].split()
        if not parts:
            return
        command = parts[0]
        if len(parts) == 1:
            message = ''
        else:
            message = ' '.join(parts[1:])  # Normalize with single spaces
        handler = self.commands.get(command)
        if not handler:
            return
        handler(message, data)

    def reply(self, message, data):
        if data['command'] == 'speak':
            self.api.speak(message)
        elif data['command'] == 'pmmed':
            self.api.pm(message, data['senderid'])
        else:
            raise Exception('Unrecognized command type `{0}`'
                            .format(data['command']))

    def run_delayed_events(self, _):
        now = time.time()
        process = True
        while process and self._delayed_events:
            item = self._delayed_events[0]  # Peek at the top
            if item[0] < now:
                heapq.heappop(self._delayed_events)  # Actually remove
                item[1](*item[2], **item[3])
            else:
                process = False

    def schedule(self, min_delay, callback, *args, **kwargs):
        """Schedule an event to occur at least min_delay seconds in the future.

        The passed in callback function will be called with all remaining
        arguments.

        Scheduled events are checked and processed after every received message
        from turntable. In an inactive room the longest duration between
        received messages is 12 seconds."""
        schedule_time = time.time() + min_delay
        heapq.heappush(self._delayed_events,
                       (schedule_time, callback, args, kwargs))

    def set_username(self, data):
        self.username = data['name']

    def start(self):
        self.api.start()

    def unload_plugin(self, plugin_name):
        if plugin_name not in self._loaded_plugins:
            return False
        plugin = self._loaded_plugins[plugin_name]
        if isinstance(plugin, CommandPlugin):
            self._unload_command_plugin(plugin)
        del self._loaded_plugins[plugin_name]
        del plugin
        print('Unloaded plugin `{0}`.'.format(plugin_name))
        return True


class TruncateFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super(TruncateFormatter, self).__init__(*args, **kwargs)
        self.max_len = 240

    def format(self, record):
        if len(record.msg) > self.max_len:
            record.msg = record.msg[:self.max_len - 3] + '...'
        return super(TruncateFormatter, self).format(record)


def main():
    parser = OptionParser(version='%prog {0}'.format(__version__))
    parser.add_option('-c', '--config', metavar='SECTION', default='DEFAULT',
                      help=('Select the config section to load the settings '
                            'from.'))
    parser.add_option('-p', '--plugin-dir', metavar='DIR',
                      help='Specify the path to a folder containing plugins.')
    parser.add_option('-l', '--log-file',
                      help='Log all messages to the specified file.')
    options, _ = parser.parse_args()

    if bool(options.log_file):
        logger = logging.getLogger('turntable-api')
        logger.setLevel(logging.DEBUG)

        if options.log_file != '-':
            handler = logging.FileHandler(options.log_file)
        else:
            handler = logging.StreamHandler()

        formatter = TruncateFormatter('%(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    try:
        bot = LazySusan(config_section=options.config,
                        plugin_dir=options.plugin_dir,
                        enable_logging=bool(options.log_file))
    except LazySusanException as exc:
        print(exc.message)
        sys.exit(1)

    bot.start()
