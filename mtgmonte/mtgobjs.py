# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
import six
import utool as ut
import operator as op
import numpy as np
import re
from mtgmonte import mtgrules
import copy
from mtglib.card_renderer import Card
#from six.moves import
ut.util_cache.VERBOSE_CACHE = False
print, rrr, profile = ut.inject2(__name__, '[mtgobjs]')


MANA_SYMBOLS = 'WUBRG'
PERMANENT_TYPES = {'Artifact', 'Creature', 'Enchantment', 'Land', 'Planeswalker'}
_TAPLIKE_UNICODE = ['⟳', '↷']
TAPPED = _TAPLIKE_UNICODE[-1]


#@ut.memoize
@ut.cached_func('lookup_card', appname='mtgmonte_', key_argx=[0])
def lookup_card_(cardname):
    print('Lookup cardname = %r' % (cardname,))
    from mtglib.gatherer_request import SearchRequest
    from mtglib.card_extractor import CardExtractor
    from mtglib.card_renderer import CardList

    from mtgmonte import mtgobjs
    #keys = ['block', 'cmc', 'color', 'colourize', 'exact',
    #        'exclude_other_colors', 'exclude_other_types', 'flavor', 'format',
    #        'hidesets', 'json', 'name', 'power', 'random', 'rarity',
    #        'reminder', 'rulings', 'set', 'special', 'text', 'tough', 'type']
    request = SearchRequest({'name': cardname, 'exact': True})
    cards = CardExtractor(request.url).cards
    double_sided_cards = {
        'Jace, Vryn\'s Prodigy',
    }
    assert len(cards) != 0, 'no match'
    if len(cards) == 2:
        # check if double sided.
        card = cards[0]
        if card.name in double_sided_cards:
            card.other_side = cards[1]
            cards = [card]
    cards = [card_ for card_ in cards if card_.name == cardname]
    if len(cards) != 1:
        cardlist = CardList(cards)
        cardlist.render()
        print('cards = %r' % (cards,))
        assert len(cards) == 1, 'should only be one card'
    assert len(cards) != 0, 'no match'
    card2 = mtgobjs.Card2()
    card2.__dict__.update(cards[0].__dict__)
    return card2


def lookup_card(cardname):
    from mtgmonte import mtgobjs
    card = mtgobjs.lookup_card_(cardname)
    #card = mtgmonte.lookup_card_(cardname, use_cache=False)
    card.rrr(verbose=False)
    return card


@six.add_metaclass(ut.ReloadingMetaclass)
class Deck(object):
    """
    from mtgmonte.mtgobjs import *  # NOQA
    """
    def __init__(deck, card_list):
        deck.card_list = card_list
        deck._card2_idx = {card: idx for idx, card in enumerate(deck.card_list)}
        deck._library = None
        deck.initialize()

    def _on_reload(deck):
        for card in deck.card_list:
            card.rrr(False)

    def copy(deck):
        other_deck = Deck([card.copy() for card in deck.card_list])
        other_deck._library = deck.reflect_card_list(deck._library, other_deck)
        return other_deck

    def reflect_card_list(deck, card_list, other_deck):
        # Find the indexes of the cards in this deck
        sortx = ut.dict_take(deck._card2_idx, card_list)
        # Return the appropriate list of card objects from the other deck
        other_card_list = ut.take(other_deck.card_list, sortx)
        return other_card_list

    @property
    def library(deck):
        if deck._library is None:
            return deck.card_list
        else:
            return deck._library

    def __len__(deck):
        return len(deck.library)

    def initialize(deck):
        deck._library = deck.card_list[:]

    def reset(deck, rng=None):
        deck.initialize()
        for card in deck.card_list:
            card.state = []
        deck.shuffle(rng=rng)

    def sample_hand(deck):
        deck.reset()
        return deck.draw_hand()

    def shuffle(deck, rng=None):
        if rng is None:
            rng = np.random
        rng.shuffle(deck._library)

    def draw_card(deck, num=1):
        taken = deck._library[0:num]
        deck._library = deck._library[num:]
        return taken

    def draw_hand(deck):
        hand = deck.draw_card(7)
        #rng = np.random
        #hand = rng.choice(deck.card_list, size=(7,), replace=False).tolist()
        #for card in hand:
        #    deck._library.remove(card)
        return hand


