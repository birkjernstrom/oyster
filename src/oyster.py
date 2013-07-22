# -*- coding: utf-8 -*-
"""
    Oyster
    ~~~~~

    **A Python parser of shell commands.**

    This module strives to support commands executed within the sh, bash
    and zsh shells alike. An important limitation to mention is that Oyster
    does not support parsing of scripted commands, i.e:

            for i in $(seq 10); do echo $i; done

    This might change in a future version of Oyster - at least in order to
    support one-liners like the one above.

    *Features to be included in upcoming releases:*

        - Extended :class:`Chain` API to ease extending the chain with
          additional commands and various control operators.

        - Parse command substitutions

    *Features which may be included in upcoming releases:*

        - Support for parsing scripted commands

        - Command execution simulation: Iterate through the command chain
          depending on the given, simulated, exit code and/or output
          of the current command within the iteration.

    :copyright: (c) 2013 by Birk Nilson.
    :license: BSD, see LICENSE for more details.
"""

import shlex
from subprocess import list2cmdline

__author__ = 'Birk Nilson <birk@tictail.com>'
__copyright__ = "Copyright 2013, Birk Nilson"
__license__ = 'BSD'
__version__ = '0.1.0'
__all__ = [
    # Constants
    'RESERVED_WORDS', 'CONTROL_OPERATORS', 'STDIN',
    'STDOUT', 'STDERR', 'STDFD_MAPPING',

    # Classes
    'Redirect', 'Chain', 'Command',

    # Functions
    'split_token_by_operators', 'tokenize', 'is_comment',
    'is_script', 'is_quoted', 'is_command', 'parse',
]


#: Set of words which are reserved in the shell.
#: See: http://bit.ly/1baSfhM#tag_02_04
RESERVED_WORDS = frozenset([
    '!', '{', '}', 'case',
    'do', 'done', 'elif', 'else',
    'esac', 'fi', 'for', 'if',
    'in', 'then', 'until', 'while',
])

#: Control operators which chain multiple commands
CONTROL_OPERATORS = frozenset([';', '|', '&&', '||'])

#: The file descriptor of the standard input file
STDIN = 0
#: The file descriptor of the standard output file
STDOUT = 1
#: The file descriptor of the standard error file
STDERR = 2

#: Mapping of the standard file descriptors and their common names
STDFD_MAPPING = {
    STDIN: 'stdin',
    STDOUT: 'stdout',
    STDERR: 'stderr',
}

