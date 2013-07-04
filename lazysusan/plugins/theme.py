"""Plugins for managing room themes."""

from lazysusan.helpers import (
    admin_or_moderator_required,
    display_exceptions,
    no_arg_command)

from lazysusan.plugins import CommandPlugin


class Theme(CommandPlugin):

    """A plugin for managing the room's current theme."""

    COMMANDS = {
        '/theme': 'get_theme',
        '/themeset': 'set_theme',
        '/themeclear': 'clear_theme',
    }

    theme = None

    @no_arg_command
    def get_theme(self, data):
        """Gets the current theme."""
        if not self.theme:
            self.bot.reply("There's no theme right now; anything goes!", data)
        else:
            self.bot.reply(
                "The current theme is: \"{}\"".format(self.theme), data)

    @display_exceptions
    @admin_or_moderator_required
    def set_theme(self, message, data):
        """Sets the current theme."""
        self.theme = message.strip()
        self.bot.api.speak("The theme is now: \"{}\"".format(self.theme))

    @display_exceptions
    @admin_or_moderator_required
    @no_arg_command
    def clear_theme(self, data):
        """Removes the current theme."""
        self.theme = None
        self.bot.api.speak("There's no theme right now; anything goes!")
