rofi-zotero
===========

A simple script that uses [Rofi] to search for and open PDF/DjVu attachments
from [Zotero].

The script requires Python 3.7 or above (and Rofi, obviously).

This repository was created for personal use, and bugs are to be expected.
Make sure to keep backups of important files.


[Rofi]: https://github.com/davatorium/rofi
[Zotero]: https://www.zotero.org/


Example
-------

![rofi-zotero](https://github.com/hanschen/rofi-zotero/assets/1353015/84de0529-ce81-4509-bcfe-4310a1ce2bb8)


Usage
-----

```bash
rofi-zotero.py [-p ZOTERO_PROFILE] [--rofi-args="ROFI_ARGS"]
```

See `rofi-zotero.py --help` for a full list of options.


### Examples:

Simplest case, just run the script.

```bash
rofi-zotero.py
```

If you have multiple zotero profiles use
the `-p` argument to specify the profile name:

```bash
rofi-zotero.py -p user_01
```

To pass arguments to Rofi, use `--rofi-args`. Note when using this argument, it
is usually necessary to include an equal sign and quote, see example below.
Spaces can be included by escaping them with backslash (`\`):

```bash
rofi-zotero.py --rofi-args="-i -theme mytheme -m -1 -p prompt\ with\ space"
```

To get a list of all options, use

```bash
rofi-zotero.py --help
```


Configuration
-------------

To customize the Rofi arguments, for example to specify the theme, use the
`--rofi-args` command-line argument.

Some formatting options (how the results appear in Rofi) currently do not have
corresponding command-line arguments. Instead, you can customize these using
the `FORMAT` variables at the top of `rofi-zotero.py`.


Differences from other projects
-------------------------------

There are two similar projects with the same name:

- [rolph-recto/rofi-zotero]
- [MatthijsMars/rofi-zotero] (fork of the former)

Here are some notable difference from the abovementioned projects:

- The list of attachments is sorted.
- It is possible to open attached links
  (for example, created using [ZotFile]).
- This script can also deal with items with multiple attachments.
- It is easier to change the format of the list of attachments.
- More flexibility regarding the arguments passed to Rofi.
- Error message are shown for various situations,
  for example if an attachment is not found.


[MatthijsMars/rofi-zotero]: https://github.com/MatthijsMars/rofi-zotero
[rolph-recto/rofi-zotero]: https://github.com/rolph-recto/rofi-zotero
[ZotFile]: http://zotfile.com/


Credits
-------

Some parts of the code are based on [MatthijsMars/rofi-zotero] and the original
project [rolph-recto/rofi-zotero].
