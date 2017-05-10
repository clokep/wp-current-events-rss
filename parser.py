from datetime import date, datetime
import urllib

import feedgenerator

import mwparserfromhell
from mwparserfromhell.definitions import get_html_tag, MARKUP_TO_HTML
from mwparserfromhell.nodes import Comment, ExternalLink, Tag, Text, Wikilink
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
        # Get the HTML tag for this node.
        tag = get_html_tag(obj.wiki_markup)

        # Convert all the children to HTML.
        inner = ''.join(map(format_wikicode, obj.__children__()))

        # Create an HTML tag.
        # TODO Handle attributes.
        return '<{}>{}</{}>'.format(tag, inner, tag)

    elif isinstance(obj, Wikilink):
        # Different text can be specified, or falls back to the title.
        text = obj.text or obj.title
        return u'<a href="{}">{}</a>'.format(wiki_url(obj.title), format_wikicode(text))

    elif isinstance(obj, ExternalLink):
        # Different text can be specified, or falls back to the URL.
        text = obj.title or obj.url
        return u'<a href="{}">{}</a>'.format(obj.url, format_wikicode(text))

    else:
        return unicode(obj)


def filter_empty(node):
    """Remove nodes that are only whitespace."""
    return bool(node.strip())


def get_article_by_date(lookup_date):
    """
    Returns the article content for a particular day, this requests a page like
    https://en.wikipedia.org/wiki/Portal:Current_events/2017_May_5

    """
    # Format the date as a string, this is formatted using the #time extension
    # to Wiki syntax:
    # https://www.mediawiki.org/wiki/Help:Extension:ParserFunctions#.23time with
    # a format of "Y F j". This is awkward because we want the day *not* zero
    # padded, but the month as a string.
    datestr = '{} {} {}'.format(lookup_date.year, lookup_date.strftime('%B'), lookup_date.day)

    response = requests.get(
        'https://en.wikipedia.org/wiki/Portal:Current_events/' + datestr,
        params={'action': 'raw'})

    return response.content


def get_events_from_article(article_content):
    """
    Returns a list of events for an article, this parsers a page like
    https://en.wikipedia.org/wiki/Portal:Current_events/2017_May_5

    Each event is list of nodes.

    """
    # Parse the raw text into an AST.
    wikicode = mwparserfromhell.parse(article_content)

    # A list of nodes with empty (whitespace only) nodes removed.
    nodes = wikicode.filter(recursive=False, matches=filter_empty)

    # Phase 1: Find the start and end comments.
    # Default to the first and last nodes.
    start = 0
    end = len(nodes) - 1
    for i, node in enumerate(nodes):
        # Once we find the start comment, break out.
        if isinstance(node, Comment):
            if 'All news items below this line' in node:
                start = i + 1
            elif 'All news items above this line' in node:
                end = i
                break

    # Ignore nodes outside of the start/end.
    nodes = nodes[start:end]

    # Phase 2: Parse to each section.
    items = []
    current_item = []
    i = 0
    while i < len(nodes):
        node = nodes[i]

        # TODO Parse definition lists into tags, e.g. node.wiki_markup == ';'.
        # TODO Handle sub-items.

        # Bulleted lists are used to start each news item.
        if isinstance(node, Tag) and node.wiki_markup == '*':
            # Don't look at the same node again.
            i += 1
            while i < len(nodes):
                temp_node = nodes[i]

                # Start collecting nodes. If it isn't a text-ish node then
                # back-up in the list and break.
                if isinstance(temp_node, (Text, Wikilink, ExternalLink)):
                    current_item.append(temp_node)
                else:
                    i -= 1
                    items.append(current_item)
                    current_item = []
                    break

                i += 1

        i += 1

    if current_item:
        items.append(current_item)

    return items


def write_feed(lookup_date, events):
    """
    Convert events (a list of list of nodes) to a feed.

    """
    feed = feedgenerator.Rss201rev2Feed('Wikipedia: Portal: Current events',
                                        'https://en.wikipedia.org/wiki/Portal:Current_events',
                                        'some description')

    for event in events:
        # Generate a title as a plaintext version.
        title = u''

        # The link is the first external source.
        link = None

        # The description is HTML.
        description = u''

        for node in event:
            if isinstance(node, Wikilink):
                # Add a HTML stripped version of the node to the title.
                title += unicode(node.text or node.title)

            elif isinstance(node, ExternalLink):
                # External links (sources) don't go in the title.

                # The first link gets set.
                if not link:
                    link = node.url

            else:
                # HTML stripped version.
                title += unicode(node)

            description += format_wikicode(node)

        feed.add_item(title, link, description, pubdate=datetime(*lookup_date.timetuple()[:3]))

    return feed.writeString('utf-8')


def get_events_by_date(lookup_date):
    """
    Returns a list of events for a particular day, this parsers a page like
    https://en.wikipedia.org/wiki/Portal:Current_events/2017_May_5

    """
    # Get the article's text.
    article = get_article_by_date(lookup_date)
    return get_events_from_article(article)


def get_events():
    """
    Returns a map of dates to a list of current events on that date.

    The root of this is parsing https://en.wikipedia.org/wiki/Portal:Current_events
    The true information we're after is included via
    https://en.wikipedia.org/wiki/Portal:Current_events/Inclusion
    which then includes the past seven days.
    """
    yesterday = date(2017, 5, 8)
    
    events = get_events_by_date(yesterday)
    return write_feed(yesterday, events)

if __name__ == '__main__':
    get_events()
