"""
cd ~/code/mtgmonte

            if False:
                for opname, opfunc in op.__dict__.items():
                    if opfunc.__doc__ is not None:
                        match = re.search('Same as a *(?P<op>.*?) *b.', opfunc.__doc__)
                        if match:
                            print(match.groupdict())
                            #print(opfunc)
                            print(opfunc.__doc__)
                            print('----')
"""
from __future__ import absolute_import, division, print_function, unicode_literals
import six
import utool as ut
import operator as op
import numpy as np
import re
import mtgrules
from mtglib.card_renderer import Card
#from six.moves import
ut.util_cache.VERBOSE_CACHE = False


def testdata_deck():
    jeskai_black = ut.codeblock(
        '''
        4 Jace, Vryn's Prodigy
        2 Dispel
        4 Mantis Rider
        4 Crackling Doom
        2 Dig Through Time
        2 Fiery Impulse
        2 Soulfire Grand Master
        3 Kolaghan's Command
        3 Ojutai's Command
        3 Tasigur, the Golden Fang
        1 Utter End
        2 Wild Slash
        1 Dragonmaster Outcast
        1 Sarkhan, the Dragonspeaker
        1 Island
        1 Plains
        2 Mountain
        1 Swamp
        1 Smoldering Marsh
        1 Sunken Hollow
        2 Prairie Stream
        1 Nomad Outpost
        4 Mystic Monastery
        4 Flooded Strand
        4 Polluted Delta
        4 Bloodstained Mire
        SB: 2 Radiant Flames
        SB: 1 Felidar Cub
        SB: 1 Negate
        SB: 2 Arashin Cleric
        SB: 2 Duress
        SB: 2 Exert Influence
        SB: 1 Dragonmaster Outcast
        SB: 1 Virulent Plague
        SB: 1 Mastery of the Unseen
        SB: 2 Roast
        ''')

    mydiff = ut.codeblock(
        '''
        +1 Plains
        +1 Sunken Hollow
        +1 Smoldering Marsh
        +1 Evolving Wilds
        +1 Battlefield Forge
        -4 Mystic Monastery
        -1 Nomad Outpost
        ''')

    decklist_text = jeskai_black
    return decklist_text, mydiff


#@ut.memoize
@ut.cached_func('lookup_card', appname='mtgmonte', key_argx=[0])
def lookup_card_(cardname):
    print('Lookup cardname = %r' % (cardname,))
    from mtglib.gatherer_request import SearchRequest
    from mtglib.card_extractor import CardExtractor
    from mtglib.card_renderer import CardList

    import mtgmonte
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
    card2 = mtgmonte.Card2()
    card2.__dict__.update(cards[0].__dict__)
    return card2


def lookup_card(cardname):
    import mtgmonte
    card = mtgmonte.lookup_card_(cardname)
    #card = mtgmonte.lookup_card_(cardname, use_cache=False)
    card.rrr(verbose=False)
    return card


class DecisionNode(object):
    def __init__(self):
        self.options = []
        self.costs = []
        pass

    def marginalize(self):
        pass


