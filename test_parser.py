import mwparserfromhell

from parser import get_events_from_article, format_wikicode

def test_formatting():
    content = "''foobar''"
    wikicode = mwparserfromhell.parse(content)
    assert format_wikicode(wikicode) == '<i>foobar</i>'


def test_formatting_link():
    content = "[http://google.com ''foobar'']"
    wikicode = mwparserfromhell.parse(content)
    assert format_wikicode(wikicode) == '<a href="http://google.com"><i>foobar</i></a>'


def test_get_events_from_article():
    data = """{{Current events header|2017|05|5}}

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

    results = get_events_from_article(data)

    assert len(results) == 7

    # Assert each one individually to make this a little easier.
    assert results[0] == [u'[[Syrian Civil War]]']
    assert results[1] == []
    assert results[2] == [u' Russia, Iran  and Turkey reach an agreement, effective this midnight, to establish four "safe zones" in Syria over which all military aircraft, including Turkish, Russian, and American aircraft, will be barred from flying.  ', u'[http://www.reuters.com/article/us-mideast-crisis-syria-agreement-idUSKBN1811KJ (Reuters)]', u'[http://www.foxnews.com/world/2017/05/05/report-russia-says-syria-safe-zones-will-be-shut-for-us-warplanes.html (Fox News)]']
    assert results[3] == []
    assert results[4] == [u'The United Nations welcomed the long discussed safe zones, although they have been rejected by Syrian rebels and the ', u'[[Democratic Union Party (Syria)|Kurdish PYD]]', u'. ', u'[http://www.reuters.com/article/us-mideast-crisis-safezones-opposition-idUSKBN1801TF (Reuters)]', u'[http://www.foxnews.com/world/2017/05/05/report-russia-says-syria-safe-zones-will-be-shut-for-us-warplanes.html (Fox News)]' ,'[http://www.reuters.com/article/us-mideast-crisis-syria-pyd-idUSKBN1811PZ (Reuters)]']
    assert results[5] == [u'[[Afghan National Police|Afghan border police]]', u' and the ', u'[[Pakistan Armed Forces|Pakistani military]]', u' clash at a ', u'[[Durand Line|border crossing]]', u' near ', u'[[Chaman]]', u', killing at least 13 people and wounding over 80 others. Both sides blame each other for the flareup in fighting. ', u'[https://www.rferl.org/a/pakistan-afghanistan-border-shooting-census-team/28469536.html (Radio Free Europe/Radio Liberty)]']
    assert results[6] == [u'[[United States Senate|United States senators]]', u'[[Ben Cardin]]', u' (', u'[[Democratic Party (United States)|D]]', u'-', u'[[Maryland|MD]]', u') and ', u'[[Marco Rubio]]', u' (', u'[[Republican Party (United States)|R]]', u'-', u'[[Florida|FL]]', u') file a bill restricting ', u'[[arms industry|arms sales]]', u' to the ', u'[[Philippine National Police]]', u' over its ', u'[[Philippine Drug War|drug war]]', u'. ', u'[http://www.rappler.com/nation/168973-us-bill-restrictions-weapons-exports-pnp (Rappler)]']
