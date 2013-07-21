# -*- coding: utf-8 -*-
"""

http://bit.ly/1baSfhM
"""

import shlex
from subprocess import list2cmdline

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


class Chain(object):
    def __init__(self):
        self.commands = []
        self._strings = []
        self._operators = []

    def append(self, command, chained_by=None):
        command = self._normalize_command(command)
        chained_by = chained_by if chained_by else ';'

        self.commands.append(command)
        self._strings.append(str(command))
        self._operators.append(chained_by)

    def insert(self, index, command, chained_by=None):
        command = self._normalize_command(command)
        chained_by = chained_by if chained_by else ';'

        self.commands.insert(index, command)
        self._strings.insert(index, str(command))
        self._operators.insert(index, chained_by)

    def index(self, command, *args):
        if hasattr(command, 'get_options'):
            return self.commands.index(command, *args)
        return self._strings.index(command, *args)

    def pop(self, *args):
        ret = self.commands.pop(*args)
        self._strings.pop(*args)
        self._operators.pop(*args)
        return ret

    def remove(self, command):
        index = self.index(command)
        del self.commands[index]
        del self._strings[index]
        del self._operators[index]

    def __add__(self, chain):
        c = Chain()
        c.commands = self.commands + chain.commands
        c._strings = self._strings + chain._strings
        c._operators = self._operators + chain._operators
        return c

    def __iadd__(self, chain):
        self.commands += chain.commands
        self._strings += chain._strings
        self._operators += chain._operators
        return self

    def __contains__(self, command):
        if not hasattr(command, 'isalpha'):
            return command in self.commands
        return command in self._strings

    def __delitem__(self, *args):
        self.commands.__delitem__(*args)
        self._strings.__delitem__(*args)
        self._operators.__delitem__(*args)

    def __delslice__(self, *args):
        self.commands.__delslice__(*args)
        self._strings.__delslice__(*args)
        self._operators.__delslice__(*args)

    def __eq__(self, chain):
        return str(self) == str(chain)

    def __ne__(self, chain):
        return not self.__eq__(chain)

    def __getitem__(self, index):
        return self.commands.__getitem__(index)

    def __getslice__(self, *args):
        c = Chain()
        c.commands = self.commands.__getslice__(*args)
        c._strings = self._strings.__getslice__(*args)
        c._operators = self._operators.__getslice__(*args)
        return c

    def __len__(self):
        return self.commands.__len__()

    def __str__(self):
        operators = self._operators[:]
        operators[0] = None
        commands = [str(command) for command in self.commands]

        components = []
        for index, operator in enumerate(operators):
            if operator:
                whitespace = ' '
                if operator == ';':
                    whitespace = ''
                components.append('{0}{1} '.format(whitespace, operator))
            components.append(commands[index])
        return ''.join(components)

    def _normalize_command(self, command):
        if hasattr(command, 'get_options'):
            return command

        chain = parse(command)
        if not chain:
            raise ValueError('invalid command')
        return chain.pop()


class Command(object):
    def __init__(self, tokens):
        """
        """
        self.program = tokens[0]
        self.arguments = tuple(tokens[1:])
        self.tokens = tuple(tokens)

        self.as_string = list2cmdline(self.tokens)
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
        except (IndexError, ValueError):
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
            if (hasattr(next_token, 'startswith') and
                not next_token.startswith('-')):
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


def split_token_by_operators(string):
    if len(string) <= 1 or is_quoted(string):
        return [string]

    tokens = []
    characters = []
    consume_next = False
    previous_character = None
    for index, character in enumerate(string):
        if consume_next:
            consume_next = False
            previous_character = character
            continue

        try:
            next_character = string[index + 1]
        except IndexError:
            next_character = ''

        is_escaped = (character == '\\' and
                      previous_character != '\\' and
                      next_character != '\\')

        if is_escaped:
            characters.append(character)
            characters.append(next_character)
            consume_next = True
            continue

        found = False
        for operator in CONTROL_OPERATORS:
            if operator == character:
                found = True
                break

            if operator == character + next_character:
                found = True
                consume_next = True
                break

        previous_character = character
        if found:
            tokens.append(''.join(characters))
            tokens.append(operator)
            characters = []
        else:
            characters.append(character)

    if characters:
        tokens.append(''.join(characters))
    return tokens

def tokenize(string):
    processed = []
    lex = shlex.shlex(string, posix=True)
    lex.whitespace_split = True
    lex.commenters = ''

    in_substitution = False
    substitution_closer = None
    substitution_tokens = []

    while True:
        token = lex.get_token()
        if token is None:
            break

        if in_substitution:
            substitution_tokens.append(token)
            if token.endswith(substitution_closer):
                processed.append(''.join(substitution_tokens))
                substitution_tokens = []
                in_substitution = False
            continue

        if token.startswith('$('):
            in_substitution = True
            substitution_closer = ')'
            substitution_tokens.append(token)
            continue

        if token.startswith('`'):
            in_substitution = True
            substitution_closer = '`'
            substitution_tokens.append(token)
            continue

        # Handle the case of: cd /some/path&&ls
        processed.extend(split_token_by_operators(token))

    if substitution_tokens:
        processed.append(''.join(substitution_tokens))
    return processed


def is_comment(string):
    return string.lstrip()[0] == '#'


def is_script(string):
    is_script = False
    string = string.lstrip()
    for reserved in RESERVED_WORDS:
        if string.startswith(reserved):
            is_script = True
            break
    return is_script


def is_quoted(string):
    string = string.lstrip()
    return ((string.startswith('"') and string.endswith('"')) or
            (string.startswith("'") and string.endswith("'")))


def is_command(string, tokens=None):
    if not string:
        return False

    if is_comment(string):
        return False

    if is_quoted(string):
        return False

    if is_script(string):
        return False
    return True


def parse(string):
    chain = Chain()
    if not (string or hasattr(string, 'isalpha')):
        return chain

    tokens = tokenize(string)
    if not is_command(string, tokens):
        return chain

    chained_by = None
    command_tokens = []
    to_parse = tokens + [';']
    control_operator_lookup = dict(zip(CONTROL_OPERATORS, CONTROL_OPERATORS))
    for index, token in enumerate(to_parse):
        if token not in control_operator_lookup:
            command_tokens.append(token)
            continue

        if is_script(command_tokens[0]):
            # Abort entire chain if script is detected
            chain = Chain()
            break

        command = Command(command_tokens)
        chain.append(command, chained_by=chained_by)
        chained_by = token
        command_tokens = []
    return chain
