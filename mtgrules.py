from __future__ import absolute_import, division, print_function, unicode_literals
import utool as ut
import re
print, rrr, profile = ut.inject2(__name__, '[rules]')


class RuleHeuristics(object):
    """
    Defines simple heuristics to determine
    revant info about a block of rules text.

    cls = RuleHeuristics
    """
    ETB = ' enters the battlefield '
    MANASYM = ut.named_field('manasym', '{[WUBRG]}')

    @classmethod
    def _iter_blocks(cls, card):
        rule_blocks = card.rules_text.split(';')
        for block in rule_blocks:
            block = block.strip(' ')
            yield block

    @classmethod
    def _fill(cls, name=None):
        return ut.named_field(name, '.*?')

    @classmethod
    def mana_generated(cls, block, card):
        esc = re.escape
        managen_line = '{T}: Add ' + cls._fill('managen') + ' to your mana pool.'
        managen_line_regexes = [managen_line,
                                esc('(') + managen_line + esc(')')]
        mana_generated = []
        for managen_line in managen_line_regexes:
            match = re.match(managen_line, block)
            if match is not None:
                manatext = match.groupdict()['managen']
                for x in re.finditer(cls.MANASYM, manatext):
                    mana_generated += [x.groupdict()['manasym']]
                break
        return mana_generated

    @classmethod
    def is_triland(cls, block, card):
        return len(cls.mana_generated(block, card)) == 3

    @classmethod
    def is_fetchland(cls, block, card):
        return cls.get_fetched_lands(block, card) is not None

    @classmethod
    def get_fetched_lands(cls, block, card):
        fetch_regex = (
            'Search your library for an? ' +
            cls._fill('landtypes') +
            ' card and put it onto the battlefield' +
            ut.named_field('istapped', ' tapped') +
            '?')
        match = re.search(fetch_regex, block)
        if match is not None:
            groupdict = match.groupdict()
            landtypes = groupdict['landtypes'].split(' or ')
            if groupdict['istapped']:
                landtypes = ['tap-' + type_ for type_ in landtypes]
            return landtypes

    @classmethod
    def is_tapland(cls, block, card):
        return block == (card.name + cls.ETB + 'tapped.')

    @classmethod
    def is_tangoland(cls, block, card):
        return block == (
            card.name + cls.ETB +
            'tapped unless you control two or more basic lands.')

    @classmethod
    def is_painland(cls, block, card):
        pain_regex = (
            '{T}: Add ' + cls._fill() + ' to your mana pool. ' + card.name +
            ' deals 1 damage to you.'
        )
        match = re.search(pain_regex, block)
        return match is not None

    @classmethod
    def is_mana_ability(cls, effect):
        pain_regex = (
            'Add ' + cls._fill() + ' to your mana pool'
        )
        match = re.search(pain_regex, effect)
        return match is not None
