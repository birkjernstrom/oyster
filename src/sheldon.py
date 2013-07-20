# -*- coding: utf-8 -*-
"""

http://bit.ly/1baSfhM
"""

import shlex

# http://bit.ly/1baSfhM#tag_02_04
RESERVED_WORDS = frozenset([
    '!', '{', '}', 'case',
    'do', 'done', 'elif', 'else',
    'esac', 'fi', 'for', 'if',
    'in', 'then', 'until', 'while',
])

CONTROL_OPERATORS = frozenset([';', '|', '&&', '||'])

STDIN = 0
STDOUT = 1
STDERR = 2

STDFD_MAPPING = {
    STDIN: 'stdin',
    STDOUT: 'stdout',
    STDERR: 'stderr',
}

class Redirect(object):
    def __init__(self, source, destination, mode='w'):
        self.source = source
        self.destination = destination

        if self.is_destination_stdfd():
            mode = 'w'

        self.mode = mode

    def is_source_stdin(self):
        return self.source == STDIN

    def is_source_stdout(self):
        return self.source == STDOUT

    def is_source_stderr(self):
        return self.source == STDERR

    def is_destination_stdfd(self):
        return self.destination in STDFD_MAPPING

    def is_destination_stdin(self):
        return self.destination == STDIN

    def is_destination_stderr(self):
        return self.destination == STDERR

    def is_destination_stdout(self):
        return self.destination == STDOUT

    def __str__(self):
        source = str(self.source) if not self.is_source_stdout() else ''
        if not self.is_destination_stdfd():
            separator = ' '
            operator = '>' if self.mode == 'w' else '>>'
        else:
            separator = ''
            operator = '>&'

        destination = str(self.destination)
        as_string = '{source}{operator}{separator}{destination}'
        return as_string.format(source=source, operator=operator,
                                separator=separator, destination=destination)

class Command(object):
    def __init__(self,
                 tokens,
                 before=None,
                 before_operator=None,
                 after=None,
                 after_operator=None):
        """
        """
        self.program = tokens[0]
        self.arguments = tuple(tokens[1:])
        self.tokens = tuple(tokens)

        self.as_string = ' '.join(self.tokens)

        self.redirects = tuple([])
        self._process_arguments(self.arguments)

    def get_options(self):
        """Retrieve a copy of the command options."""
        # Changes to the options dict will not propagate to the
        # tokens, arguments or string representation of the command.
        # Therefore, the options are intended to be read-only which this
        # API hopefully makes clear by making the attribute "private" and
        # the accessor return a copy of the dict.
        return self._options.copy()

    def has_option(self, name):
        return name in self._options

    def get_option_values(self, name, *args):
        return self._options.get(name, *args)

    def get_option_count(self, name):
        values = self.get_option_values(name)
        if values:
            return len(values)
        return 0

    def __str__(self):
        return self.as_string

    def _register_redirect(self, token, output_file=None):
        if is_quoted(token):
            return

        index = token.find('>')
        if index == -1:
            return

        source = 1
        if index:
            try:
                source = int(token[index - 1])
            except ValueError:
                pass

        mode = 'w'
        destination = None

        try:
            next_index = index + 1
            if token[next_index] == '&':
                destination = int(token[next_index:])
            elif token[next_index] == '>':
                mode = 'a'
                destination = output_file
        except IndexError, ValueError:
            pass

        if not destination:
            return

        if hasattr(destination, 'lstrip'):
            destination = destination.lstrip()

        r = Redirect(source, destination, mode=mode)
        redirects = list(self.redirects)
        redirects.append(r)
        self.redirects = tuple(redirects)

    def _process_arguments(self, arguments):
        def sanitize_value(value):
            if not hasattr(value, 'isalpha'):
                return value

            if is_quoted(value):
                value = value[1:-1]
            return value

        def get_value(next_token):
            if not next_token.startswith('-'):
                return sanitize_value(next_token)
            return True

        options = {}
        for index, token in enumerate(arguments):
            try:
                next_token = arguments[index + 1]
            except IndexError:
                next_token = None

            if not token.startswith('-'):
                self._register_redirect(token, output_file=next_token)
                continue

            if token.startswith('--'):
                key, _, value = token.partition('=')
                if value:
                    value = sanitize_value(value)
                else:
                    value = get_value(next_token)
                options.setdefault(key, []).append(value)
            else:
                keys = list(token[1:])
                for key in keys:
                    value = get_value(next_token)
                    options.setdefault('-' + key, []).append(value)

        self._options = options


def tokenize(string):
    return shlex.split(string, posix=True)


def is_comment(string):
    return string.lstrip()[0] == '#'


def is_script(string):
    tokens = string if hasattr(string, 'append') else tokenize(string)
    return tokens[0] in RESERVED_WORDS


def is_quoted(string):
    return ((string.startswith('"') and string.endswith('"')) or
            (string.startswith("'") and string.endswith("'")))


def is_command(string, tokens=None):
    if not string:
        return False

    if is_comment(string):
        return False

    if is_quoted(string):
        return False

    tokens = tokens if tokens else tokenize(string)
    if not tokens:
        return False

    if is_script(tokens):
        return False
    return True


def parse(string):
    if not string:
        return None

    tokens = tokenize(string)
    if not is_command(string, tokens):
        return None

    commands = []
    chained_by = None
    command_tokens = []
    control_operator_lookup = dict(zip(CONTROL_OPERATORS, CONTROL_OPERATORS))
    for index, token in enumerate(tokens + [';']):
        if token not in control_operator_lookup:
            command_tokens.append(token)
            continue

        try:
            previous_command = commands[-1]
        except IndexError:
            previous_command = None

        command = Command(command_tokens)
        commands.append(command)

        chained_by = token
        command_tokens = []
    return commands[0]
