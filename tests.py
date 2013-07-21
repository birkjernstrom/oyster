#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import unittest

test_directory = os.path.dirname(os.path.abspath(__file__))
test_directory = os.path.join(test_directory, 'src')
sys.path.insert(0, test_directory)

import oyster


class TestRedirects(unittest.TestCase):
    def test_api(self):
        r = oyster.Redirect(oyster.STDERR, oyster.STDOUT)
        self.assertEqual(r.mode, 'w')
        self.assertEqual(str(r), '2>&1')
        self.assertTrue(r.is_source_stderr())
        self.assertTrue(not r.is_source_stdin())
        self.assertTrue(not r.is_source_stdout())
        self.assertTrue(r.is_destination_stdfd())
        self.assertTrue(r.is_destination_stdout())
        self.assertTrue(not r.is_destination_stdin())
        self.assertTrue(not r.is_destination_stderr())

    def test_mode_override(self):
        # Test mode override in case of standard fp to standard fp
        r = oyster.Redirect(oyster.STDERR, oyster.STDOUT, mode='a')
        self.assertEqual(r.mode, 'w')

    def test_string_representation(self):
        r = oyster.Redirect(oyster.STDERR, 'stderr.txt', mode='a')
        self.assertEqual(str(r), '2>> stderr.txt')

        r = oyster.Redirect(oyster.STDERR, 'stderr.txt', mode='w')
        self.assertEqual(str(r), '2> stderr.txt')

        r = oyster.Redirect(oyster.STDOUT, 'stdout.txt', mode='w')
        self.assertEqual(str(r), '> stdout.txt')

        r = oyster.Redirect(oyster.STDOUT, 'stdout.txt', mode='a')
        self.assertEqual(str(r), '>> stdout.txt')


class TestChain(unittest.TestCase):
    def setUp(self):
        self.cmd = 'cat foo.txt | grep python | wc -l'
        self.chain = oyster.parse(self.cmd)

    def test_append(self):
        pass

    def test_insert(self):
        pass

    def test_index(self):
        command = oyster.Command(['mv', 'foo.txt', 'bar.txt'])
        self.assertEqual(self.chain.index('grep python'), 1)
        self.assertEqual(self.chain.index(self.chain[2]), 2)
        self.assertRaises(ValueError, self.chain.index, str(command))
        self.assertRaises(ValueError, self.chain.index, command)

    def test_index(self):
        self.assertEqual(self.chain.index('grep python'), 1)
        self.assertEqual(self.chain.index(self.chain[2]), 2)
        self.assertRaises(ValueError, self.chain.index, 'echo "Hello"')

    def test_pop(self):
        chain = oyster.parse('mv foo.txt bar.txt; ls | wc -l')
        self.assertEqual(len(chain), 3)
        wc = chain.pop()
        self.assertEqual(wc.program, 'wc')
        mv = chain.pop(0)
        self.assertEqual(mv.program, 'mv')
        self.assertEqual(len(chain), 1)
        self.assertEqual(chain[0].program, 'ls')
        self.assertRaises(IndexError, chain.pop, 1337)

    def test_remove(self):
        chain = oyster.parse('mv foo.txt bar.txt; ls | wc -l')
        chain.remove('wc -l')
        self.assertEqual(str(chain), 'mv foo.txt bar.txt; ls')
        chain.remove(chain[chain.index('ls')])
        self.assertEqual(str(chain), 'mv foo.txt bar.txt')

    def test_iteration(self):
        iterator = iter(self.chain)
        cat = iterator.next()
        grep = iterator.next()
        wc = iterator.next()

        self.assertRaises(StopIteration, iterator.next)
        self.assertEqual(cat.program, 'cat')
        self.assertEqual(grep.program, 'grep')
        self.assertEqual(wc.program, 'wc')

    def test_chain_add(self):
        cmd = 'mv foo.txt bar.txt'
        chain = oyster.parse(cmd)
        combined = self.chain + chain

        self.assertTrue(id(combined) != id(self.chain))
        self.assertTrue(id(combined) != id(chain))

        as_str  = 'cat foo.txt | grep python | wc -l; mv foo.txt bar.txt'

        self.assertEqual(len(self.chain), 3)
        self.assertEqual(len(chain), 1)
        self.assertEqual(len(combined), 4)
        self.assertEqual(str(combined), as_str)

    def test_chain_iadd(self):
        first_cmd = 'mv foo.txt bar.txt'
        first = oyster.parse(first_cmd)
        second_cmd = 'cat bar.txt'
        second = oyster.parse(second_cmd)

        first_id = id(first)
        first += second

        self.assertEqual(first_id, id(first))
        self.assertEqual(len(first), 2)
        self.assertEqual(str(first), 'mv foo.txt bar.txt; cat bar.txt')
        self.assertEqual(len(second), 1)

    def test_chain_contains(self):
        cat, grep, wc = self.chain
        self.assertTrue(wc in self.chain)
        self.assertTrue('wc -l' in self.chain)
        self.assertTrue(not 'mv foo.txt bar.txt' in self.chain)

    def test_delete(self):
        chain = oyster.parse('ls | wc -l')
        self.assertEqual(len(chain), 2)
        del chain[1]
        self.assertEqual(len(chain), 1)
        self.assertEqual(str(chain), 'ls')

        try:
            del chain[1337]
            did_raise = False
        except IndexError:
            did_raise = True

        self.assertTrue(did_raise)

    def test_delete_slice(self):
        chain = oyster.parse('cd /some/path; ls | wc -l')
        self.assertEqual(len(chain), 3)
        del chain[-1]
        self.assertEqual(len(chain), 2)
        self.assertEqual(str(chain), 'cd /some/path; ls')

    def test_equal(self):
        copy = oyster.parse(str(self.chain))
        self.assertTrue(id(self.chain) != id(copy))
        self.assertEqual(self.chain, copy)

    def test_not_equal(self):
        copy = oyster.parse(str(self.chain))
        copy.append('less')
        self.assertTrue(self.chain != copy)

    def test_get_command(self):
        self.assertEqual(self.chain[2].program, 'wc')

    def test_get_slice(self):
        chain_slice = self.chain[1:]
        self.assertEqual(len(chain_slice), 2)
        self.assertEqual(str(chain_slice), 'grep python | wc -l')

    def test_chain_len(self):
        self.assertEqual(len(self.chain), 3)

