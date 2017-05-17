import mwparserfromhell

import pytest

from parser import WikicodeToHtmlComposer

def test_formatting():
    """Test that simple formatting works."""
    content = "''foobar''"
    wikicode = mwparserfromhell.parse(content)
    composer = WikicodeToHtmlComposer()
    assert composer.compose(wikicode) == '<i>foobar</i>'


def test_formatting_link():
    """Ensure an external link is rendered properly with a title that's formatted."""
    content = "[http://google.com ''foobar'']"
    wikicode = mwparserfromhell.parse(content)
    composer = WikicodeToHtmlComposer()
    assert composer.compose(wikicode) == '<a href="http://google.com"><i>foobar</i></a>'


def test_internal_link():
    """Ensure an internal link is rendered properly."""
    content = "[[Foobar]]"
    wikicode = mwparserfromhell.parse(content)
    composer = WikicodeToHtmlComposer()
    assert composer.compose(wikicode) == '<a href="https://en.wikipedia.org/wiki/Foobar">Foobar</a>'


def test_internal_link_title():
    """Ensure an internal link with a title is rendered properly."""
    content = "[[Foobar|fuzzbar]]"
    wikicode = mwparserfromhell.parse(content)
    composer = WikicodeToHtmlComposer()
    assert composer.compose(wikicode) == '<a href="https://en.wikipedia.org/wiki/Foobar">fuzzbar</a>'


def test_list():
    """Ensure a list is rendered properly."""
    content = "* Foobar"
    wikicode = mwparserfromhell.parse(content)
    composer = WikicodeToHtmlComposer()
    assert composer.compose(wikicode) == '<ul><li> Foobar</li></ul>'


def test_subitem_list():
    """Ensure a list with another list inside of it is rendered properly."""
    content = "* Foobar\n** Subitem"
    wikicode = mwparserfromhell.parse(content)
    composer = WikicodeToHtmlComposer()
    assert composer.compose(wikicode) == '<ul><li> Foobar\n</li><ul><li> Subitem</li></ul></ul>'


def test_subitem_list_complex():
    """Ensure a list with another list inside of it is rendered properly."""
    content = "* Foobar\n** Subitem\n* Barfoo"
    wikicode = mwparserfromhell.parse(content)
    composer = WikicodeToHtmlComposer()
    result = composer.compose(wikicode)
    print(result)
    assert result == '<ul><li> Foobar\n</li><ul><li> Subitem\n</li></ul><li> Barfoo</li></ul>'


@pytest.mark.skip
def test_foobar():
    content = """{{Current events header|2017|05|5}}

<!-- All news items below this line -->
;Armed conflicts and attacks
*[[Syrian Civil War]]
** Russia, Iran  and Turkey reach an agreement, effective this midnight, to establish four "safe zones" in Syria over which all military aircraft, including Turkish, Russian, and American aircraft, will be barred from flying.  [http://www.reuters.com/article/us-mideast-crisis-syria-agreement-idUSKBN1811KJ (Reuters)] [http://www.foxnews.com/world/2017/05/05/report-russia-says-syria-safe-zones-will-be-shut-for-us-warplanes.html (Fox News)]
**The United Nations welcomed the long discussed safe zones, although they have been rejected by Syrian rebels and the [[Democratic Union Party (Syria)|Kurdish PYD]]. [http://www.reuters.com/article/us-mideast-crisis-safezones-opposition-idUSKBN1801TF (Reuters)] [http://www.foxnews.com/world/2017/05/05/report-russia-says-syria-safe-zones-will-be-shut-for-us-warplanes.html (Fox News)] [http://www.reuters.com/article/us-mideast-crisis-syria-pyd-idUSKBN1811PZ (Reuters)]
*[[Afghan National Police|Afghan border police]] and the [[Pakistan Armed Forces|Pakistani military]] clash at a [[Durand Line|border crossing]] near [[Chaman]], killing at least 13 people and wounding over 80 others. Both sides blame each other for the flareup in fighting. [https://www.rferl.org/a/pakistan-afghanistan-border-shooting-census-team/28469536.html (Radio Free Europe/Radio Liberty)]

;International relations
*[[United States Senate|United States senators]] [[Ben Cardin]] ([[Democratic Party (United States)|D]]-[[Maryland|MD]]) and [[Marco Rubio]] ([[Republican Party (United States)|R]]-[[Florida|FL]]) file a bill restricting [[arms industry|arms sales]] to the [[Philippine National Police]] over its [[Philippine Drug War|drug war]]. [http://www.rappler.com/nation/168973-us-bill-restrictions-weapons-exports-pnp (Rappler)]

<!-- All news items above this line -->|}
"""

    wikicode = mwparserfromhell.parse(content)

    print("======== Raw wikicode ========")
    print(wikicode)
    print("======== Parsed wikicode =======")
    print(wikicode.filter(recursive=False))

    composer = WikicodeToHtmlComposer()
    print("======= HTML =======")
    print(composer.compose(wikicode))

    1/0
