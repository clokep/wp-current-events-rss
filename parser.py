from datetime import date
import urllib

import feedgenerator

import mwparserfromhell
from mwparserfromhell.nodes import Comment, ExternalLink, Tag, Text, Wikilink

import requests


ARTICLE_URL_FORMAT = 'https://en.wikipedia.org/wiki/{}'

def wiki_url(title):
    return ARTICLE_URL_FORMAT.format(urllib.quote(title.encode('utf-8')))


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
                end = i - 1
                break

    # Ignore nodes outside of the start/end.
    nodes = nodes[start:end]

    # Phase 2: Parse to each section.
    items = []
    i = 0
    while i < len(nodes):
        node = nodes[i]

        # TODO Parse definition lists into tags, e.g. node.wiki_markup == ';'.
        # TODO Handle sub-items.

        # Bulleted lists are used to start each news item.
        if isinstance(node, Tag) and node.wiki_markup == '*':
            # Start collecting nodes.
            current_item = []

            while i < len(nodes):
                # Get the next node.
                i += 1
                temp_node = nodes[i]

                # If it isn't a text then back-up and break.
                if isinstance(temp_node, (Text, Wikilink, ExternalLink)):
                    current_item.append(temp_node)
                else:
                    i -= 1
                    items.append(current_item)
                    break

        i += 1

    return items


def write_feed(lookup_date, events):
    """
    Convert events (a list of list of nodes) to a feed.

    """
    feed = feedgenerator.Rss201rev2Feed('Some title', 'some link', 'some description')

    for event in events:
        # Generate a title as a plaintext version.
        title = u''

        # The link is the first external source.
        link = None

        # The description is HTML.
        description = u''

        for node in event:
            if isinstance(node, Wikilink):
                text = unicode(node.text or node.title)
                title += text
                description += u'<a href="{}">{}</a>'.format(wiki_url(text), text)
            elif isinstance(node, ExternalLink):
                # External links (sources) don't go in the title.
                text = unicode(node.title or node.url)
                description += u'<a href="{}">{}</a>'.format(node.url, text)
            else:
                title += node.value
                description += node.value

        feed.add_item(title, link, description)

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
