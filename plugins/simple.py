from . import Plugin

class Echo(Plugin):
    '''Simply echo everything after /echo.'''
    COMMAND = '/echo'

    def handle(self, bot, message, data):
        bot.reply(message, data)
