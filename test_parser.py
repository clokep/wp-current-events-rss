import mwparserfromhell

from parser import WikicodeToHtmlComposer

def test_formatting():
    content = "''foobar''"
    wikicode = mwparserfromhell.parse(content)
    composer = WikicodeToHtmlComposer()
    assert composer.compose(wikicode) == '<i>foobar</i>'


def test_formatting_link():
    content = "[http://google.com ''foobar'']"
    wikicode = mwparserfromhell.parse(content)
    composer = WikicodeToHtmlComposer()
    assert composer.compose(wikicode) == '<a href="http://google.com"><i>foobar</i></a>'


def test_internal_link():
    content = "[[Foobar]]"
    wikicode = mwparserfromhell.parse(content)
    composer = WikicodeToHtmlComposer()
    assert composer.compose(wikicode) == '<a href="https://en.wikipedia.org/wiki/Foobar">Foobar</a>'


def test_internal_link_title():
    content = "[[Foobar|fuzzbar]]"
    wikicode = mwparserfromhell.parse(content)
    composer = WikicodeToHtmlComposer()
    assert composer.compose(wikicode) == '<a href="https://en.wikipedia.org/wiki/Foobar">fuzzbar</a>'


def test_list():
    content = "* Foobar"
    wikicode = mwparserfromhell.parse(content)
    composer = WikicodeToHtmlComposer()
    assert composer.compose(wikicode) == '<li> Foobar'
