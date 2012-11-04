import traceback
from functools import wraps
from lazysusan.plugins import CommandPlugin


def admin_required(function):
    """A command decorator that requires an admin to run.

    Admin users are listed in lazysusan.ini under admin_ids, one per line.

    If the sending user is not an admin, a private message will be returned to
    them indicated such."""
    @wraps(function)
    def wrapper(cls, *args, **kwargs):
        if isinstance(cls, CommandPlugin):
            bot = cls.bot
        else:  # Support the built-in commands
            bot = cls

        user_id = get_sender_id(args[1])
        # Verify the user is a moderator
        if user_id not in bot.config['admin_ids']:
            message = 'You must be an admin to execute that command.'
            return bot.api.pm(message, user_id)
        return function(cls, *args, **kwargs)
    wrapper.func_dict['admin_required'] = True
    return wrapper


def admin_or_moderator_required(function):
    """A command decorator that requires either an admin or a moderator to run.

    If the sending user is neither an admin, nor a moderator, a private message
    will be returned to them indicating such.
    """
    @wraps(function)
    def wrapper(cls, *args, **kwargs):
        if isinstance(cls, CommandPlugin):
            bot = cls.bot
        else:  # Support the built-in commands
            bot = cls

        user_id = get_sender_id(args[1])
        # Verify the user is a moderator
        if user_id not in bot.moderator_ids \
                and user_id not in bot.config['admin_ids']:
            message = ('You must be either an admin or a moderator to execute '
                       'that command.')
            return bot.api.pm(message, user_id)
        return function(cls, *args, **kwargs)
    wrapper.func_dict['admin_or_moderator_required'] = True
    return wrapper


def display_exceptions(function):
    """Expand the arguments to the functions."""
    @wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except:
            traceback.print_exc()
    return wrapper


def get_sender_id(data):
    if data['command'] == 'speak':
        return data['userid']
    elif data['command'] == 'pmmed':
        return data['senderid']
    else:
        raise Exception('Unrecognized command type `{0}`'
                        .format(data['command']))


def moderator_required(function):
    """A command decorator that requires a moderator to run.

    This decorator should only be used on commands that explicitly require the
    bot to have moderator privileges. Use the `admin_or_moderator` decorator if
    you just want to control access to a specific command.

    If the sending user is not a moderator, a private message will be returned
    to them indicating such.
    """
    @wraps(function)
    def wrapper(cls, *args, **kwargs):
        if isinstance(cls, CommandPlugin):
            bot = cls.bot
        else:  # Support the built-in commands
            bot = cls

        user_id = get_sender_id(args[1])
        # Verify the user is a moderator
        if user_id not in bot.moderator_ids:
            message = 'You must be a moderator to execute that command.'
            return bot.api.pm(message, user_id)
        return function(cls, *args, **kwargs)
    wrapper.func_dict['moderator_required'] = True
    return wrapper


def no_arg_command(function):
    """Indicate that the command does not have a message."""
    @wraps(function)
    def wrapper(cls, *args, **kwargs):
        if args[0]:
            return
        return function(cls, *args[1:], **kwargs)
    return wrapper


def single_arg_command(function):
    """Indicate that the command takes a message with a single argument."""
    @wraps(function)
    def wrapper(cls, *args, **kwargs):
        if not args[0] or ' ' in args[0]:  # Input will only contain spaces
            return
        return function(cls, *args, **kwargs)
    return wrapper
