"""Text a stranger wrote, put inside a tag of a prompt: a video's description, its title, the
words said in it. It must not be able to close the tag it sits in and speak as tarjim.

Until 2026-11-14 the closing tag was deleted from the text, once. Deleting can make what it
deletes: "</kn</known>own>" is left as "</known>" (found by the review of the commit that told
the listener a link's description). So nothing is looked for and nothing deleted: every angle
bracket becomes a quotation mark that no tag is written with, and no tag of any name, spaced or
nested in any way, is left to form.
"""
ANGLES = str.maketrans({"<": "\u2039", ">": "\u203a"})


def inert(text: str) -> str:
    """The text with no angle bracket in it."""
    return text.translate(ANGLES)
