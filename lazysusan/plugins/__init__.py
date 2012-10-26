class Plugin(object):
    pass


class CommandPlugin(Plugin):
    """Subclass this class to create a plugin that contains commands.

    COMMANDS should be a dictionary of mapping from command to function that
    the class provides. The target function's docstring provides the help
    message for the command."""
    COMMANDS = None

    def __init__(self):
        self.loaded = True
        if not self.COMMANDS:
            raise PluginException('COMMANDS must be set for CommandPlugins')


class PluginException(Exception):
    def __init__(self, message):
        self.message = message
