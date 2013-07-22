Oyster
=======

Oyster is a Python module for parsing shell commands. Unlike awesome modules such as docopt, optparse & argpare the
primary intention of Oyster is not to parse the arguments passed to a single application - although it is capable of that too.
The main objective is rather to parse any given shell command whether it be a chain of multiple commands or not.

Let's see a demo:

```python
import oyster

chain = oyster.parse('pip search -vvv --timeout=5 flask | grep session | less')
print len(chain)  # ==> 3

pip, grep, less = chain

print pip.has_option('--timeout')  # ==> True
print pip.get_option_values('--timeout')  # ==> ['5']
print pip.get_option_count('-v')  # ==> 3
print pip.arguments  # ==> ('search', '--timeout=5', 'flask')

print grep  # ==> 'grep session'
print less  # ==> 'less'

chain.remove('less')
print chain  # ==> 'pip search -vvv --timeout=5 flask | grep session'

chain += 'date -u'
print chain  # ==> 'pip search -vvv --timeout=5 flask | grep session; date -u'
utc_date = chain[chain.index('date -u')]
print utc_date  # ==> 'date -u'
print utc_date.get_option_values('-u')  # ==> [True]

```

## Gotchas to bring up

- get_option_values always returns a list
- curl -v http://localhost:8000 (-v will have the URL as value)
