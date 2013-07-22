#!/usr/bin/env python

import os
import markdown2


def rel(path):
    scripts_dir = os.path.dirname(__file__)
    return os.path.join(scripts_dir, path)


def read(filename):
    contents = ''
    with open(filename, 'r') as f:
        contents = f.read()
    return contents


def inject_markdown(template, md):
    md = markdown2.markdown(md)
    return template.replace('{{{MARKDOWN}}}', md)


def main():
    readme = read(rel('../README.md'))
    template = read(rel('data/website_template.html'))
    output = inject_markdown(template, readme)
    with open(rel('../website/index.html'), 'w') as f:
        f.write(output)


if __name__ == '__main__':
    main()
