#!/usr/bin/env python
import os
import sys
import traceback
from ConfigParser import ConfigParser
from ttapi import Bot
from plugins import Plugin

__version__ = '0.1dev'


def display_exceptions(function):
    """Expand the arguments to the functions."""
    def wrapper(cls, *args, **kwargs):
        try:
            return function(cls, *args, **kwargs)
        except:
            traceback.print_exc()
            print data.keys()
    return wrapper


def handle_error(*args, **kwargs):
    print args
    print kwargs


class LazySusan(object):
    @staticmethod
    def _get_config(config_section):
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
            raise Exception('No lazysusan.ini found.')
        return dict(config.items(config_section))

    def __init__(self, config_section='DEFAULT'):
        config = self._get_config(config_section)
        self.bot = Bot(config['auth_id'], config['user_id'], config['room_id'])
        self.bot.on('pmmed', self.handle_pm)
        self.bot.on('ready', self.handle_ready)
        self.bot.on('speak', self.handle_room_message)
        self.bot.ws.on_error = handle_error
        self.commands = {'/about': self.cmd_about,
                         '/commands': self.cmd_commands,
                         '/help': self.cmd_help}
        self.loaded_plugins = {}
        self.username = None

    def cmd_about(self, message, data):
        """Display information about this bot."""
        if not message.strip():
            reply = ('I am powered by LazySusan version {0}. '
                     'https://github.com/bboe/LazySusan'.format(__version__))
            self.reply(reply, data)

    def cmd_commands(self, message, data):
        """List the available commands."""
        if message.strip():
            return
        reply = 'Available commands: '
        reply += ', '.join(sorted(self.commands.keys()))
        self.reply(reply, data)

    def cmd_help(self, message, data):
        """With no arguments, display this message. Otherwise, display the help
        for the given command."""
        def docstr(item):
            lines = []
            for line in item.__doc__.split('\n'):
                line = line.strip()
                if line:
                    lines.append(line)
            return ' '.join(lines)

        message = message.strip()
        if not message:
            reply = docstr(self.cmd_help)
        elif not message.isspace():
            if message in self.commands:
                reply = docstr(self.commands[message])
            else:
                reply = '`{0}` is not a valid command.'.format(message)
        else:
            return
        self.reply(reply, data)

    def load_plugin(self, plugin_name):
        parts = plugin_name.split('.')
        if len(parts) > 1:
            module_name = '.'.join(parts[:-1])
            class_name = parts[-1]
        else:
            # Use the titlecase format of the module name as the class name
            module_name = parts[0]
            class_Name = parts[0].title()

        try:
            module = __import__('plugins.{0}'.format(module_name),
                                fromlist=[class_name])
            plugin = getattr(module, class_name)()
            plugin.__class__.NAME = plugin_name
            cmd = plugin.COMMAND
            if plugin.COMMAND in self.commands:
                other = self.commands[plugin.COMMAND]
                if isinstance(other, Plugin):
                    print('`{0}` conflicts with `{1}` for command `{2}`.'
                          .format(plugin_name, other.NAME, plugin.COMMAND))
                else:
                    print('`{0}` cannot use the reserved command `{1}`.'
                          .format(plugin_name, plugin.COMMAND))
                return False
            self.commands[cmd] = plugin
            self.loaded_plugins[plugin_name] = plugin
            return True
        except (AttributeError, ImportError):
            print('`{0}` is not a valid plugin'.format(plugin_name))
            return False

    @display_exceptions
    def handle_pm(self, data):
        self.process_message(data)

    @display_exceptions
    def handle_ready(self, _):
        self.bot.userInfo(self.set_username)

    @display_exceptions
    def handle_room_message(self, data):
        if self.username and self.username != data['name']:
            self.process_message(data)

    def process_message(self, data):
        parts = data['text'].split()
        command = parts[0]
        if len(parts) == 1:
            message = ''
        else:
            message = ' '.join(parts[1:])  # Normalize with single spaces
        handler = self.commands.get(command)
        if not handler:
            return

        if isinstance(handler, Plugin):
            handler.handle(self, message, data)
        else:
            handler(message, data)

    def reply(self, message, data):
        if data['command'] == 'speak':
            self.bot.speak(message)
        elif data['command'] == 'pmmed':
            self.bot.pm(message, data['senderid'])
        else:
            raise Exception('Unrecognized command type `{0}`'
                            .format(data['command']))

    def set_username(self, data):
        self.username = data['name']

    def start(self):
        self.bot.start()


def main():
    bot = LazySusan()
    bot.load_plugin('simple.Echo')
    bot.start()


if __name__ == '__main__':
    sys.exit(main())
