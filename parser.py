from datetime import date, datetime, timedelta
from urllib.parse import quote as url_quote

import feedgenerator

import mwparserfromhell
from mwparserfromhell.definitions import MARKUP_TO_HTML
from mwparserfromhell.nodes import ExternalLink, Tag, Template, Wikilink
from mwparserfromhell.wikicode import Wikicode

import requests

# The MARKUP_TO_HTML is missing a few things...this duck punches them in.
MARKUP_TO_HTML.update({
    "''": 'i',
})


class WikicodeToHtmlComposer(object):
    """
    Format HTML from Parsed Wikicode.

    Note that this is not currently re-usable.

    https://en.wikipedia.org/wiki/Help:Wiki_markup
    """
    def __init__(self, base_url='https://en.wikipedia.org/wiki'):
        self._base_url = base_url

        self._article_url_format = base_url + '/{}'

    def _get_url(self, title):
        """Given a page title, return a URL suitable for linking."""
        safe_title = url_quote(title.encode('utf-8'))
        return self._article_url_format.format(safe_title)

    def _compose_parts(self, obj):
        """Takes an object and returns a generator that will compose one more pieces of HTML."""
        if isinstance(obj, Wikicode):
            for node in obj.ifilter(recursive=False):
                yield from self._compose_parts(node)

        elif isinstance(obj, Tag):
            # Create an HTML tag.
            # TODO Handle attributes.
            yield u'<{}>'.format(obj.tag)

            for child in obj.__children__():
                yield from self._compose_parts(child)

            # Self closing tags don't need an end tag, this produces "broken"
            # HTML, but readers should handle it fine.
            if not obj.self_closing:
                yield u'</{}>'.format(obj.closing_tag)

        elif isinstance(obj, Wikilink):
            # Different text can be specified, or falls back to the title.
            text = obj.text or obj.title
            url = self._get_url(obj.title)
            yield u'<a href="{}">{}</a>'.format(url, self.compose(text))

        elif isinstance(obj, ExternalLink):
            # Different text can be specified, or falls back to the URL.
            text = obj.title or obj.url
            yield u'<a href="{}">{}</a>'.format(obj.url, self.compose(text))

        elif isinstance(obj, (list, tuple)):
            # If the object is iterable, just handle each item separately.
            for node in obj:
                yield from self._compose_parts(self.compose(node))

        else:
             # TODO Raise?
            yield str(obj)

    def compose(self, obj):
        """Converts Wikicode or Node objects to HTML."""
        return ''.join(self._compose_parts(obj))


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

    for i in xrange(7):
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