#ut.reloading_metacl
@six.add_metaclass(ut.ReloadingMetaclass)
class Card2(Card):
    """
    cd ~/code/mtgmonte

    from mtgmonte.mtgobjs import *  # NOQA

    card = lookup_card('Island')

    card = lookup_card('Mountain')
    card.printinfo()
    card = lookup_card('Evolving Wilds')
    card.printinfo()
    card = lookup_card('Battlefield Forge')
    card.printinfo()
    card = lookup_card('Flooded Strand')
    card.printinfo()
    card = lookup_card('Mystic Monastery')
    card.printinfo()
    card = lookup_card('Sunken Hollow')
    card.printinfo()

    print(card.rules_text)
    card = lookup_card('Flooded Strand')
    card.mana_source_stats()
    print(card.rules_text)
    card = lookup_card('Mystic Monastery')
    print(card.rules_text)
    card = lookup_card('Sunken Hollow')
    print(card.rules_text)

    #print('costs = %r' % (costs,))
    #print('mana_generated = %r' % (mana_generated,))
    """

    def __init__(card, *args, **kwargs):
        card.state = []
        super(Card2, card).__init__(*args, **kwargs)

    def copy(card):
        other = copy.deepcopy(card)
        return other

    def __repr__(card):
        return '<' + card.__str__() + '>'

    def __str__(card):
        if not hasattr(card, 'state'):
            card.state = []
        if card.mana_cost:
            body = card.name + ' (' + card.mana_cost + ')'
        else:
            body = card.name
        if len(card.state) > 0:
            state_nice =  {
                # 'tapped': TAPPED
            }
            body += ' ' + ut.repr2([state_nice.get(s, s) for s in card.state])
        return body

    def __getstate__(card):
        return card.__dict__

    def __setstate__(card, dict_):
        card.__dict__.update(dict_)

    @property
    def basic_infodict(card):
        _basic_keys = [
            'name',  'mana_cost', 'color_indicator',  'types',  'subtypes',
            'power', 'toughness', 'loyalty',
            #'rules_text'
        ]
        basic_keys = filter(lambda key: card.__dict__[key], _basic_keys)
        basic_infodict = ut.dict_subset(card.__dict__, basic_keys)
        return basic_infodict

    @property
    def infodict(card):
        basic_infodict = card.basic_infodict
        infodict = basic_infodict.copy()
        heuristic_types, heuristic_subtypes = card.get_heuristic_info()
        infodict['heuristic_types'] = heuristic_types
        return infodict

    @property
    def heuristic_infodict(card):
        infodict = ut.dict_subset(card.__dict__, ['name', 'mana_cost'])
        heuristic_types, heuristic_subtypes = card.get_heuristic_info()
        infodict['heuristic_types'] = heuristic_types
        return infodict

    @property
    def manacost_colored(card):
        return [x for x in card.mana_cost if x in MANA_SYMBOLS]

    @property
    def manacost_uncolored(card):
        if not hasattr(card, 'manacost'):
            return 0
        patern = '[' + MANA_SYMBOLS + ']'
        cost = int('0' + re.sub(patern, card.mana_cost, ''))
        return cost

    @property
    def cmc(card):
        if len(card.mana_cost) > 0:
            try:
                return int(card.converted_mana_cost)
            except AttributeError:
                return len(card.mana_cost)
        else:
            return 0

    @property
    def heuristic_types(card):
        return card.get_heuristic_info()[0]

    def basic_infostr(card):
        basic_infostr_ = ut.repr3(card.basic_infodict, nl=1)
        return basic_infostr_

    def infostr(card):
        infostr_ = ut.repr3(card.infodict, nl=1)
        return infostr_

    def printinfo(card):
        print(card.infostr())

    def get_heuristic_info(card):
        """
        hueristic category label (fetch-land, removal, creature)
        """
        heuristic_types = []
        heuristic_subtypes = []
        if ut.is_subset(['Basic', 'Land'], card.types):
            heuristic_types += ['basic']

        RuleHeuristics = mtgrules.RuleHeuristics

        for block in RuleHeuristics._iter_blocks(card):
            if RuleHeuristics.is_tapland(block, card):
                heuristic_types += ['tap']

            if RuleHeuristics.is_tangoland(block, card):
                heuristic_types += ['tango']

            if RuleHeuristics.is_triland(block, card):
                heuristic_types += ['tri']

            if RuleHeuristics.is_painland(block, card):
                heuristic_types += ['pain']

            if RuleHeuristics.is_fetchland(block, card):
                heuristic_types += ['fetch']

        return heuristic_types, heuristic_subtypes

    def get_abilities(card):
        """
        card = lookup_card('Battlefield Forge')
        card.printinfo()
        """
        ability_list = []
        RuleHeuristics = mtgrules.RuleHeuristics
        for block in RuleHeuristics._iter_blocks(card):
            ability = {'type': None}

            if ':' in block:
                costs_, effects_ = block.split(':')
                costs = [_.strip() for _ in costs_.split(',')]
                effects = [_.strip() for _ in effects_.split('.')]

                def tolkenize_effect(effect):
                    if effect.startswith('Then '):
                        effect = effect.replace('Then ', '')
                    return effect.strip()

                # Tolkenize effect language
                effects = [tolkenize_effect(effect) for effect in effects]

                # Remove empty sections
                effects = [effect for effect in effects if effect]

                if any([RuleHeuristics.is_mana_ability(_) for _ in effects]):
                    type_ = 'mana'
                else:
                    type_ = 'activated'

                ability['type'] = type_
                ability['costs'] = costs
                ability['effects'] = effects
            else:
                ability['type'] = 'PARSE ERROR'
                ability['text'] = block
            ability_list.append(ability)
        return ability_list
        #print(ut.repr3(ability_list))

    def get_etb_modifiers(card, player=None):
        if 'tap' in card.heuristic_types:
            return ['tapped']
        if 'tango' in card.heuristic_types:
            if player is None:
                return ['tapped']
            else:
                basic_lands_under_control = [
                    c for c in player.bfield
                    if ut.is_superset(c.types, ['Basic', 'Land'])
                ]
                if len(basic_lands_under_control) >= 2:
                    return []
                else:
                    return ['tapped']
        else:
            return []

    def get_nonmana_abilities(card):
        pass

    def get_goldfish_value(card):
        # TODO: consider game state
        return 1

    def is_tapped(card):
        return 'tapped' in card.state

    def is_permanent(card):
        if len(PERMANENT_TYPES.intersection(card.types)) > 0:
            return True
        else:
            return False

    def mana_potential(card, deck=None):
        if card.is_tapped():
            # todo: just check feasiblity of ability
            mana_potential = []
        else:
            list_ = card.mana_source_stats(deck)[0]
            mana_potential = [x.strip('{}') for x in list_]
        return mana_potential

    @property
    def ability_blocks(card):
        # TODO: filter out non-"activated" abilities
        blocks = card.rules_text.split(';')
        return blocks

    def mana_potential2(card, deck=None, recurse=True):
        """
        cd ~/code/mtgmonte

        CommandLine:
            python -m mtgmonte.mtgobjs --exec-mana_potential2

        Example:
            >>> # ENABLE_DOCTEST
            >>> from mtgmonte import mtgobjs
            >>> deck = mtgobjs.Deck(mtgobjs.load_cards(['Tropical Island', 'Sunken Hollow', 'Island']))
            >>> cards = mtgobjs.load_cards(['Flooded Strand', 'Tundra', 'Island', 'Shivan Reef', 'Ancient Tomb'])
            >>> card = cards[-1]
            >>> result = ut.repr2([card.mana_potential2(deck) for card in cards])
            >>> print(result)
            [['B', 'U', 'G'], ['W', 'U'], ['U'], ['C', 'U', 'R'], ['CC']]
        """
        from mtgmonte import mtgrules
        mana_generated = [mtgrules.RuleHeuristics.mana_generated(block, card)
                          for block in card.ability_blocks]
        if mtgrules.RuleHeuristics.is_fetchland(block, card):
            from mtgmonte import mtgrules
            fetch_targets = [
                mtgrules.get_fetch_search_targets(block, card, deck)
                for block in card.ability_blocks]
            if recurse:
                mana_generated = [
                    list(set(ut.flatten([t.mana_potential2(deck) for t in ts]))) for ts in fetch_targets
                ]
            else:
                mana_generated = fetch_targets

        # TODO: use more than one iteration
        mana_potential2 = ut.flatten([
            [x.strip('{}') if isinstance(x, six.string_types) else x for x in xs]
            for xs in mana_generated])
        return mana_potential2

    def mana_source_stats(card, deck=None):
        rule_blocks = card.rules_text.split(';')

        costs = []
        mana_generated = []

        if 'Land' in card.types:
            if 'Basic' in card.types:
                mana_generated = ['{' + card.rules_text + '}']
                costs = []
            else:
                for block in rule_blocks:
                    block = block.strip(' ')
                    manasymbol = ut.named_field('manasym', '{[WUBRG]}')
                    managen_regex = ut.named_field('managen', '.*?')
                    landtypes_regex = ut.named_field('landtypes', '.*?')
                    managen_line_regexes = [
                        '{T}: Add ' + managen_regex + ' to your mana pool.',
                        re.escape('({T}: Add ') + managen_regex + re.escape(' to your mana pool.)'),
                    ]
                    for managen_line in managen_line_regexes:
                        match = re.match(managen_line, block)
                        if match is not None:
                            break
                    if match is not None:
                        manatext = match.groupdict()['managen']
                        for x in re.finditer(manasymbol, manatext):
                            mana_generated += [x.groupdict()['manasym']]
                    # Is tapland
                    ETB = ' enters the battlefield '
                    if card.name + ETB + 'tapped.' == block:
                        costs.append('ETB_Tapped()')
                    if card.name + ETB + 'tapped unless you control two or more basic lands.' == block:
                        costs.append('if len(controlled_basics) >= 2: ETB_Tapped()')

                    # from mtgmonte import mtgrules
                    # mtgrules.get_fetch_search_targets(block, card, player)

                    # Is fetchland
                    fetch_regex = (
                        'Search your library for an? ' +
                        landtypes_regex +
                        ' card and put it onto the battlefield. Then shuffle your library.')
                    match = re.search(fetch_regex, block)
                    if match is not None:
                        valid_targets = set([])
                        for type_ in match.groupdict()['landtypes'].split(' or '):
                            if deck is None:
                                card = lookup_card(type_)
                                valid_targets.add(card)
                            else:
                                for card in deck.library:
                                    if type_ in card.subtypes:
                                        valid_targets.add(card)
                        costs = []
                        mana_generated = []
                        for card in valid_targets:
                            # marginalize mana
                            gen, cost = card.mana_source_stats()
                            mana_generated.append(gen)
                        mana_generated = list(set(ut.flatten(mana_generated)))
                    #else:
                    #    costs = []
                    #    mana_generated = []
            manastats = mana_generated, costs
        else:
            manastats = None

        return manastats


