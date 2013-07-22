#!/usr/bin/env python

import os

import markdown2

from solarized256 import Solarized256Style
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter


def rel(path):
    scripts_dir = os.path.dirname(__file__)
    return os.path.join(scripts_dir, path)


def read(filename):
    contents = ''
    with open(filename, 'r') as f:
        contents = f.read()
    return contents


def python_highlight(output, offset=0):
    start_needle = '```python'
    highlight_offset = output.find(start_needle, offset)
    if highlight_offset == -1:
        return (False, output)


    end_needle = '```'
    highlight_finish = output.find(end_needle,
                                   highlight_offset + len(start_needle))

    if highlight_finish == -1:
        return (False, output)

    formatter = HtmlFormatter(style=Solarized256Style)
    code = output[highlight_offset + len(start_needle):highlight_finish]
    code = highlight(code, PythonLexer(), formatter)

    highlight_finish += len(end_needle)
    highlighted = '{before}{code}{after}'.format(
        before=output[:highlight_offset],
        code=code,
        after=output[highlight_finish:],
    )
    highlight_offset += len(start_needle)
    return (highlight_finish, highlighted)


def syntax_highlight(output):
    highlight_offset = 0
    while True:
        highlight_offset, output = python_highlight(output,
                                                    offset=highlight_offset)
        if not highlight_offset:
            break

    return output


def inject_markdown(template, md):
    return template.replace('{{{MARKDOWN}}}', md)


def main():
    readme = read(rel('../README.md'))
    readme = syntax_highlight(readme)
    readme = markdown2.markdown(readme)

    template = read(rel('data/website_template.html'))
    output = inject_markdown(template, readme)
    with open(rel('../website/index.html'), 'w') as f:
        f.write(output)


if __name__ == '__main__':
    main()
