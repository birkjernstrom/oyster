#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import unittest

test_directory = os.path.dirname(os.path.abspath(__file__))
test_directory = os.path.join(test_directory, 'src')
sys.path.insert(0, test_directory)

import sheldon

class TestCase(unittest.TestCase):
    def test_tokenize(self):
        # Only limited testing required since shlex handles the dirty work
        command = "grep -r 'foo' /some/file"
        tokens = sheldon.tokenize(command)
        self.assertTrue(isinstance(tokens, list))
        self.assertEqual(len(tokens), 4)

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

    def test_simple_command(self):
        command_str = 'cat -nb --fake=yes /foo/bar'
        command = sheldon.parse(command_str)
        self.assertTrue(command.program == 'cat')
        self.assertEqual(len(command.arguments), 3)
        self.assertTrue(command.has_option('-n'))
        self.assertTrue(command.has_option('-b'))
        self.assertEqual(command.get_option('--fake'), 'yes')
        self.assertEqual(str(command), command_str)

if __name__ == '__main__':
    unittest.main()
