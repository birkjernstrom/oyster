.. Oyster documentation master file, created by
   sphinx-quickstart on Mon Jul 22 02:59:19 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. automodule:: oyster

Constants
==================================
.. currentmodule:: oyster
.. autodata:: RESERVED_WORDS
.. autodata:: CONTROL_OPERATORS
.. autodata:: STDIN
.. autodata:: STDOUT
.. autodata:: STDERR
.. autodata:: STDFD_MAPPING


Chains
==================================
.. currentmodule:: oyster
.. autoclass:: Chain

.. autoinstanceattribute:: Chain.commands

.. automethod:: Chain.append
.. automethod:: Chain.insert
.. automethod:: Chain.index
.. automethod:: Chain.pop
.. automethod:: Chain.remove


Commands
==================================
.. currentmodule:: oyster
.. autoclass:: Command

.. autoinstanceattribute:: Command.program
.. autoinstanceattribute:: Command.arguments
.. autoinstanceattribute:: Command.tokens
.. autoinstanceattribute:: Command.as_string
.. autoinstanceattribute:: Command.redirects

.. automethod:: Command.get_options
.. automethod:: Command.has_option
.. automethod:: Command.get_option_values
.. automethod:: Command.get_option_count

Redirects
==================================
.. currentmodule:: oyster
.. autoclass:: Redirect

.. autoinstanceattribute:: Redirect.source
.. autoinstanceattribute:: Redirect.destination
.. autoinstanceattribute:: Redirect.mode

.. automethod:: Redirect.is_source_stdin
.. automethod:: Redirect.is_source_stdout
.. automethod:: Redirect.is_source_stderr
.. automethod:: Redirect.is_destination_stdfd
.. automethod:: Redirect.is_destination_stdin
.. automethod:: Redirect.is_destination_stdout
.. automethod:: Redirect.is_destination_stderr

Functions
==================================
.. currentmodule:: oyster
.. autofunction:: parse
.. autofunction:: is_comment
.. autofunction:: is_script
.. autofunction:: is_quoted
.. autofunction:: is_command
.. autofunction:: tokenize
.. autofunction:: split_token_by_operators
