from datetime import date, datetime, timedelta
from urllib.parse import quote as url_quote

import feedgenerator

import mwparserfromhell
from mwparserfromhell.definitions import MARKUP_TO_HTML
from mwparserfromhell.nodes import Comment, ExternalLink, HTMLEntity, Tag, Template, Text, Wikilink
from mwparserfromhell.wikicode import Wikicode

import requests

# The MARKUP_TO_HTML is missing a few things...this duck punches them in.
MARKUP_TO_HTML.update({
    "''": 'i',
})


class UnknownNode(Exception):
    pass


class WikicodeToHtmlComposer(object):
    """
    Format HTML from Parsed Wikicode.

    Note that this is not currently re-usable.

    https://en.wikipedia.org/wiki/Help:Wiki_markup
    """
    def __init__(self, base_url='https://en.wikipedia.org/wiki'):
        self._base_url = base_url

        self._article_url_format = base_url + '/{}'

        # Track the currently open tags.
        self._stack = []

    def _get_url(self, title):
        """Given a page title, return a URL suitable for linking."""
        safe_title = url_quote(title.encode('utf-8'))
        return self._article_url_format.format(safe_title)

    def _close_stack(self, tag=None):
        """Close tags that are on the stack. It closes all tags until ``tag`` is found.

        If no tag to close is given the entire stack is closed.
        """
        # Close the entire stack.
        if tag is None:
            print("Closing the full stack.")
            for current_tag in reversed(self._stack):
                yield u'</{}>'.format(current_tag)
            return

        # If a tag was given, close all tags behind it (in reverse order).
        if tag not in self._stack:
            # TODO
            raise RuntimeError('Uh oh')

        while len(self._stack):
            current_tag = self._stack.pop()
            print("Removing {} from the stack.".format(current_tag))
            yield u'</{}>'.format(current_tag)

            if current_tag == tag:
                break

    def _require_parent(self, parent_tag, current_tag):
        """Ensure a particular tag is open on the stack, opens it if not."""
        try:
            child_after_parent = self._stack.index(current_tag) > self._stack.index(parent_tag)
        except ValueError:
            child_after_parent = False

        if parent_tag not in self._stack or child_after_parent:
            self._stack.append(parent_tag)
            yield u'<{}>'.format(parent_tag)

    def _compose_parts(self, obj):
        """Takes an object and returns a generator that will compose one more pieces of HTML."""
        if isinstance(obj, Wikicode):
            for node in obj.ifilter(recursive=False):
                yield from self._compose_parts(node)

        elif isinstance(obj, Tag):
            # Some tags require a parent tag to be open first, but get grouped
            # if one is already open.
            if obj.wiki_markup == '*':
                yield from self._require_parent('ul', 'li')
            elif obj.wiki_markup == '#':
                yield from self._require_parent('ol', 'li')
            elif obj.wiki_markup == ';':
                yield from self._require_parent('dl', 'dt')

            # Create an HTML tag.
            # TODO Handle attributes.
            yield u'<{}>'.format(obj.tag)

            # We just opened a tag, woot!
            self._stack.append(obj.tag)
            print("Adding {} to the stack.".format(obj.tag))

            for child in obj.__children__():
                yield from self._compose_parts(child)

            # Self closing tags don't need an end tag, this produces "broken"
            # HTML, but readers should handle it fine.
            if not obj.self_closing:
                # Close this tag and any other open tags after it.
                yield from self._close_stack(obj.tag)

        elif isinstance(obj, Wikilink):
            # Different text can be specified, or falls back to the title.
            text = obj.text or obj.title
            url = self._get_url(obj.title)
            yield u'<a href="{}">{}</a>'.format(url, self._compose_parts(text))

        elif isinstance(obj, ExternalLink):
            # Different text can be specified, or falls back to the URL.
            text = obj.title or obj.url
            yield u'<a href="{}">{}</a>'.format(obj.url, self._compose_parts(text))

        elif isinstance(obj, Comment):
            yield u'<!-- {} -->'.format(obj.contents)

        elif isinstance(obj, Text):
            yield obj.value

        elif isinstance(obj, (HTMLEntity, Template)):
            # TODO
            yield str(obj)

        elif isinstance(obj, (list, tuple)):
            # If the object is iterable, just handle each item separately.
            for node in obj:
                yield from self._compose_parts(node)

        else:
            raise UnknownNode(u'Unknown node type: {}'.format(type(obj)))

    def compose(self, obj):
        """Converts Wikicode or Node objects to HTML."""
        # TODO Add a guard that this can only be called once at a time.

        result = u''

        # Generate each part and append it to the result.
        for part in self._compose_parts(obj):
            result += part

            # Certain tags get closed when there's a line break.
            if self._stack:
                for c in reversed(part):
                    if c == '\n':
                        elements_to_close = ['li', 'ul', 'ol', 'dl', 'dt']
                        # Close an element in the stack.
                        if self._stack[-1] in elements_to_close:
                            for part in self._close_stack(self._stack[-1]):
                                result += part
                    else:
                        break

        # If any parts of the stack are still open, close them.
        for part in self._close_stack():
            result += part

        return result

def filter_templates(node):
    """Remove nodes that are only whitespace."""
    return not isinstance(node, Template)


def get_article_url(lookup_date):
    # Format the date as a string, this is formatted using the #time extension
    # to Wiki syntax:
    # https://www.mediawiki.org/wiki/Help:Extension:ParserFunctions#.23time with
    # a format of "Y F j". This is awkward because we want the day *not* zero
    # padded, but the month as a string.
    datestr = '{} {} {}'.format(lookup_date.year, lookup_date.strftime('%B'), lookup_date.day)
    return 'https://en.wikipedia.org/wiki/Portal:Current_events/' + datestr


def get_article_by_date(lookup_date):
    """
    Returns the article content for a particular day, this requests a page like
    https://en.wikipedia.org/wiki/Portal:Current_events/2017_May_5

    """
    response = requests.get(get_article_url(lookup_date), params={'action': 'raw'})

    return response.content


def get_articles():
    """
    Returns a map of dates to a list of current events on that date.

    The root of this is parsing https://en.wikipedia.org/wiki/Portal:Current_events
    The true information we're after is included via
    https://en.wikipedia.org/wiki/Portal:Current_events/Inclusion
    which then includes the past seven days.
    """
    feed = feedgenerator.Rss201rev2Feed('Wikipedia: Portal: Current events',
                                        'https://en.wikipedia.org/wiki/Portal:Current_events',
                                        'some description')

    # Start at today.
    day = date.today()

    for i in range(7):
        day -= timedelta(days=1)

        # Download the article content.
        article = get_article_by_date(day)
        # Parse the article contents.
        wikicode = mwparserfromhell.parse(article)
        nodes = wikicode.filter(recursive=False, matches=filter_templates)

        composer = WikicodeToHtmlComposer('https://en.wikipedia.org/wiki/')

        feed.add_item(title=u'Current events: {}'.format(day),
                      link=get_article_url(day),
                      description=composer.compose(nodes),
                      pubdate=datetime(*day.timetuple()[:3]))

    return feed.writeString('utf-8')


if __name__ == '__main__':
    get_articles()
