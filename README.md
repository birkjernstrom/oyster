Oyster: Get 'em pearls
=======

Oyster is a Python module for parsing shell commands. Unlike awesome modules such as docopt, optparse & argpare the
primary intention of Oyster is not to parse the arguments passed to a single application - although it is capable of that too.
The main objective is rather to parse any given shell command whether it be a chain of multiple commands or not.

  - [Demo](#demo)
  - [Features](#features)
    - [Chains](#chains)
    - [Commands](#commands)
    - [Redirects](#redirects)
  - [Caveats](#caveats)
  - [Documentation](#documentation)
  - [License](#license)

## Demo

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

## Features

####Chains:
```python
import oyster

chain = oyster.parse('cat /var/log/system.log | grep kernel >> system_kernel.log 2>> errors.log')
cat, grep = chain
print cat  # ==> 'cat /var/log/system.log'
print grep  # ==> 'grep kernel >> system_kernel.log 2>> errors.log'

```

####Commands:
```python
import oyster

command = oyster.Command(['cat', '-n', 'foo.txt'])
print command  # ==> 'cat -n foo.txt'
print command.program  # ==> 'cat'
print command.arguments  # ==> ('-n', 'foo.txt')
print command.has_option('-n')  # ==> True
print command.get_option_values('-n')  # ==> ['foo.txt']  (See "Caveats" about this)
print command.get_option_count('-n')  # ==> 1
print command.get_options()  # ==> {'-n': ['foo.txt']}  (See "Caveats" about this)
```

####Redirects:

```python
import oyster

chain = oyster.parse('cat /var/log/system.log | grep kernel >> system_kernel.log 2>> errors.log')
print chain[0].redirects  # ==> ()
print chain[1].redirects[0]  # ==> >> system_kernel.log
print chain[1].redirects[0].source == oyster.STDOUT  # ==> True
print chain[1].redirects[0].destination == 'system_kernel.log'  # ==> True
print chain[1].redirects[0].mode  # ==> 'a'
print chain[1].redirects[1]  # ==> 2>> errors.log
print chain[1].redirects[1].is_source_stderr()  # ==> True
print chain[1].redirects[1].is_destination_stdfd()  # ==> False

```

## Caveats

  - The string passed to ``oyster.parse`` can differ from ``str(command)`` since the latter is generated using ``subprocess.list2cmdline`` which can cause different quotations.
  - ``Command(['cat', '-n', 'foo.txt']).get_option_values('-n')`` will always return a ``list`` since options can be repeated.
  - ``Command(['curl', '-v', 'http://localhost']).get_option_values('-v')`` will return ``['http://localhost']``. Whether this is true or not is up to the program executed, i.e ``curl`` in this instance.


## Documentation

The Oyster documentation is available [here](http://birknilson.github.io/oyster/documentation/).
Currently, this is a work in progress and a complete documentation will be available within a few days.

## License

Oyster is licensed under a three clause BSD License which can read in the included [LICENSE](https://github.com/birknilson/oyster/blob/master/LICENSE) file.
