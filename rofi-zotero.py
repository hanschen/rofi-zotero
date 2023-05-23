#!/usr/bin/env python
"""Use Rofi to search and open attachments from Zotero.

Requirements:
- Python 3.7 or newer
- Rofi

Author: Hans Chen (contact@hanschen.org)

"""

import argparse
import os
import shutil
import shlex
import sqlite3
import subprocess
import sys
import tempfile

from pathlib import Path


__version__ = "0.1"


DEFAULT_ZOTERO_PATH = Path.home() / "Zotero"
DEFAULT_ZOTERO_BASE_DIR = Path.home() / "papers"
DEFAULT_ROFI_ARGS = "-i"  # case insensitive
DEFAULT_VIEWER = "xdg-open %u"
DEFAULT_PROMPT_PAPER = "paper"
DEFAULT_PROMPT_ATTACHMENT = "attachment"

FORMAT_ITEM = "{author} ({year}) - {title}"
FORMAT_ITEM_WITHOUT_YEAR = "{author} - {title}"
FORMAT_ITEM_WITHOUT_AUTHOR = "Unknown ({year}) - {title}"
FORMAT_ITEM_WITHOUT_AUTHOR_AND_YEAR = "Unknown - {title}"

FORMAT_AUTHORS_SINGLE = "{author1}"
FORMAT_AUTHORS_TWO = "{author1} and {author2}"
FORMAT_AUTHORS_MULTIPLE = "{author1} et al."

FORMAT_PATH_MAXLEN = 80
FORMAT_PATH_FULLPATH = False
FORMAT_PATH_ENDING_FRACTION = 0.5

# Zotero directories and files
_ZOTERO_STORAGE_DIR = "storage"
_ZOTERO_SQLITE_FILE = "zotero.sqlite"

# SQL queries for internal use
_QUERY_AUTHORS = """
    SELECT items.itemID,
            creators.Lastname
    FROM    ((creators
              JOIN itemCreators
                ON creators.creatorID = itemCreators.creatorID) AS t1
             JOIN items
               ON t1.itemID = items.itemID)
"""

_QUERY_TITLES = """
    SELECT parentInfo.itemID,
           parentItemDataValues.value,
           attachmentInfo.key
    FROM   itemAttachments
           INNER JOIN items AS attachmentInfo
                   ON attachmentInfo.itemID = itemAttachments.itemID
           INNER JOIN itemData AS attachmentItemData
                   ON attachmentItemData.itemID = attachmentInfo.itemID
           INNER JOIN itemDataValues AS attachmentItemDataValues
                   ON attachmentItemData.valueID =
                      attachmentItemDataValues.valueID
           INNER JOIN items AS parentInfo
                   ON itemAttachments.parentItemID = parentInfo.itemID
           INNER JOIN itemData AS parentItemData
                   ON parentItemData.itemID = parentInfo.itemID
           INNER JOIN itemDataValues AS parentItemDataValues
                   ON parentItemDataValues.valueID = parentItemData.valueID
    WHERE  attachmentItemData.fieldID = 1
           AND parentItemData.fieldID = 1
           AND ( itemAttachments.contentType LIKE '%pdf%'
                 OR itemAttachments.contentType LIKE '%djvu%' )
"""

_QUERY_DATES = """
    SELECT parentInfo.itemID,
           parentItemDataValues.value
    FROM   itemAttachments
           INNER JOIN items AS attachmentInfo
                   ON attachmentInfo.itemID = itemAttachments.itemID
           INNER JOIN itemData AS attachmentItemData
                   ON attachmentItemData.itemID = attachmentInfo.itemID
           INNER JOIN itemDataValues AS attachmentItemDataValues
                   ON attachmentItemData.valueID =
                      attachmentItemDataValues.valueID
           INNER JOIN items AS parentInfo
                   ON itemAttachments.parentItemID = parentInfo.itemID
           INNER JOIN itemData AS parentItemData
                   ON parentItemData.itemID = parentInfo.itemID
           INNER JOIN itemDataValues AS parentItemDataValues
                   ON parentItemDataValues.valueID = parentItemData.valueID
    WHERE parentItemData.fieldID=6
"""

