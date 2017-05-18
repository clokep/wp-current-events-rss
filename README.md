## Wikipedia Current Events to RSS

[![CircleCI](https://circleci.com/gh/clokep/wp-current-events-rss.svg?style=svg)](https://circleci.com/gh/clokep/wp-current-events-rss)

**wp-current-events-rss** serves the last 7 days of
[Wikipedia's Current Events](https://en.wikipedia.org/wiki/Portal:Current_events)
as an RSS feed. This is deployed at https://wp-current-events-rss.herokuapp.com/.

Information is pulled on demand on each refresh of the page (and is always
current).

### About

This project runs on Heroku. It is a Flask application that serves a single web
page (an RSS feed). It pulls data from the last 7 days of current events from
Wikipedia, e.g. a page like
https://en.wikipedia.org/wiki/Portal:Current_events/2017_May_8. The Wikicode is
parsed using [mwparserfromhell](http://mwparserfromhell.readthedocs.org/) to an
AST which is then cleaned-up slightly and converted back into HTML.
