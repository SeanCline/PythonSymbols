==========================
WinDbg symbols for CPython
==========================


.. image:: https://img.shields.io/github/last-commit/SeanCline/PythonSymbols/gh-pages.svg?label=Symbol%20Server%20Updated
    :target: https://app.travis-ci.com/github/SeanCline/PythonSymbols
    :alt: Build Status

This repository hosts the symbols for all recent Windows builds of the CPython interpreter. (Both x86 and x64.)

It stays up to date automatically by looking for new Python releases weekly and adding their symbols to the symbols store.

To use the symbols server, add the following to your symbol path:

.. code-block::

    srv*c:\symbols*http://pythonsymbols.sdcline.com/symbols