_QUERY_PATHS = """
    SELECT parentInfo.itemID,
           path
    FROM   itemAttachments
           INNER JOIN items AS attachmentInfo
                   ON attachmentInfo.itemID = itemAttachments.itemID
           INNER JOIN itemData AS attachmentItemData
                   ON attachmentItemData.itemID = attachmentInfo.itemID
           INNER JOIN itemDataValues AS attachmentItemDataValues
                   ON attachmentItemData.valueID =
                      attachmentItemDataValues.valueID
           INNER JOIN items AS parentInfo
                   ON itemAttachments.parentItemID = parentInfo.itemID
           INNER JOIN itemData AS parentItemData
                   ON parentItemData.itemID = parentInfo.itemID
           INNER JOIN itemDataValues AS parentItemDataValues
                   ON parentItemDataValues.valueID = parentItemData.valueID
    WHERE  attachmentItemData.fieldID = 1
           AND parentItemData.fieldID = 1
           AND ( itemAttachments.contentType LIKE '%pdf%'
                 OR itemAttachments.contentType LIKE '%djvu%' )
"""


def format_authors(author_list):
    """Format author string depending on the number of authors.

    Parameters
    ----------
    author_list : list
        A list of all authors.

    Returns
    -------
    str
        String of formatted author list.

    """
    if len(author_list) == 1:
        author_string = FORMAT_AUTHORS_SINGLE.format(author1=author_list[0])
    elif len(author_list) == 2:
        author_string = FORMAT_AUTHORS_TWO.format(author1=author_list[0],
                                                  author2=author_list[1])
    else:
        author_string = FORMAT_AUTHORS_MULTIPLE.format(author1=author_list[0])

    return author_string


def format_path(path, maxlen=80, fullpath=False, ending_fraction=0.5):
    """Format path to shorten it.

    Parameters
    ----------
    path : pathlib.Path
        Path to format.
    maxlen : int, optional
        Maximum length of formatted path string.
    fullpath : bool, optional
        Set to True to return full path rather than just the filename.
    ending_fraction : float, optional
        Fraction of string length to use for the ending of the path.
        Default: 0.5.

    Returns
    -------
    str
        Formatted (shortened) path.

    """
    if not fullpath:
        path_str = path.name
    else:
        path_str = str(path)

    if len(path_str) <= maxlen:
        return path_str

    char_end = round(maxlen * ending_fraction) - 1
    char_start = maxlen - char_end - 1

    formatted_path = path_str[:char_start] + "…" + path_str[-char_end:]
    return formatted_path


def format_item(title, author=None, year=None):
    """Format item string depending on if author and year information are
    available.

    Parameters
    ----------
    title : str
        Title of item.
    author : str
        Author information for item.
    year : str
        Publishing year for item.

    Returns
    -------
    str
        String representation of time.

    """
    if author and year:
        item_string = FORMAT_ITEM.format(title=title, author=author, year=year)
    elif author:
        item_string = FORMAT_ITEM_WITHOUT_YEAR.format(title=title,
                                                      author=author)
    elif year:
        item_string = FORMAT_ITEM_WITHOUT_AUTHOR.format(title=title, year=year)
    else:
        item_string = FORMAT_ITEM_WITHOUT_AUTHOR_AND_YEAR.format(title=title)

    return item_string


def get_item_info(zotero_sqlite_file, query):
    """Get item information from Zotero.

    Parameters
    ----------
    zotero_sqlite_file : str
        Path to Zotero database.
    query : str
        SQL query.

    Returns
    -------
    list
        List of items return from the SQL query.

    """
    conn = sqlite3.connect(zotero_sqlite_file)
    items = list(conn.execute(query))
    conn.close()
    return items