class CardGroup(object):
    def __init__(group, cards):
        #cards = player.hand
        # group = ut.DynStruct
        group.cards = cards
        group.sortself()

    def reloadcards(group):
        for c in group.cards:
            c.rrr(False)

    def sortself(group):
        val_list = [(c.cmc, c.name) for c in group.cards]
        group.cards = ut.sortedby(group.cards, val_list)

    @property
    def infohist(group):
        cardnames = [six.text_type(c) for c in group.cards]
        types_ = [c.types[-1] for c in group.cards]
        hgroup = dict(ut.hierarchical_group_items(cardnames, [types_, cardnames]))
        infohist1 = ut.map_dict_vals(ut.dict_hist, hgroup).items()
        # Grouped infohist
        infohist = [(key, [(vals[n], n) for n in vals]) for key, vals in infohist1]
        # list_ = [six.text_type(c) for c in group.cards]
        # dict_ = ut.dict_hist(list_)
        # ulist_ = ut.unique_keep_order(list_)
        # infohist = [(dict_[item], item) for item in ulist_]
        # ut.embed()
        return infohist

    def __repr__(group):
        repr_ = ut.repr3(group.infohist, nl=1)
        print(repr_)
        return repr_

    def get_attrs(group, attr):
        attrs = [getattr(c, attr) for c in group.cards]
        return attrs

    def get_where(group, attr, cmp_, target):
        if isinstance(cmp_, six.string_types):
            cmp_ = {
                '==': op.eq,
                '<': op.lt, '<=': op.le,
                '>': op.gt, '>=': op.ge,
            }[cmp_]
            #.get(cmp_, cmp_)
        attrs = group.get_attrs(attr)
        flags = [cmp_(val, target) for val in attrs]
        return ut.compress(group.cards, flags)


