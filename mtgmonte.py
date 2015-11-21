"""
cd ~/code/mtgmonte
"""
from __future__ import absolute_import, division, print_function, unicode_literals
import six
import utool as ut
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


@ut.memoize
@ut.cached_func('lookup_card', appname='mtgmonte', key_argx=[0])
def lookup_card(cardname):
    print('Lookup cardname = %r' % (cardname,))
    from mtglib.gatherer_request import SearchRequest
    from mtglib.card_extractor import CardExtractor
    from mtglib.card_renderer import CardList
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
    card2 = Card2()
    card2.__dict__.update(cards[0].__dict__)
    return card2


import numpy as np
from mtglib.card_renderer import Card


class DecisionNode(object):
    def __init__(self):
        self.options = []
        self.costs = []
        pass

    def marginalize(self):
        pass


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

    def sample_hand(deck):
        deck.initialize()
        return deck.draw_hand()

    def draw_hand(deck):
        rng = np.random
        hand = rng.choice(deck.card_list, size=(7,), replace=False).tolist()
        for card in hand:
            deck._library.remove(card)
        return hand


#ut.reloading_metacl
@six.add_metaclass(ut.ReloadingMetaclass)
class Card2(Card):
    def __repr__(self):
        return 'Card: ' + self.name

    def mana_source_stats(card, deck=None):
        """
        card = lookup_card('Mountain')
        card = lookup_card('Island')
        card = lookup_card('Evolving Wilds')
        card = lookup_card('Battlefield Forge')


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
                    import re
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

                    fetch_regex = (
                        'Search your library for a ' +
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
        for cardname in ut.ProgressIter(cardname_list, lbl='Loading Cards', adjust=True)
    ]

    def upgrade_card(card):
        card2 = Card2()
        card2.__dict__.update(card.__dict__)
        return card2

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

    card_list = list(map(upgrade_card, card_list))
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

    for _ in range(2000):
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
    decklist_text, mydiff = testdata_deck()
    load_list(decklist_text, mydiff)
