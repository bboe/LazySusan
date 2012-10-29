#!/usr/bin/env python
import os
import sys
from ConfigParser import ConfigParser
from lazysusan.helpers import (display_exceptions, get_sender_id,
                               moderator_required, no_arg_command,
                               single_arg_command)
from lazysusan.plugins import CommandPlugin
from optparse import OptionParser
from ttapi import Bot

__version__ = '0.1rc2'


def handle_error(*args, **kwargs):
    print args
    print kwargs


class LazySusanException(Exception):
    pass


class LazySusan(object):
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

    def __init__(self, config_section, plugin_dir):
        if plugin_dir:
            if os.path.isdir(plugin_dir):
                sys.path.append(plugin_dir)
            else:
                print('`{0}` is not a directory.'.format(plugin_dir))

        config = self._get_config(config_section)
        self._loaded_plugins = {}
        self.api = Bot(config['auth_id'], config['user_id'], config['room_id'])
        self.api.on('add_dj', self.handle_add_dj)
        self.api.on('deregistered', self.handle_user_leave)
        self.api.on('new_moderator', self.handle_add_moderator)
        self.api.on('pmmed', self.handle_pm)
        self.api.on('ready', self.handle_ready)
        self.api.on('registered', self.handle_user_join)
        self.api.on('rem_dj', self.handle_remove_dj)
        self.api.on('rem_moderator', self.handle_remove_moderator)
        self.api.on('roomChanged', self.handle_room_change)
        self.api.on('speak', self.handle_room_message)
        self.api.ws.on_error = handle_error
        self.bot_id = config['user_id']
        self.commands = {'/about': self.cmd_about,
                         '/commands': self.cmd_commands,
                         '/help': self.cmd_help,
                         '/plugin_load': self.cmd_plugin_load,
                         '/plugin_unload': self.cmd_plugin_unload,
                         '/plugins': self.cmd_plugins}
        self.config = config
        self.dj_ids = set()
        self.listener_ids = set()
        self.max_djs = None
        self.moderator_ids = set()
        self.username = None

        # Load plugins after everything has been initialized
        for plugin in config['plugins'].split('\n'):
            self.load_plugin(plugin)

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
    def cmd_about(self, message, data):
        """Display information about this bot."""
        reply = ('I am powered by LazySusan version {0}. '
                 'https://github.com/bboe/LazySusan'.format(__version__))
        self.reply(reply, data)

    @no_arg_command
    def cmd_commands(self, message, data):
        """List the available commands."""
        if self.is_moderator(data):  # All commands
            commands = self.commands.keys()
        else:  # Exclude moderator commands
            commands = {}
            for command, func in self.commands.items():
                if not func.func_dict.get('moderator_required'):
                    commands[command] = func
        reply = 'Available commands: '
        reply += ', '.join(sorted(commands))
        self.reply(reply, data)

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
                func = self.commands[message]
                if func.func_dict.get('moderator_required') and \
                        not self.is_moderator(data):
                    return
                reply = docstr(self.commands[message])
            else:
                reply = '`{0}` is not a valid command.'.format(message)
        else:
            return
        self.reply(reply, data)

    @moderator_required
    @single_arg_command
    def cmd_plugin_load(self, message, data):
        """Load the specified plugin."""
        if message in self._loaded_plugins:
            reply = 'Plugin `{0}` is already loaded.'.format(message)
        elif self.load_plugin(message):
            reply = 'Plugin `{0}` loaded.'.format(message)
        else:
            reply = 'Plugin `{0}` could not be loaded.'.format(message)
        self.reply(reply, data)

    @moderator_required
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

    @moderator_required
    @no_arg_command
    def cmd_plugins(self, message, data):
        """Display the list of loaded plugins."""
        reply = 'Loaded plugins: '
        reply += ', '.join(sorted(self._loaded_plugins.keys()))
        self.reply(reply, data)

    def is_moderator(self, item):
        """item can either be the user_id, or a dictionary from a message."""
        if isinstance(item, dict):
            item = get_sender_id(item)
        return item in self.moderator_ids

    @display_exceptions
    def handle_add_dj(self, data):
        for user in data['user']:
            self.dj_ids.add(user['userid'])

    @display_exceptions
    def handle_add_moderator(self, data):
        self.moderator_ids.add(data['userid'])

    @display_exceptions
    def handle_pm(self, data):
        self.process_message(data)

    @display_exceptions
    def handle_ready(self, _):
        self.api.userInfo(self.set_username)

    @display_exceptions
    def handle_remove_dj(self, data):
        for user in data['user']:
            self.dj_ids.remove(user['userid'])

    @display_exceptions
    def handle_remove_moderator(self, data):
        self.moderator_ids.remove(data['userid'])

    @display_exceptions
    def handle_room_change(self, data):
        self.dj_ids = set(data['room']['metadata']['djs'])
        self.listener_ids = set(x['userid'] for x in data['users'])
        self.max_djs = data['room']['metadata']['max_djs']
        self.moderator_ids = set(data['room']['metadata']['moderator_id'])

    @display_exceptions
    def handle_room_message(self, data):
        if self.username and self.username != data['name']:
            self.process_message(data)

    @display_exceptions
    def handle_user_join(self, data):
        for user in data['user']:
            self.listener_ids.add(user['userid'])

    @display_exceptions
    def handle_user_leave(self, data):
        for user in data['user']:
            self.listener_ids.remove(user['userid'])

    def load_plugin(self, plugin_name):
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
            try:
                module = __import__(module_name, fromlist=[class_name])
                if module:
                    break
            except ImportError:
                pass
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


def main():
    parser = OptionParser(version='%prog {0}'.format(__version__))
    parser.add_option('-c', '--config', metavar='SECTION', default='DEFAULT',
                      help=('Select the config section to load the settings '
                            'from.'))
    parser.add_option('-p', '--plugin-dir', metavar='DIR',
                      help='Specify the path to a folder containing plugins.')
    options, _ = parser.parse_args()

    try:
        bot = LazySusan(config_section=options.config,
                        plugin_dir=options.plugin_dir)
    except LazySusanException as exc:
        print(exc.message)
        sys.exit(1)

    bot.start()