class Redirect(object):
    """A :class:`Redirect` instance represents the various output redirections
    performed by the command it is attached to.

    Each redirect has a :attr:`source` and :attr:`destination` in which the
    source is the value of the standard file descriptor to be redirected to
    the given :attr:`destination` - which can be either a
    file descriptor or a filename.

    The method in which the redirect is performed is determined by the
    :attr:`mode` which can be either ``w`` or ``a``. The ``w`` mode will
    write to the :attr:`destination` while ``a`` will append to
    it, i.e '>' vs. '>>'.

    When a shell command is parsed all redirects will automatically be
    initiated and assigned to their respective command as shown below:

        >>> import oyster
        >>> cmd = 'cp -v -r myfiles/* >> copied.log 2>> errors.log'
        >>> command = oyster.parse(cmd)[0]
        >>> str(command.redirects[0])
        '>> copied.log'
        >>> str(command.redirects[1])
        '2>> errors.log'
        >>> command.redirects[0].is_source_stdout()
        True

    :param source: An integer representing the standard file descriptor to
                   be redirected.
    :param destination: Either an integer representing the standard file
                        descriptor which output should be redirected to or
                        a string representing the filename.
    :param mode: Either ``w`` or ``a`` depending on whether the redirect should
                 write or append its output to the :attr:`destination`.
    """
    def __init__(self, source, destination, mode='w'):
        #: Which standard file descriptor to be redirected
        self.source = source
        #: The destination of the redirect which can either be a standard
        #: file descriptor (integer) or a filename (string.
        self.destination = destination

        if self.is_destination_stdfd():
            mode = 'w'

        #: The mode in which the redirect should be performed.
        #: ``w`` represents writes (>) & ``a`` represents appends (>>).
        self.mode = mode

    def is_source_stdin(self):
        """Check if the source is the standard input file descriptor."""
        return self.source == STDIN

    def is_source_stdout(self):
        """Check if the source is the standard output file descriptor."""
        return self.source == STDOUT

    def is_source_stderr(self):
        """Check if the source is the standard error file descriptor."""
        return self.source == STDERR

    def is_destination_stdfd(self):
        """Check if the destination is a standard file descriptor."""
        return self.destination in STDFD_MAPPING

    def is_destination_stdin(self):
        """Check if the destination is the standard input file descriptor."""
        return self.destination == STDIN

    def is_destination_stdout(self):
        """Check if the destination is the standard output file descriptor."""
        return self.destination == STDOUT

    def is_destination_stderr(self):
        """Check if the destination is the standard error file descriptor."""
        return self.destination == STDERR

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
    """A list-like object containing all the individual commands which have
    been chained together using control operators in the shell.

    Unlike a regular Python list the :class:`Chain` instance does not implement the
    ``.extend``, ``.sort`` and ``.count`` methods. Also it introduces the
    ``chain_by`` parameter to the ``.append`` and ``.insert`` methods.

    Oyster treats all shell commands as a chain even in the case of a single
    program being executed. This is a design choice to simplify usage of the
    module since it is easier if :func:`parse` consistently returns the
    same type. As shown here:

        >>> import oyster
        >>> commands = oyster.parse('ps aux | grep python')
        >>> len(commands)
        2
        >>> ps, grep = commands
        >>> ps.arguments
        ('aux',)
        >>> ps = oyster.parse('ps aux')[0]
        >>> ps.program
        'ps'

    """
    def __init__(self):
        #: A list containing all the individual :class:`Command` instances
        self.commands = []
        self._strings = []
        self._operators = []

    def append(self, command, chained_by=None):
        """C.append(command[, chained_by=';'])

        Append given ``command`` to the chain with the
        ``chained_by`` as the separating control operator.

        :param command: A string representing the command or an
                        instance of :class:`Command`
        :param chained_by: One of the control operators defined in the
                           :attr:`CONTROL_OPERATORS` constant. The default
                           is ``;``.
        """
        command = self._normalize_command(command)
        chained_by = self._normalize_chained_by(chained_by)

        self.commands.append(command)
        self._strings.append(str(command))
        self._operators.append(chained_by)

    def insert(self, index, command, chained_by=None):
        """C.insert(index, command[, chained_by=';'])

        Insert given ``command`` to the chain at ``index`` with the
        ``chained_by`` as the separating control operator.

        :param index: At which index of the chain to insert the command
        :param command: A string representing the command or an
                        instance of :class:`Command`
        :param chained_by: One of the control operators defined in the
                           :attr:`CONTROL_OPERATORS` constant. The default
                           is ``;``.
        """
        command = self._normalize_command(command)
        chained_by = self._normalize_chained_by(chained_by)

        self.commands.insert(index, command)
        self._strings.insert(index, str(command))
        self._operators.insert(index, chained_by)

    def index(self, command, *args):
        """C.index(command, [start, [stop]]) -> first index of command.

        Raises ValueError if the command is not present.

        :param command: A string representing the command or an
                        instance of :class:`Command`
        :param start: At which index to start the search
        :param stop: At which index to stop the search
        """
        if hasattr(command, 'get_options'):
            return self.commands.index(command, *args)
        return self._strings.index(command, *args)

    def pop(self, *args):
        """C.pop([index]) -> command -- remove and return item at index (default last).

        Raises IndexError if list is empty or index is out of range.

        :param index: Which command to pop by index
        """
        ret = self.commands.pop(*args)
        self._strings.pop(*args)
        self._operators.pop(*args)
        return ret

    def remove(self, command):
        """C.remove(command) -- remove first occurrence of command.

        Raises ValueError if the value is not present.

        :param command: A string representing the command or an
                        instance of :class:`Command`
        """
        index = self.index(command)
        del self.commands[index]
        del self._strings[index]
        del self._operators[index]

    def __add__(self, chain):
        if hasattr(chain, 'isalpha'):
            chain = parse(chain)

        c = Chain()
        c.commands = self.commands + chain.commands
        c._strings = self._strings + chain._strings
        c._operators = self._operators + chain._operators
        return c

    def __iadd__(self, chain):
        if hasattr(chain, 'isalpha'):
            chain = parse(chain)

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

    def _normalize_chained_by(self, chained_by):
        if not chained_by:
            return ';'

        if chained_by in CONTROL_OPERATORS:
            return chained_by
        raise ValueError('invalid control operator given')