class TestCommand(unittest.TestCase):
    def setUp(self):
        self.command_string = 'pip install -U -vvv -r requirements.txt'
        self.command = oyster.parse(self.command_string)[0]

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

    def test_simple_command(self):
        command_str = 'cat -nb --fake=yes /foo/bar'
        command = oyster.parse(command_str)[0]
        self.assertTrue(command.program == 'cat')
        self.assertEqual(len(command.arguments), 3)
        self.assertTrue(command.has_option('-n'))
        self.assertTrue(command.has_option('-b'))
        self.assertEqual(command.get_option_values('--fake')[0], 'yes')
        self.assertEqual(str(command), command_str)

    def test_redirects(self):
        command_str = 'rm -v -r some/path/* >> deleted.txt 2>> delete_err.txt'
        command = oyster.parse(command_str)[0]

        r = command.redirects
        self.assertEqual(len(r), 2)
        self.assertEqual(str(r[0]), '>> deleted.txt')
        self.assertEqual(str(r[1]), '2>> delete_err.txt')

    def test_repeated_option_values(self):
        command = oyster.parse('pip -v -v -v install oyster')[0]
        self.assertEqual(command.get_option_count('-v'), 3)

        cmd = 'curl -v --data "foo=bar" --data "bar=foo" http://localhost'
        command = oyster.parse(cmd)[0]
        values = command.get_option_values('--data')
        self.assertEqual(values[0], 'foo=bar')
        self.assertEqual(values[1], 'bar=foo')

        cmd = 'curl -v -d "foo=bar" -d "bar=foo" http://localhost'
        command = oyster.parse(cmd)[0]
        values = command.get_option_values('-d')
        self.assertEqual(values[0], 'foo=bar')
        self.assertEqual(values[1], 'bar=foo')

        # Determening whether the next token is actually the option value
        # or an application argument is up to the application. As illustrated
        # in by this valid, curl, command.
        cmd = 'curl -v http://localhost'
        command = oyster.parse(cmd)[0]
        values = command.get_option_values('-v')
        self.assertEqual(values[0], 'http://localhost')

    def test_option_sanitization(self):
        cmd = 'curl -H "Host: oyster.com" -d bar=foo http://localhost'
        command = oyster.parse(cmd)[0]

        host = command.get_option_values('-H').pop()
        self.assertEqual(host, 'Host: oyster.com')

        data = command.get_option_values('-d').pop()
        self.assertEqual(data, 'bar=foo')


