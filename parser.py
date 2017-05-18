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

        self._wanted_lists = []

        # Track the currently open tags.
        self._stack = []
        # The result of calling this.
        self._parts = []

    def _get_url(self, title):
        """Given a page title, return a URL suitable for linking."""
        safe_title = url_quote(title.encode('utf-8'))
        return self._article_url_format.format(safe_title)

    def _close_stack(self, tag=None, raise_on_missing=True):
        """Close tags that are on the stack. It closes all tags until ``tag`` is found.

        If no tag to close is given the entire stack is closed.
        """
        # Close the entire stack.
        if tag is None:
            for current_tag in reversed(self._stack):
                self._parts.append(u'</{}>'.format(current_tag))
            return

        # If a tag was given, close all tags behind it (in reverse order).
        if tag not in self._stack:
            # TODO
            if raise_on_missing:
                raise RuntimeError('Uh oh')
            else:
                return

        while len(self._stack):
            current_tag = self._stack.pop()
            self._parts.append(u'</{}>'.format(current_tag))

            if current_tag == tag:
                break

    def _add_part(self, part):
        """Append a part, closing any parts of the stack that should be closed here."""
        if self._wanted_lists:
            stack_lists = [node for node in self._stack if node in ['ul', 'ol', 'dl']]

            # Remove the prefixed part of the lists that match.
            i = 0
            shortest = min([len(stack_lists), len(self._wanted_lists)])
            for i in range(shortest):
                if stack_lists[i] != self._wanted_lists[i]:
                    break
            else:
                i = shortest

            # Now close anything left in stack_lists.
            for node in reversed(stack_lists[i:]):
                self._close_stack(node)

            # Open anything in wanted_lists.
            for node in self._wanted_lists[i:]:
                self._stack.append(node)
                self._parts.append(u'<{}>'.format(node))

            # Finally, open the list item.
            if self._wanted_lists[-1] == 'dl':
                item_tag = 'dt'
            else:
                item_tag = 'li'
            self._stack.append(item_tag)
            self._parts.append(u'<{}>'.format(item_tag))

            # Reset the list.
            self._wanted_lists = []

        self._parts.append(part)

        # Certain tags get closed when there's a line break.
        if self._stack:
            for c in reversed(part):
                if c == '\n':
                    elements_to_close = ['li', 'ul', 'ol', 'dl', 'dt']
                    # Close an element in the stack.
                    if self._stack[-1] in elements_to_close:
                        self._close_stack(self._stack[-1])
                else:
                    break

    def _compose_parts(self, obj):
        """Takes an object and returns a generator that will compose one more pieces of HTML."""
        if isinstance(obj, Wikicode):
            for node in obj.ifilter(recursive=False):
                self._compose_parts(node)

        elif isinstance(obj, Tag):
            # Some tags require a parent tag to be open first, but get grouped
            # if one is already open.
            if obj.wiki_markup == '*':
                self._wanted_lists.append('ul')
                # Don't allow a ul inside of a dl.
                self._close_stack('dl', raise_on_missing=False)
            elif obj.wiki_markup == '#':
                self._wanted_lists.append('ol')
                # Don't allow a ul inside of a dl.
                self._close_stack('dl', raise_on_missing=False)
            elif obj.wiki_markup == ';':
                self._wanted_lists.append('dl')
                # Don't allow dl instead ol or ul.
                self._close_stack('ol', raise_on_missing=False)
                self._close_stack('ul', raise_on_missing=False)

            else:
                # Create an HTML tag.
                # TODO Handle attributes.
                self._add_part(u'<{}>'.format(obj.tag))
                self._stack.append(obj.tag)

            for child in obj.__children__():
                self._compose_parts(child)

            # Self closing tags don't need an end tag, this produces "broken"
            # HTML, but readers should handle it fine.
            if not obj.self_closing:
                # Close this tag and any other open tags after it.
                self._close_stack(obj.tag)

        elif isinstance(obj, Wikilink):
            # Different text can be specified, or falls back to the title.
            text = obj.text or obj.title
            url = self._get_url(obj.title)
            self._add_part(u'<a href="{}">'.format(url))
            self._compose_parts(text)
            self._add_part(u'</a>')

        elif isinstance(obj, ExternalLink):
            # Different text can be specified, or falls back to the URL.
            text = obj.title or obj.url
            self._add_part(u'<a href="{}">'.format(obj.url))
            self._compose_parts(text)
            self._add_part(u'</a>')

        elif isinstance(obj, Comment):
            self._add_part(u'<!-- {} -->'.format(obj.contents))

        elif isinstance(obj, Text):
            self._add_part(obj.value)

        elif isinstance(obj, (HTMLEntity, Template)):
            # TODO
            self._add_part(str(obj))

        elif isinstance(obj, (list, tuple)):
            # If the object is iterable, just handle each item separately.
            for node in obj:
                self._compose_parts(node)

        else:
            raise UnknownNode(u'Unknown node type: {}'.format(type(obj)))

    def compose(self, obj):
        """Converts Wikicode or Node objects to HTML."""
        # TODO Add a guard that this can only be called once at a time.

        self._compose_parts(obj)

        # If any parts of the stack are still open, close them.
        self._close_stack()

        return u''.join(self._parts)


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

        # Remove all nodes before / after the start / end comments.
        start = 0
        end = len(nodes) - 1
        for i, node in enumerate(nodes):
            if isinstance(node, Comment):
                if 'All news items below this line' in node:
                    start = i + 1
                elif 'All news items above this line' in node:
                    end = i
                    break

        # Ignore nodes outside of the start/end.
        nodes = nodes[start:end]

        composer = WikicodeToHtmlComposer()

        feed.add_item(title=u'Current events: {}'.format(day),
                      link=get_article_url(day),
                      description=composer.compose(nodes),
                      pubdate=datetime(*day.timetuple()[:3]))

    return feed.writeString('utf-8')


if __name__ == '__main__':
    get_articles()
