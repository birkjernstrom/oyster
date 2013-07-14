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


class Command(object):
    def __init__(self, program, arguments):
        self.options = {}
        self.program = program
        self.arguments = tuple(arguments)

        tokens = [self.program]
        tokens.extend(self.arguments)
        self.tokens = tuple(tokens)

        self.as_string = ' '.join(self.tokens)
        self._parse_options()

    def has_option(self, name):
        return name in self.options

    def get_option(self, name, *args):
        return self.options.get(name, *args)

    def __str__(self):
        return self.as_string

    def _parse_options(self):
        options = {}
        for token in self.arguments:
            if not token.startswith('-'):
                continue

            if token.startswith('--'):
                key, _, value = token.partition('=')
                options[key] = value if value else True
                continue

            keys = list(token[1:])
            map(lambda key: options.__setitem__('-' + key, True), keys)
        self.options = options

def tokenize(string):
    return shlex.split(string, posix=True)


def is_comment(string):
    return string.lstrip()[0] == '#'


def is_script(string):
    tokens = string if hasattr(string, 'append') else tokenize(string)
    return tokens[0] in RESERVED_WORDS


def parse(string):
    if is_comment(string):
        return None

    tokens = tokenize(string)
    if not tokens:
        return None

    if is_script(tokens):
        return None

    command_tokens = []
    for index, token in enumerate(tokens):
        if token == '|':
            raise NotImplemented()
        elif token == '||':
            raise NotImplemented()
        elif token == '&&':
            raise NotImplemented()
        elif token == ';':
            raise NotImplemented()

        command_tokens.append(token)
    return Command(command_tokens[0], command_tokens[1:])