class TestAPI(unittest.TestCase):
    def test_split_by_operators(self):
        tests = [
            ('/some/path\\\;ls;wc', 5),
            ('"a && b && c || d;"', 1),
            ('/some/path;ls', 3),
            ('/some-dir||ls|less', 5),
            ('/some/path&&ls;wc', 5),
            ('/some/path\\&\\&ls;wc', 3),
            ('/some/path\\;ls;wc', 3),
            ('/some/path\\\;ls;wc', 5),
        ]

        for test in tests:
            tokens = oyster.split_token_by_operators(test[0])
            self.assertEqual(len(tokens), test[1])

    def test_tokenize(self):
        # Only limited testing required since shlex handles the dirty work
        command = "grep -r 'foo' /some/file"
        tokens = oyster.tokenize(command)
        self.assertTrue(isinstance(tokens, list))
        self.assertEqual(len(tokens), 4)

        no_whitespace = 'cd /some/path;ls|wc -l'
        chain = oyster.parse(no_whitespace)
        self.assertTrue(len(chain), 3)
        self.assertEqual(str(chain[0]), 'cd /some/path')
        self.assertEqual(str(chain[1]), 'ls')
        self.assertEqual(str(chain[2]), 'wc -l')

        with_cmd_substitution = 'grep $(echo $1 | sed "s/^\\(.\\)/[\\1]/g")'
        chain = oyster.parse(with_cmd_substitution)
        self.assertEqual(len(chain), 1)
        self.assertEqual(len(chain[0].arguments), 1)

    def test_is_comment(self):
        comments = [
            '# This is a comment'
            '  # This too, although with spaces before it',
            '#Also a comment',
            '#Final#Comment#',
        ]
        for comment in comments:
            self.assertTrue(oyster.is_comment(comment))

        not_comments = [
            'This is not a comment #',
            'x# Neither is this',
            'Just a normal string',
            'cat /path/to/some/file  # Especially not me',
        ]
        for command in not_comments:
            self.assertFalse(oyster.is_comment(command))

    def test_is_script(self):
        script = """for i in $(ls /some/directory); do
            echo $i
        done
        """
        self.assertTrue(oyster.is_script(script))

        command = 'cat /foo/bar'
        self.assertFalse(oyster.is_script(command))

    def test_is_quoted(self):
        self.assertTrue(oyster.is_quoted('"hello"'))
        self.assertTrue(oyster.is_quoted("'hello'"))
        self.assertTrue(oyster.is_quoted("''"))

        self.assertTrue(not oyster.is_quoted('hello'))
        self.assertTrue(not oyster.is_quoted('"hello"something'))

    def test_is_command(self):
        self.assertTrue(oyster.is_command('cat foo.txt'))
        self.assertTrue(oyster.is_command('cat "foo.txt"'))
        self.assertTrue(oyster.is_command('cat while'))
        self.assertTrue(oyster.is_command('../../do_something.sh'))

        command = 'for i in $(seq 10); do echo $i; done'
        self.assertTrue(not oyster.is_command(command))
        self.assertTrue(not oyster.is_command('#comment'))
        self.assertTrue(not oyster.is_command('"not a command"'))
        self.assertTrue(not oyster.is_command(''))

    def test_parse(self):
        command_string = 'cat foo.txt'
        command = oyster.parse(command_string)[0]
        self.assertTrue(isinstance(command, oyster.Command))
        self.assertEqual(command.program, 'cat')
        self.assertEqual(command.arguments, ('foo.txt',))
        self.assertEqual(command.tokens, ('cat', 'foo.txt'))
        self.assertEqual(command.as_string, command_string)

        invalid_command = oyster.parse('#cat foo.txt')
        self.assertTrue(not invalid_command)

        invalid_command = oyster.parse('for i in $(seq 10); do echo $i; done')
        self.assertTrue(not invalid_command)


if __name__ == '__main__':
    unittest.main()
