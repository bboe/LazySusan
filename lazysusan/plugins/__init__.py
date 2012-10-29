class Plugin(object):
    def __init__(self, bot):
        self.bot = bot
        self._registered = {}
        self._reg_num = 0

    def __del__(self):
        for register_number in self._registered:
            self.unregister(register_number)

    def register(self, event, callback):
        self.bot.api.on(event, callback)
        reg_num = self._reg_num
        self._registered[reg_num] = (event, callback)
        self._reg_num += 1
        return reg_num

    def unregister(self, register_number):
        if register_number not in self._registered:
            return False
        event, callback = self._registered[register_number]
        self.bot.api.signals[event].remove(callback)
        del self._registered[register_number]
        return True


class CommandPlugin(Plugin):
    """Subclass this class to create a plugin that contains commands.

    COMMANDS should be a dictionary of mapping from command to function that
    the class provides. The target function's docstring provides the help
    message for the command."""
    COMMANDS = None

    def __init__(self, bot):
        if not self.COMMANDS:
            raise PluginException('COMMANDS must be set for CommandPlugins')
        super(CommandPlugin, self).__init__(bot)


class PluginException(Exception):
    def __init__(self, message):
        super(PluginException, self).__init__()
        self.message = message
