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
rofi-zotero.py
```

Configuration
-------------

The configuration options are currently quite limited.

You can change the format of the Rofi list using the `FORMAT` variables in
`rofi-zotero.py`.


Differences from other projects
-------------------------------

There are two similar projects with the same name:

- [rolph-recto/rofi-zotero]
- [MatthijsMars/rofi-zotero] (fork of the former)

Here are some notable difference from the abovementioned projects:

- The list of attachments is sorted.
- It is also possible to open attached links
  (for example, created using [ZotFile]).
- It is easier to change the format of the list of attachment.
- An error message is shown if an attachment is not found.


[MatthijsMars/rofi-zotero]: https://github.com/MatthijsMars/rofi-zotero
[rolph-recto/rofi-zotero]: https://github.com/rolph-recto/rofi-zotero
[ZotFile]: http://zotfile.com/


Credits
-------

Some parts of the code are based on [MatthijsMars/rofi-zotero] and the original
project [rolph-recto/rofi-zotero].
