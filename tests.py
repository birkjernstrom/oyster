#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import unittest

test_directory = os.path.dirname(os.path.abspath(__file__))
test_directory = os.path.join(test_directory, 'src')
sys.path.insert(0, test_directory)

import sheldon


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.command_string = 'pip install -U -vvv -r requirements.txt'
        self.command = sheldon.parse(self.command_string)

    def test_redirect_class(self):
        r = sheldon.Redirect(sheldon.STDERR, sheldon.STDOUT)
        self.assertEqual(r.mode, 'w')
        self.assertEqual(str(r), '2>&1')
        self.assertTrue(r.is_source_stderr())
        self.assertTrue(not r.is_source_stdin())
        self.assertTrue(not r.is_source_stdout())
        self.assertTrue(r.is_destination_stdfd())
        self.assertTrue(r.is_destination_stdout())
        self.assertTrue(not r.is_destination_stdin())
        self.assertTrue(not r.is_destination_stderr())

        # Test mode override in case of standard fp to standard fp
        r = sheldon.Redirect(sheldon.STDERR, sheldon.STDOUT, mode='a')
        self.assertEqual(r.mode, 'w')

        r = sheldon.Redirect(sheldon.STDERR, 'stderr.txt', mode='a')
        self.assertEqual(str(r), '2>> stderr.txt')

        r = sheldon.Redirect(sheldon.STDERR, 'stderr.txt', mode='w')
        self.assertEqual(str(r), '2> stderr.txt')

        r = sheldon.Redirect(sheldon.STDOUT, 'stdout.txt', mode='w')
        self.assertEqual(str(r), '> stdout.txt')

        r = sheldon.Redirect(sheldon.STDOUT, 'stdout.txt', mode='a')
        self.assertEqual(str(r), '>> stdout.txt')

    def test_parse(self):
        command_string = 'cat foo.txt'
        command = sheldon.parse(command_string)
        self.assertTrue(isinstance(command, sheldon.Command))
        self.assertEqual(command.program, 'cat')
        self.assertEqual(command.arguments, ('foo.txt',))
        self.assertEqual(command.tokens, ('cat', 'foo.txt'))
        self.assertEqual(command.as_string, command_string)

        invalid_command = sheldon.parse('#cat foo.txt')
        self.assertEqual(invalid_command, None)

        invalid_command = sheldon.parse('for i in $(seq 10); do echo $i; done')
        self.assertEqual(invalid_command, None)

    def test_is_comment(self):
        comments = [
            '# This is a comment'
            '  # This too, although with spaces before it',
            '#Also a comment',
            '#Final#Comment#',
        ]
        for comment in comments:
            self.assertTrue(sheldon.is_comment(comment))

        not_comments = [
            'This is not a comment #',
            'x# Neither is this',
            'Just a normal string',
            'cat /path/to/some/file  # Especially not me',
        ]
        for command in not_comments:
            self.assertFalse(sheldon.is_comment(command))

    def test_is_script(self):
        script = """for i in $(ls /some/directory); do
            echo $i
        done
        """
        self.assertTrue(sheldon.is_script(script))

        command = 'cat /foo/bar'
        self.assertFalse(sheldon.is_script(command))

    def test_is_quoted(self):
        self.assertTrue(sheldon.is_quoted('"hello"'))
        self.assertTrue(sheldon.is_quoted("'hello'"))
        self.assertTrue(sheldon.is_quoted("''"))

        self.assertTrue(not sheldon.is_quoted('hello'))
        self.assertTrue(not sheldon.is_quoted('"hello"something'))

    def test_is_command(self):
        self.assertTrue(sheldon.is_command('cat foo.txt'))
        self.assertTrue(sheldon.is_command('cat "foo.txt"'))
        self.assertTrue(sheldon.is_command('cat while'))
        self.assertTrue(sheldon.is_command('../../do_something.sh'))

        command = 'for i in $(seq 10); do echo $i; done'
        self.assertTrue(not sheldon.is_command(command))
        self.assertTrue(not sheldon.is_command('#comment'))
        self.assertTrue(not sheldon.is_command('"not a command"'))
        self.assertTrue(not sheldon.is_command(''))

    def test_get_options(self):
        options = self.command.get_options()
        self.assertEqual(sorted(options.keys()), sorted([
            '-U', '-v', '-r',
        ]))
        second_copy = self.command.get_options()
        self.assertEqual(options, second_copy)
        self.assertTrue(id(options) != id(second_copy))

    def test_has_options(self):
        self.assertTrue(self.command.has_option('-U'))
        self.assertTrue(self.command.has_option('-v'))
        self.assertTrue(self.command.has_option('-r'))

    def test_get_option_values(self):
        values = self.command.get_option_values('-U')
        self.assertEqual(values, [True])

        values = self.command.get_option_values('-v')
        self.assertEqual(values, [True, True, True])

        values = self.command.get_option_values('-r')
        self.assertEqual(values, ['requirements.txt'])

    def test_get_option_count(self):
        self.assertEqual(self.command.get_option_count('-U'), 1)
        self.assertEqual(self.command.get_option_count('-v'), 3)
        self.assertEqual(self.command.get_option_count('-r'), 1)

    def test_string_representation(self):
        as_string = str(self.command)
        self.assertEqual(self.command_string, as_string)