def load_cards(cardname_list):
    card_list = [
        lookup_card(cardname)
        for cardname in ut.ProgIter(cardname_list, 'Loading Cards', adjust=True)
    ]
    return card_list


def load_list(decklist_text, mydiff):
    lines = decklist_text.split('\n')
    line_regex = ut.named_field('num', r'\d+') + ' ' + ut.named_field('cardname', r'.*')
    line_re = re.compile(line_regex)

    def parse_line(line):
        match = line_re.match(line)
        groupdict_ = match.groupdict()
        return [groupdict_['cardname']] * int(groupdict_['num'])

    cardname_list = ut.flatten([
        parse_line(line)
        #[line[2:]] * int(line[0])
        for line in lines
        if (
            len(line) > 0 and not line.startswith('SB') and
            not line.startswith('#')
        )
    ])

    card_list = load_cards(cardname_list)

    #card_list = list(map(upgrade_card, card_list))
    deck = Deck(card_list)
    print('len(deck) = %r' % (len(deck),))

    # APPLY DIFF
    if False:
        print('Apply diff')
        new_cardlist = deck.card_list[:]
        for cardname in mydiff.split('\n'):
            if len(cardname) == 0:
                continue
            sign = cardname[0]
            num = cardname[1]
            cardname = cardname[3:]
            if sign == '+':
                for _ in range(int(num)):
                    new_cardlist.append(lookup_card(cardname))
            elif sign == '-':
                for _ in range(int(num)):
                    card_ = None
                    for card__ in new_cardlist:
                        if card__.name == cardname:
                            card_ = card__
                            break
                    if card_ is None:
                        assert False, 'cannot remove nonexistant'
                    new_cardlist.remove(card_)
        deck = Deck(new_cardlist)
    return deck


if __name__ == '__main__':
    r"""
    CommandLine:
        python -m mtgmonte.mtgobjs
        python -m mtgmonte.mtgobjs --allexamples
    """
    import multiprocessing
    multiprocessing.freeze_support()  # for win32
    import utool as ut  # NOQA
    ut.doctest_funcs()
