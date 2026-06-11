import html
import re


def plaintext_to_html(text: str):
    """
    Convert plaintext to HTML, also handling newlines and whitespace.
    """
    return (
        html.escape(text)
        .replace("\n", "<br>")
        .replace("\t", "&nbsp;" * 4)
        .replace("  ", "&nbsp;&nbsp;")
    )


def html_to_plaintext(text: str):
    """
    Convert HTML to plaintext, stripping tags and converting entities.
    """
    text = re.sub(r"<br>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p>", "\n\n", text, flags=re.IGNORECASE)
    unescaped_text = html.unescape(text)
    clean_text = re.sub("<[^<]+?>", "", unescaped_text)
    return clean_text