class TestSimpleCommand(unittest.TestCase):
    def test_tokenize(self):
        # Only limited testing required since shlex handles the dirty work
        command = "grep -r 'foo' /some/file"
        tokens = sheldon.tokenize(command)
        self.assertTrue(isinstance(tokens, list))
        self.assertEqual(len(tokens), 4)

    def test_simple_command(self):
        command_str = 'cat -nb --fake=yes /foo/bar'
        command = sheldon.parse(command_str)
        self.assertTrue(command.program == 'cat')
        self.assertEqual(len(command.arguments), 3)
        self.assertTrue(command.has_option('-n'))
        self.assertTrue(command.has_option('-b'))
        self.assertEqual(command.get_option_values('--fake')[0], 'yes')
        self.assertEqual(str(command), command_str)

    def test_redirects(self):
        command_str = 'rm -v -r some/path/* >> deleted.txt 2>> delete_err.txt'
        command = sheldon.parse(command_str)

        r = command.redirects
        self.assertEqual(len(r), 2)
        self.assertEqual(str(r[0]), '>> deleted.txt')
        self.assertEqual(str(r[1]), '2>> delete_err.txt')

    def test_repeated_option_values(self):
        command = sheldon.parse('pip -v -v -v install sheldon')
        self.assertEqual(command.get_option_count('-v'), 3)

        cmd = 'curl -v --data "foo=bar" --data "bar=foo" http://localhost'
        command = sheldon.parse(cmd)
        values = command.get_option_values('--data')
        self.assertEqual(values[0], 'foo=bar')
        self.assertEqual(values[1], 'bar=foo')

        cmd = 'curl -v -d "foo=bar" -d "bar=foo" http://localhost'
        command = sheldon.parse(cmd)
        values = command.get_option_values('-d')
        self.assertEqual(values[0], 'foo=bar')
        self.assertEqual(values[1], 'bar=foo')

        # Determening whether the next token is actually the option value
        # or an application argument is up to the application. As illustrated
        # in by this valid, curl, command.
        cmd = 'curl -v http://localhost'
        command = sheldon.parse(cmd)
        values = command.get_option_values('-v')
        self.assertEqual(values[0], 'http://localhost')

    def test_option_sanitization(self):
        cmd = 'curl -H "Host: sheldon.com" -d bar=foo http://localhost'
        command = sheldon.parse(cmd)

        host = command.get_option_values('-H').pop()
        self.assertEqual(host, 'Host: sheldon.com')

        data = command.get_option_values('-d').pop()
        self.assertEqual(data, 'bar=foo')


if __name__ == '__main__':
    unittest.main()
