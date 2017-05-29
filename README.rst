==========================
WinDbg symbols for CPython
==========================

This repository hosts the symbols for all recent Windows builds of the CPython interpreter. (Both x86 and x64.)

It stays up to date automatically by looking for new Python releases daily and adding their symbols to the symbols store.

To use the symbols server, add the following to your symbol path:

.. code-block::

    srv*c:\symbols*http://pythonsymbols.sdcline.com/symbols
