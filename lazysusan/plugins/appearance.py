"""A set of plugins that affect LazySusan's appearance."""

from lazysusan.helpers import display_exceptions, single_arg_command
from lazysusan.plugins import CommandPlugin


class Appearance(CommandPlugin):

    """A plugin that enables changing the bot's avatar and machine."""

    COMMANDS = {'/botavatar': 'set_avatar',
                '/botmachine': 'set_machine'}

    @display_exceptions
    @single_arg_command
    def set_avatar(self, message, data):
        """Set's the bot's avatar to the desired avatar id."""
        @display_exceptions
        def callback(cb_data):
            """Handle the response to the setAvatar API call."""
            if not cb_data['success']:
                self.bot.reply(cb_data['err'], data)
        if not message.isdigit():
            self.bot.reply('`{0}` is not a valid avatar id.'.format(message),
                           data)
            return
        self.bot.api.setAvatar(message, callback)

    @display_exceptions
    @single_arg_command
    def set_machine(self, message, data):
        """Set's the bot's machine.

        Available machines are: linux, mac, pc, chrome"""
        @display_exceptions
        def callback(cb_data):
            """Handle the response to the modifyLaptop API call."""
            if cb_data['success']:
                self.bot.reply('Bot change successful.'
                               'You may need to re-join the table.', data)
        if message in ('android', 'iphone'):
            self.bot.reply('Preventing change that disables PMs.', data)
        elif message not in ('linux', 'mac', 'pc', 'chrome'):
            self.bot.reply('`{0}` is not a valid machine.'.format(message),
                           data)
        else:
            self.bot.api.modifyLaptop(message, callback)