class Command(object):
    """A representation of a single - unchained - command.

    Contains the name of the program being executed along with all the
    arguments passed to it. Furthermore, it processes the given arguments
    to convert them into ``options``: A dictionary mapping options to their
    given values.

    An argument is considered an option in case it is prefixed with ``-``.
    In other words ``-v``, ``--install`` and ``-c`` are all considered
    to be options.

    **Caveat #1:**

    How their values are retrieved is an interesting topic. The easiest case
    is the scenario of an argument being --foo=bar. Then the option name is
    ``foo`` and its corresponding value ``bar``. Single-hyphenated arguments
    is a trickier matter though. Consider the following:

        pip install -v -r requirements.txt

    In the case above Oyster will treat the ``-v`` argument as a boolean
    option, i.e giving it a value of ``True``. In case all single-hyphenated
    arguments would be considered boolean options then, everyone who knows
    pip, will know that the stored value would be useless & incorrect.

    Therefore, in the case a single-hypenhated argument is followed by a
    non-hypenated argument the latter is considered the formers value.
    Naturally, this is not bulletproof neither, but it is better to be
    more greedy in this scenario since the arguments are also kept, untouched,
    in the :attr:`arguments` attribute. After all: Determening how the
    arguments should be handled is ultimately up to the targetted
    program in the command.

    **Caveat #2:**

    The :attr:`as_string` and thus str(self) value is retrieved using
    the ``subprocess.list2cmdline`` function. In case the command is retrieved
    via :func:`parse` this opens up for the possibility of minor differences
    in how command arguments are quoted. Therefore, a direct comparison
    of the input command and the string representation of its instance
    is not guaranteed to be successful.

    :param tokens: A list of all the tokens the command consists of
    """
    def __init__(self, tokens):
        #: Name of the program which the command is executing
        self.program = tokens[0]
        #: A tuple of all the arguments passed to the program
        self.arguments = tuple(tokens[1:])
        #: A tuple containing all tokens which the command consists of.
        #: In other words: tuple([self.program] + list(self.arguments))
        self.tokens = tuple(tokens)
        #: The string representation of the command. Used in str(self)
        self.as_string = list2cmdline(self.tokens)
        #: A tuple containing all the instances of :class:`Redirect`
        #: found during processing of the command.
        self.redirects = tuple([])
        self._process_arguments(self.arguments)

    def get_options(self):
        """Retrieve a copy of the command options.

        A copy is returned to prevent tampering with the instance options.
        The :class:`Command` class is not designed to support mutations.
        """
        # Changes to the options dict will not propagate to the
        # tokens, arguments or string representation of the command.
        # Therefore, the options are intended to be read-only which this
        # API hopefully makes clear by making the attribute "private" and
        # the accessor return a copy of the dict.
        return self._options.copy()

    def has_option(self, name):
        """Check whether the command includes the given option ``name``.

        :param name: Name of the option including hyphens.
        """
        return name in self._options

    def get_option_values(self, name, *args):
        """D.get(k[,d]) -> D[k] if k in D, else d.  d defaults to None.

        :param name: Name of the option including hyphens.
        """
        return self._options.get(name, *args)

    def get_option_count(self, name):
        """Return the amount of values stored for the given options.

        :param name: Name of the option including hyphens.
        """
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


def split_token_by_operators(token):
    """Split the given ``token`` by all containing :attr:`CONTROL_OPERATORS`.

    Each unquoted token longer than a single character is required to do this
    during tokenization of a command. Otherwise, commands which are not
    properly spaced will be treated incorrectly. As illustrated below:

        >>> import shlex
        >>> import oyster
        >>> cmd = 'cd /some/path;ls'
        >>> tokens = shlex.split(cmd, posix=True)
        >>> tokens
        ['cd', '/some/path;ls']
        >>> processed = oyster.split_token_by_operators(tokens[1])
        >>> processed
        ['/some/path', ';', 'ls']
        >>> tokens = [tokens[0]]
        >>> tokens.extend(processed)
        >>> tokens
        ['cd', '/some/path', ';', 'ls']

    :param token: The token to check for control operators
    """
    if len(token) <= 1 or is_quoted(token):
        return [token]

    tokens = []
    characters = []
    consume_next = False
    previous_character = None
    for index, character in enumerate(token):
        if consume_next:
            consume_next = False
            previous_character = character
            continue

        try:
            next_character = token[index + 1]
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
    """Tokenize given ``string`` and return a list containing all the tokens.

    The workhorse behind this function is the ``shlex`` module. However, tokens
    found via ``shlex`` are processed to ensure we handle command substitutions
    along with chained commands properly.

    :paramter string: The command - as a string - to tokenize
    """
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
    """Check whether given string is considered to be a comment.

    :param string: The string, i.e command, to check
    """
    return string.lstrip()[0] == '#'


def is_script(string):
    """Check whether given string is considered to be a script.

    This function oversimplifies what a shell script is, but covers
    the necessary basics for this module.

    :param string: The string, i.e command, to check
    """
    is_script = False
    string = string.lstrip()
    for reserved in RESERVED_WORDS:
        if string.startswith(reserved):
            is_script = True
            break
    return is_script


def is_quoted(string):
    """Check whether given string is quoted.

    :param string: The string, i.e command, to check
    """
    string = string.lstrip()
    return ((string.startswith('"') and string.endswith('"')) or
            (string.startswith("'") and string.endswith("'")))


def is_command(string, tokens=None):
    """Check whether given string is considered to be a command.

    :param string: The string, i.e command, to check
    """
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
    """Parse given ``string`` into a :class:`Chain` of :class:`Command` s.


        >>> import oyster
        >>> cmd = 'pip search -vvv --timeout=5 flask | grep session | less'
        >>> chain = oyster.parse(cmd)
        >>> len(chain)
        3
        >>> pip, grep, less = chain
        >>> pip.has_option('--timeout')
        True
        >>> pip.get_option_values('--timeout')
        ['5']
        >>> pip.get_option_count('-v')
        3
        >>> pip.arguments
        ('search', '--timeout=5', 'flask')
        >>> str(grep)
        'grep session'
        >>> str(less)
        'less'
        >>> chain.remove('less')
        >>> str(chain)
        'pip search -vvv --timeout=5 flask | grep session'
        >>> chain += 'date -u'
        >>> str(chain)
        'pip search -vvv --timeout=5 flask | grep session; date -u'
        >>> utc_date = chain[chain.index('date -u')]
        >>> str(utc_date)
        'date -u'
        >>> utc_date.get_option_values('-u')
        [True]

    :param string: The string, i.e command, to parse
    """
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