def open_file(app, file_path):
    """Attempt to open ``file_path`` using ``app``.

    Parameters
    ----------
    app : str
        Application to open file. Should contain '%u' for where the file path
        would appear in the command. If '%u' is not provided, it is assumed
        that the file path is the last argument to the command.
    file_path : str
        Path to file to open.

    """
    app_and_args = [arg if arg != "%u" else file_path for arg in app.split()]
    if "%u" not in app:
        app_and_args.append(file_path)
    subprocess.run(app_and_args)


def show_error(error_msg, rofi_args=None):
    """Show ``error_msg`` as an error message in Rofi and stderr."""
    if rofi_args is None:
        rofi_args = []
    print(error_msg, file=sys.stderr)
    subprocess.run(["rofi", "-e", error_msg] + rofi_args)


def parse_args():
    description = "Open Zotero attachments with Rofi"
    parser = argparse.ArgumentParser(description=description)

    default_viewer_without_percent = DEFAULT_VIEWER.replace("%", "%%")

    parser.add_argument('-v', '--version', action='version',
                        version=f"%(prog)s {__version__}")
    parser.add_argument('-p', '--zotero-path', type=Path,
                        default=DEFAULT_ZOTERO_PATH,
                        help=(f'Path to Zotero data directory. '
                              f'Default: "{DEFAULT_ZOTERO_PATH}"'))
    parser.add_argument('-b', '--zotero-base-dir', type=Path,
                        default=DEFAULT_ZOTERO_BASE_DIR,
                        help=(f'Base directory for relative paths in Zotero. '
                              f'Default: "{DEFAULT_ZOTERO_BASE_DIR}"'))
    parser.add_argument('-l', '--list', action='store_true', default=False,
                        help=('Print out list of results instead of passing '
                              'it to Rofi'))
    parser.add_argument('--rofi-args', type=str,
                        default=DEFAULT_ROFI_ARGS,
                        help=(f'Arguments to Rofi, usually given as: '
                              f'--rofi-args="-i -t theme '
                              f'-p title\\ with\\ space". '
                              f'Default: "{DEFAULT_ROFI_ARGS}"'))
    parser.add_argument('--viewer', type=str,
                        default=DEFAULT_VIEWER,
                        help=(f'Application to open attachments, with "%%u" '
                              f'to indicate where the path should go. '
                              f'Default: "{default_viewer_without_percent}"'))
    parser.add_argument('--prompt-paper', type=str,
                        default=DEFAULT_PROMPT_PAPER,
                        help=(f'Prompt title when searching through papers. '
                              f'Default: "{DEFAULT_PROMPT_PAPER}"'))
    parser.add_argument('--prompt-attachment', type=str,
                        default=DEFAULT_PROMPT_ATTACHMENT,
                        help=(f'Prompt title when searching through '
                              f'attachments. '
                              f'Default: "{DEFAULT_PROMPT_ATTACHMENT}"'))

    return parser.parse_args()