#ut.reloading_metacl
@six.add_metaclass(ut.ReloadingMetaclass)
class Card2(Card):
    """
    cd ~/code/mtgmonte

    from mtgmonte import *  # NOQA

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
        super(Card2, card).__init(*args, **kwargs)
        card.state = []

    def __repr__(card):
        return '<' + card.__str__() + '>'

    def __str__(card):
        if card.mana_cost:
            body = card.name + ' (' + card.mana_cost + ')'
        else:
            body = card.name
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
        basic_infodict = card.basic_infodict
        infodict = ut.dict_subset(basic_infodict, ['name', 'mana_cost'])
        heuristic_types, heuristic_subtypes = card.get_heuristic_info()
        infodict['heuristic_types'] = heuristic_types
        return infodict

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
        print(ut.repr3(ability_list))

    def get_nonmana_abilities():
        pass

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


@six.add_metaclass(ut.ReloadingMetaclass)
class Deck(object):
    def __init__(deck, card_list):
        deck.card_list = card_list
        deck._library = None
        deck.initialize()

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

    def reset(deck):
        deck.initialize()
        deck.shuffle()

    def sample_hand(deck):
        deck.reset()
        return deck.draw_hand()

    def shuffle(deck):
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
        list_ = [six.text_type(c) for c in group.cards]
        dict_ = ut.dict_hist(list_)
        ulist_ = ut.unique_keep_order(list_)
        infohist = [(dict_[item], item) for item in ulist_]
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


@six.add_metaclass(ut.ReloadingMetaclass)
class Player(object):
    """
    An agent
    player = Player()
    """
    def __init__(player, deck):
        player.deck = deck
        player.hand = []
        player.bfield = []
        player.graveyard = []
        player.exiled = []

    def untap_step(player):
        max_land_drops = 1
        player.land_drops_left = max_land_drops

    def draw_step(player):
        card = player.deck.draw_card()
        player.hand.append(card)

    def initial_draw(player):
        player.hand.extend(player.deck.draw_hand())

    def reset(player):
        player.deck.reset()
        player.hand = []
        player.bfield = []
        player.graveyard = []
        player.exiled = []

    def infodict(player):
        infodict = {
            'library_size': len(player.deck),
            'hand_size': len(player.hand),
            'bfield_size': len(player.bfield),
            'graveyard_size': len(player.graveyard),
            'exiled_size': len(player.exiled),
        }
        return infodict

    def print_state(player):
        print(ut.repr3(player.infodict2(), nl=2))

    def infodict2(player):
        infodict = {
            'library_size': len(player.deck),
            'hand_size': len(player.hand),
            'bfield_size': len(player.bfield),
            'graveyard_size': len(player.graveyard),
            'exiled_size': len(player.exiled),
            'hand': CardGroup(player.hand).infohist,
            'bfield': CardGroup(player.bfield).infohist,
        }
        return infodict


def goldfish(deck):

    player = Player(deck)
    player.reset()
    player.rrr()
    #print(ut.repr2(player.infodict()))
    #CardGroup(player.hand)
    #group = CardGroup(deck.card_list)
    #group = CardGroup(player.hand)

    print('Starting Goldfish')
    turn = 0

    def get_resources():
        resources = {}
        resources['land_drops_left'] = player.land_drops_left
        #group = CardGroup(player.bfield)
        untapped_lands = [
            c for c in player.bfield
            if ut.is_superset(c.types, ['Land']) and 'tapped' not in c.state]
        mana_potential = [c.mana_source_stats() for c in untapped_lands]
        resources['mana_potential'] = mana_potential

    def play_land():
        land_in_hand = [
            c for c in player.hand
            if ut.is_superset(c.types, ['Land'])]

        if len(land_in_hand) > 0:

            def get_land_value(land, turn):
                if turn == 0:
                    if 'tap' in land.heuristic_types:
                        return 2
                    else:
                        return 1

            value_list = [get_land_value(land, turn) for land in land_in_hand]
            idx = ut.list_argmax(value_list)
            land = land_in_hand[idx]
            # Get land with maximum play value
            player.hand.remove(land)
            player.bfield.append(land)

    def main_phase_play():
        player.print_state()
        group = CardGroup(player.hand)
        valid_cards = group.get_where('cmc', '<=', 0)

        # choose play
        if len(valid_cards) > 0:
            card = valid_cards[0]
            play_land(card)
            # LEFT OFF HERE

    player.initial_draw()

    player.untap_step()

    player.print_state()  #

    play_land()

    player.print_state()  #

    print(ut.repr3([card.heuristic_infodict for card in player.hand]))
    pass


def load_list(decklist_text, mydiff):
    lines = decklist_text.split('\n')
    cardname_list = ut.flatten([
        [line[2:]] * int(line[0])
        for line in lines
        if (
            len(line) > 0 and not line.startswith('SB') and
            not line.startswith('#')
        )
    ])
    card_list = [
        lookup_card(cardname)
        for cardname in ut.ProgIter(cardname_list, 'Loading Cards', adjust=True)
    ]

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


def inspect_deck(deck):

    def get_card_tags(card, deck):
        tags = []
        stats = card.mana_source_stats(deck)
        if stats is not None:
            tags.append('land')
            if len(stats[1]) > 0:
                tags.append('tapland')
            else:
                tags.append('untapland')
        return tags
    # ------------
    print('len(deck) = %r' % (len(deck),))
    tags_list = [get_card_tags(card, deck) for card in deck.card_list]
    print('Deck Counts:')
    print(ut.repr2(ut.dict_hist(ut.flatten(tags_list)), nl=True))

    hand = deck.sample_hand()
    manastats_list = [card.mana_source_stats(deck) for card in hand]
    print(ut.list_str([card.name + ': ' + str(stats) for card, stats in zip(hand, manastats_list)]))
    tags_list = [get_card_tags(card, deck) for card in hand]
    print('Hand Counts')
    print(ut.repr2(ut.dict_hist(ut.flatten(tags_list)), nl=True))

    valid_tags = ['land', 'tapland', 'untapland']
    x = {tag: [] for tag in valid_tags}

    for _ in range(500):
        hand = deck.sample_hand()
        tags_list = [get_card_tags(card, deck) for card in hand]
        taghist = ut.dict_hist(ut.flatten(tags_list))
        for key, val in x.items():
            val.append(taghist.get(key, 0))

    print('Monte Stats:')
    for key, val in list(x.items()):
        print('%15s: %s' % (key, ut.repr2(ut.get_stats(val), precision=2)))

    def hand_stats():
        #[card.types for card in hand]
        #[card.rrr() for card in hand]
        [card.mana_source_stats(deck) for card in hand]
        card.types

    #cardlist = CardList(cards)
    #cardlist.render()


if __name__ == '__main__':
    """
    cd ~/code/mtgmonte
    >>> from mtgmonte import *  # NOQA

    """
    decklist_text, mydiff = testdata_deck()
    deck = load_list(decklist_text, mydiff)
    inspect_deck(deck)
    goldfish(deck)

if __name__ == '__main__':
    r"""
    CommandLine:
        set PYTHONPATH=%PYTHONPATH%;C:/Users/joncrall/code/mtgmonte
        python -B %HOME%/code/mtgmonte/mtgmonte.py
        python -B %HOME%/code/mtgmonte/mtgmonte.py --allexamples
    """
    #import multiprocessing
    #multiprocessing.freeze_support()  # for win32
    #import utool as ut  # NOQA
    #ut.doctest_funcs()