from __future__ import absolute_import, division, print_function, unicode_literals
import utool as ut
import re
print, rrr, profile = ut.inject2(__name__, '[rules]')

# TODO: remove static class. just use the module


class RuleHeuristics(object):
    """
    Defines simple heuristics to determine
    revant info about a block of rules text.

    cls = RuleHeuristics
    """
    ETB = ' enters the battlefield '
    COLOR_SYMS = 'WUBRG'
    COLORLESS_SYMS = 'C'
    MANASYM = ut.named_field('manasym', '{[' + COLOR_SYMS + COLORLESS_SYMS + ']}')
    COLORLESS_MANASYM = ut.named_field('colorless_manasym', '{[0-9]+}')

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
        """
        from mtgmonte import mtgrules
        from mtgmonte.mtgrules import *  # NOQA
        cls = mtgrules.RuleHeuristics

        CommandLine:
            python -m mtgmonte.mtgrules --exec-mana_generated --show

        Example:
            >>> # DISABLE_DOCTEST
            >>> from mtgmonte.mtgrules import *  # NOQA
            >>> from mtgmonte import mtgobjs
            >>> cls = RuleHeuristics
            >>> cards = mtgobjs.load_cards(['Flooded Strand', 'Tundra', 'Island', 'Shivan Reef', 'Ancient Tomb'])
            >>> card = cards[1]
            >>> block = card.ability_blocks[0]
            >>> result = cls.mana_generated(block, card)
            >>> print(result)
        """
        #esc = re.escape
        if block in cls.MANASYM:
            return ['{' + block + '}']
        managen_line = '{T}: Add ' + cls._fill('managen') + ' to your mana pool.'
        managen_line_regexes = [managen_line]
        #,
        #esc('(') + managen_line + esc(')')]
        mana_generated = []
        for managen_line in managen_line_regexes:
            match = re.search(managen_line, block)
            if match is not None:
                manatext = match.groupdict()['managen']
                for x in re.finditer(cls.MANASYM, manatext):
                    mana_generated += [x.groupdict()['manasym']]
                # Deal with colorless mana
                for x in re.finditer(cls.COLORLESS_MANASYM, manatext):
                    num = int(x.groupdict()['colorless_manasym'].strip('{}'))
                    mana_generated += ['{' + ('C' * num) + '}']
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
        valid_types = None
        if match is not None:
            groupdict = match.groupdict()
            landtypes = groupdict['landtypes'].split(' or ')
            valid_types = [
                [x.lower() for x in type_.split(' ')]
                for type_ in landtypes
            ]

            #landtypes = groupdict['landtypes'].split(' or ')
            #if groupdict['istapped']:
            #    landtypes = ['tap-' + type_ for type_ in landtypes]
        return valid_types

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


def get_fetch_search_targets(effect, card, deck=None):
    from mtgmonte import mtgobjs
    valid_types = RuleHeuristics.get_fetched_lands(effect, card)
    targets = []
    for type_ in valid_types:
        if deck is None:
            # Infer normal sort of thing out of deck context
            card = mtgobjs.lookup_card(type_)
            targets.add(card)
        else:
            for card in deck.library:
                alltypes = card.subtypes + card.types
                alltypes = [x.lower() for x in alltypes]
                if ut.is_subset(type_, alltypes):
                    targets += [card]
    return targets


if __name__ == '__main__':
    r"""
    CommandLine:
        python -m mtgmonte.mtgrules
        python -m mtgmonte.mtgrules --allexamples
    """
    import multiprocessing
    multiprocessing.freeze_support()  # for win32
    import utool as ut  # NOQA
    ut.doctest_funcs()