def main(zotero_path=DEFAULT_ZOTERO_PATH,
         zotero_base_dir=DEFAULT_ZOTERO_BASE_DIR,
         list=False,
         viewer=DEFAULT_VIEWER,
         rofi_args=DEFAULT_ROFI_ARGS,
         prompt_paper=DEFAULT_PROMPT_PAPER,
         prompt_attachment=DEFAULT_PROMPT_ATTACHMENT):
    """Run main program.

    Parameters
    ----------
    zotero_path : str or pathlib.Path, optional
        Path to Zotero data directory. Default: "$HOME/Zotero"
    zotero_base_dir : str or pathlib.Path, optional
        Base directory for relative paths stored in Zotero (see Preferences ->
        Advanced -> Files and Folders -> Base directory in Zotero).
        Default: "$HOME/papers"
    list : bool, optional
        Set to True to print out list of results instead of passing it to Rofi.
        Default: False.
    viewer : str
        Application to open attachments. Use '%u' to specify the path to the
        file to open. Default: "xdg-open %u"
    rofi_args : str
        Arguments to pass to Rofi. Default: "-i"
    prompt_paper: str
        Prompt title when searching through Zotero items. Default: "paper"
    prompt_attachment: str
        Prompt title when searching through attachments for a specific item.
        Default: "attachment"

    """
    rofi_args = shlex.split(rofi_args)
    zotero_path = Path(zotero_path)
    zotero_base_dir = Path(zotero_base_dir)

    # Create a temporary copy of the database to avoid issues with locking
    tmp_dir = Path(tempfile.gettempdir())
    database_copy = tmp_dir / _ZOTERO_SQLITE_FILE
    shutil.copy2(zotero_path / _ZOTERO_SQLITE_FILE, database_copy)

    all_authors = get_item_info(database_copy, _QUERY_AUTHORS)
    all_titles = get_item_info(database_copy, _QUERY_TITLES)
    all_dates = get_item_info(database_copy, _QUERY_DATES)
    all_paths = get_item_info(database_copy, _QUERY_PATHS)

    os.remove(database_copy)

    id = all_authors[0][0]
    author_list = []
    authors = {}
    for author_id, author in all_authors:
        if author_id != id:
            authors[id] = format_authors(author_list)
            author_list = []
            id = author_id

        author_list.append(author)

    titles = {}
    keys = {}
    for title_id, title, key in all_titles:
        if title_id not in titles:
            titles[title_id] = title
            keys[title_id] = key

    years = {}
    for date_id, date in all_dates:
        if date_id not in years:
            years[date_id] = date.split("-")[0]

    paths = {}
    for path_id, path in all_paths:
        if path is None:
            continue

        if path_id in paths and str(paths[path_id]) == path:
            continue

        if path.startswith("attachments:"):
            path = path.replace("attachments:", "", 1)
            path = zotero_base_dir / path
        elif path.startswith("storage:"):
            path = path.replace("storage:", "", 1)
            path = zotero_path / _ZOTERO_STORAGE_DIR / keys[path_id] / path
        else:
            path = Path(path)

        if path_id not in paths:
            paths[path_id] = []
        paths[path_id].append(path)

    item_list_with_ids = []
    for item_id, title in titles.items():
        author = authors.get(item_id)
        year = years.get(item_id)
        item_string = format_item(title=title, author=author, year=year)
        item_list_with_ids.append((item_string, item_id))

    item_list_with_ids.sort()
    item_list = [item for item, _ in item_list_with_ids]
    items_input = "\n".join(item_list)

    if list:
        print(items_input)
        return

    # note: rofi seems to prefer the first -p argument, so if -p is given in
    # rofi_args, the latter -p argument should be ignored
    rofi_command = (["rofi", "-dmenu", "-format", "i"] + rofi_args +
                    ["-p", prompt_paper])
    rofi = subprocess.run(rofi_command, capture_output=True, text=True,
                          input=items_input)

    selected_index = rofi.stdout.strip()
    if not selected_index:
        return

    item_id = item_list_with_ids[int(selected_index)][1]
    files_to_open = paths[item_id]
    files_to_open.sort()

    if len(files_to_open) == 1:
        file_to_open = files_to_open[0]
    else:
        format_opts = {
            'maxlen': FORMAT_PATH_MAXLEN,
            'fullpath': FORMAT_PATH_FULLPATH,
            'ending_fraction': FORMAT_PATH_ENDING_FRACTION,
        }
        files = [format_path(p, **format_opts) for p in files_to_open]
        files_input = "\n".join(files)

        rofi_command = (["rofi", "-dmenu", "-format", "i"] + rofi_args +
                        ["-p", prompt_attachment])
        rofi = subprocess.run(rofi_command, capture_output=True, text=True,
                              input=files_input)
        selected_index = rofi.stdout.strip()
        if not selected_index:
            return

        file_to_open = files_to_open[int(selected_index)]

    if file_to_open.exists():
        open_file(viewer, file_to_open)
    else:
        show_error(f"Could not find file: {file_to_open}", rofi_args)


if __name__ == "__main__":
    args = parse_args()
    main(**vars(args))
