# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
import utool as ut
import re
from itertools import combinations
#import sys
print, rrr, profile = ut.inject2(__name__, '[rules]')

# TODO: remove static class. just use the module

#INF = sys.maxint
#HAS_NUMPY = False
#if HAS_NUMPY:
#INF = np.inf
INF = 1000  # pretty much infinite


def english_number(numtext):
    try:
        return int(numtext)
    except Exception:
        lookup = {'one': 1, 'two': 2, 'three': 3, 'four': 4}  # , '∞': INF}
        return lookup[numtext]


ETB = ' enters the battlefield '
COLORLESS_SYMS = 'C'
COLOR_SYMS = 'WUBRG'
ALL_MANA_SYM = COLOR_SYMS + COLORLESS_SYMS
COLORLESS_MANASYM = ut.named_field('colorless_manasym', '{[0-9]+}')
MANASYM = ut.named_field('manasym', '({[' + ALL_MANA_SYM + ']})+')


def _fill(name=None):
    return ut.named_field(name, '.*?')


def is_ability_block(block):
    return ':' in block or (len(block) == 1 and (block in ALL_MANA_SYM))


def mana_generated(block, card, new=False, debug=False):
    r"""
    Parse the string representation of mana generated

    CommandLine:
        python -m mtgmonte.mtgrules --exec-mana_generated
        python -m mtgmonte.mtgrules --exec-mana_generated --cards "Reflecting Pool" --debug-mana

    Example:
        >>> # ENABLE_DOCTEST
        >>> from mtgmonte.mtgrules import *  # NOQA
        >>> from mtgmonte import mtgobjs
        >>> testmana_cards_ = [
        >>>     'Flooded Strand',
        >>>     'Tundra',
        >>>     'Island',
        >>>     'Shivan Reef',
        >>>     'Ancient Tomb',
        >>>     'Black Lotus',
        >>>     'Mox Lotus',
        >>>     'Mox Ruby',
        >>>     'Mox Diamond', 'Chrome Mox',
        >>>     'Elvish Mystic', 'Lion\'s Eye Diamond',
        >>>     'Grim Monolith', 'Tolarian Academy',
        >>>     'City of Brass', 'Mana Confluence',
        >>>     'Lake of the Dead', 'Snow-Covered Island',
        >>>     'Reflecting Pool',
        >>>     'Mirrorpool', 'Wastes',
        >>>     # 'Dark Ritual', (dark rit does not have ability blocks)
        >>> ]
        >>> testmana_cards = ut.get_argval('--cards', type_=list, default=testmana_cards_)
        >>> DEBUG = ut.get_argflag('--debug-mana')
        >>> print('testmana_cards = %r' % (testmana_cards,))
        >>> cards = mtgobjs.load_cards(testmana_cards)
        >>> for card in cards:
        >>>     print('\n-----')
        >>>     print(card)
        >>>     if DEBUG:
        >>>         card.printinfo()
        >>>     for block in card.ability_blocks:
        >>>         #print('block = %r' % (block,))
        >>>         print(mana_generated(block, card, debug=DEBUG))

    Ignore:
        >>> card = cards[1]
        >>> card = cards[-1]
        >>> block = card.ability_blocks[0]
        >>> result = mana_generated(block, card)
        >>> print(result)
    """
    if debug:
        print('block = %s' % (block,))
    #esc = re.escape
    if block in MANASYM:
        mana_generated = ['{' + block + '}']
    else:
        # Most mana generaters look like this
        managen_line1 = 'Add ' + _fill('managen') + ' to your mana pool ?' + _fill('modifier') + '$'
        # Some (like reflecting pool look like this)
        managen_line2 = 'Add to your mana pool ' + _fill('managen') + ' mana ?' + _fill('modifier') + '$'

        managen_line_regexes = [managen_line1, managen_line2]
        #,
        #print('block = %r' % (block,))
        #esc('(') + managen_line + esc(')')]
        any_matched = False
        mana_generated = []

        for count, managen_line in enumerate(managen_line_regexes):
            match = re.search(managen_line, block)
            if match is None:
                if debug:
                    print('Did not match managen_line %d' % (count + 1))
            elif match is not None:
                any_matched = True
                manatext = match.groupdict()['managen']
                modifier = match.groupdict()['modifier']

                if debug:
                    print(' * Matched managen_line=%r (%d)' % (managen_line, count + 1))
                    print(' * modifier = %r' % (modifier,))
                    print(' * manatext = %r' % (manatext,))

                for x in re.finditer(MANASYM, manatext):
                    z = x.groupdict()
                    mana_generated += [z['manasym']]

                for x in re.finditer(_fill('num') + ' mana of any one color', manatext):
                    numtxt = x.groupdict()['num']
                    num = english_number(numtxt)
                    mana_generated += ['{' + (c * num) + '}' for c in COLOR_SYMS]

                for x in re.finditer(_fill('num') + ' mana of any color', manatext):
                    numtxt = x.groupdict()['num']
                    num = english_number(numtxt)
                    mana_generated += ['{' + ''.join(comb) + '}' for comb in combinations(COLOR_SYMS, num)]

                for x in re.finditer(_fill('num') + ' mana of any of the ' +
                                     _fill('refcard') + ' colors', manatext):
                    print('Refer card hack')
                    num = english_number(x.groupdict()['num'])
                    refcard = x.groupdict()['refcard']
                    # chrome mox hack
                    if refcard == 'exiled card\'s':
                        # TODO: Refers to part of the game state
                        # Assume any color for now
                        mana_generated += ['{' + ('*' * num) + '}']  # for c in COLOR_SYMS]
                    #print('num = %r' % (num,))
                    #print('refcard = %r' % (refcard,))
                    #mana_generated += ['{' + (c * num) + '}' for c in COLOR_SYMS]

                if manatext == 'one':
                    num = 1

                # Deal with colorless mana
                for x in re.finditer(COLORLESS_MANASYM, manatext):
                    num = english_number(x.groupdict()['colorless_manasym'].strip('{}'))
                    mana_generated += ['{' + ('C' * num) + '}']

                # Mox lotus hack
                if manatext.strip('{}') == '∞':
                    num = INF
                    mana_generated += [{'C': '∞'}]

                # Tolarian acadamy hack
                if modifier == 'for each artifact you control.':
                    #print('modifier = %r' % (modifier,))
                    # TODO: Refers to part of the game state
                    mana_generated = [{c.strip('{}'): '*'} for c in mana_generated]
                    print('Refer card hack')
                # Reflecting pool hack
                if modifier == 'of any type that a land you control could produce.':
                    mana_generated += ['{' + ('*' * num) + '}']  # for c in COLOR_SYMS]
                    pass

        if not any_matched and len(mana_generated) == 0:
            #mana_generated = []
            mana_generated = None
    if mana_generated is not None:
        from mtgmonte import mtgobjs
        # sources = None
        sources = [card]
        options = [mtgobjs.ManaSet(manas, sources) for manas in mana_generated]
        mana_generated = mtgobjs.ManaOption(options)
    return mana_generated


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

    @classmethod
    def _iter_blocks(cls, card):
        rule_blocks = card.rules_text.split(';')
        for block in rule_blocks:
            block = block.strip(' ')
            yield block

    @classmethod
    def _fill(cls, name=None):
        return _fill(name)

    @classmethod
    def mana_generated(cls, block, card):
        return mana_generated(block, card)

    @classmethod
    def is_triland(cls, block, card):
        mana = mana_generated(block, card)
        return mana is not None and len(mana) == 3

    @classmethod
    def is_fetchland(cls, block, card):
        return is_fetchland(block, card)

    @classmethod
    def get_fetched_lands(cls, block, card):
        return get_fetched_lands(block, card)

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


def get_fetched_lands(block, card):
    fetch_regex = (
        'Search your library for an? ' +
        _fill('landtypes') +
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


def is_fetchland(block, card):
    return get_fetched_lands(block, card) is not None


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
