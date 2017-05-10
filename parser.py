from datetime import date, datetime, timedelta
import urllib

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


ARTICLE_URL_FORMAT = 'https://en.wikipedia.org/wiki/{}'

def wiki_url(title):
    """Given a page titiel, return a URL suitable for linking."""
    return ARTICLE_URL_FORMAT.format(urllib.quote(title.encode('utf-8')))


def format_wikicode(obj):
    """Returns Unicode of a Wikicode or Node object converted to HTML."""
    if isinstance(obj, Wikicode):
        result = u''
        for node in obj.ifilter(recursive=False):
            result += format_wikicode(node)
        return result

    if isinstance(obj, Tag):
        # Convert all the children to HTML.
        inner = u''.join(map(format_wikicode, obj.__children__()))

        # Self closing tags don't need an end tag, this produces "broken" HTML,
        # but readers should handle it fine.
        if not obj.self_closing:
            template = u'<{tag}>{inner}</{closing_tag}>'
        else:
            template = u'<{tag}>{inner}'

        # Create an HTML tag.
        # TODO Handle attributes.
        return template.format(tag=obj.tag, inner=inner, closing_tag=obj.closing_tag)

    elif isinstance(obj, Wikilink):
        # Different text can be specified, or falls back to the title.
        text = obj.text or obj.title
        return u'<a href="{}">{}</a>'.format(wiki_url(obj.title), format_wikicode(text))

    elif isinstance(obj, ExternalLink):
        # Different text can be specified, or falls back to the URL.
        text = obj.title or obj.url
        return u'<a href="{}">{}</a>'.format(obj.url, format_wikicode(text))

    elif isinstance(obj, (list, tuple)):
        # If the object is iterable, just handle each item separately.
        result = u''
        for node in obj:
            result += format_wikicode(node)
        return result
    else:
        return unicode(obj)


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

        feed.add_item(title=u'Current events: {}'.format(day),
                      link=get_article_url(day),
                      description=format_wikicode(nodes),
                      pubdate=datetime(*day.timetuple()[:3]))

    return feed.writeString('utf-8')


if __name__ == '__main__':
    get_articles()
