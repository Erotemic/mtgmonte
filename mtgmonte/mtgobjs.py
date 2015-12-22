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
#ut.util_cache.VERBOSE_CACHE = False
print, rrr, profile = ut.inject2(__name__, '[mtgobjs]')


MANA_SYMBOLS = 'WUBRG'
PERMANENT_TYPES = {'Artifact', 'Creature', 'Enchantment', 'Land', 'Planeswalker'}
_TAPLIKE_UNICODE = ['⟳', '↷']
TAPPED = _TAPLIKE_UNICODE[-1]
COLOR_ORDER = {sym: count for count, sym in enumerate(MANA_SYMBOLS + 'C')}


class NotEnoughManaError(Exception):
    pass


#@six.add_metaclass(ut.ReloadingMetaclass)
class _ManaBase(object):
    """
    Base class for mana objects
    """
    def __str__(self):
        return self.get_str()

    # def __str__(self):
    #     return self.get_str()

    # def __repr__(self):
    #     return '<ManaCost' + self.get_str() + '>'

    def __repr__(self):
        # if self.source is None:
        return '<{classname} {str_}>'.format(
            classname=self.__class__.__name__, str_=self.get_str())
        # return '<Mana {color} at {addr}>'.format(
        #     color=self.color, addr=hex(id(self)))
        # else:
        #     return '<Mana {color} from {source} at {addr}>'.format(
        #         color=self.color, source=self.source,
        #         addr=hex(id(self)))

    def __hash__(self):
        return hash(ut.hashstr27(self.astuple()))

    def __eq__(self, other):
        return self.astuple() == other.astuple()

    def __add__(self, other):
        return self.add(other)

    def __radd__(self, other):
        if other == 0:
            return self
        return self + other

    def __sub__(self, other):
        return self.sub(other)

    def __rsub__(self, other):
        return other.sub(self)


class ManaOption(list):
    def get_str(self):
        return '[' + ', '.join([
            #item.get_str()
            str(item)
            #if isinstance(item, ManaSet) else
            if hasattr(item, 'get_str') else
            repr(item)
            for item in self]) + ']'

    def __str__(self):
        return self.get_str()

    def __repr__(self):
        return '<{classname} {str_}>'.format(
            classname=self.__class__.__name__, str_=self.get_str())


#@six.add_metaclass(ut.ReloadingMetaclass)
class Mana(_ManaBase):
    def __init__(self, color, source=None, num=1):
        if isinstance(color, Mana):
            color = color.color
        self.color = color
        self.source = source
        self.num = num

    def get_str(self):
        try:
            if self.num == 1:
                return self.color
            elif isinstance(self.num, int):
                return '%s*%d' % (self.color, self.num,)
            elif self.num == '∞':
                return self.color + '*INF'  # '∞'
            else:
                return self.color + '*'
        except Exception as ex:
            ut.printex(ex, 'Error making str', keys=['self.num', 'self.color', 'self.source'])
            raise

    def __eq__(self, other):
        if isinstance(other, six.string_types):
            return self.num == 1 and self.color == other
        else:
            return self.astuple() == other.astuple()

    def __gt__(self, other):
        return COLOR_ORDER[self.color] > COLOR_ORDER[other.color]

    def __lt__(self, other):
        return COLOR_ORDER[self.color] < COLOR_ORDER[other.color]

    def astuple(self):
        return (self.color, self.source, self.num)


#@six.add_metaclass(ut.ReloadingMetaclass)
class ManaSet(_ManaBase):
    """
    CommandLine:
        python -m mtgmonte.mtgobjs --exec-ManaSet

    Example:
        >>> # ENABLE_DOCTEST
        >>> from mtgmonte.mtgobjs import *
        >>> from mtgmonte import mtgobjs
        >>> mana = mtgobjs.ManaSet('CCUUR')
        >>> result = ('mana = %r' % (mana,))
        >>> print(result)
        mana = {CCUUR}
    """
    def __init__(self, manas=None, sources=None):
        # TODO: use a dict representation instead?
        _manas = ensure_mana_list(manas, sources)
        self._manas = sorted(_manas)

    def astuple(self):
        return (self._manas,)

    def get_str(self):
        body = ''.join([m.get_str() for m in self._manas])
        return '{%s}' % (body,)

    def __getitem__(self, index):
        return self._manas[index]

    def __gt__(self, other):
        if len(self._manas) > len(other._manas):
            return True
        elif len(self._manas) == len(other._manas):
            return self._manas[0] > other._manas[0]
        else:
            return False

    def get_colordict(self):
        color2_num = ut.dict_hist([m.color for m in self._manas for _ in range(m.num)])
        return color2_num

    def add(self, other):
        """
        Example:
            >>> # ENABLE_DOCTEST
            >>> from mtgmonte.mtgobjs import *
            >>> from mtgmonte import mtgobjs
            >>> self = mtgobjs.ManaSet('R')
            >>> other = mtgobjs.ManaSet('G')
            >>> mana = self + other
            >>> result = ('mana = %r' % (mana,))
            >>> print(result)
            mana = {RG}
        """
        other_manas = ensure_mana_list(other)
        return ManaSet(self._manas + other_manas)

    def sub(self, other):
        """
        CommandLine:
            python -m mtgmonte.mtgobjs --exec-ManaSet.sub:0
            python -m mtgmonte.mtgobjs --exec-ManaSet.sub:1

        Example:
            >>> # ENABLE_DOCTEST
            >>> from mtgmonte.mtgobjs import *
            >>> from mtgmonte import mtgobjs
            >>> self = mtgobjs.ManaSet('RRRUC')
            >>> other = mtgobjs.ManaSet('RRU')
            >>> mana = self - other
            >>> result = ('mana = %r' % (mana,))
            >>> print(result)
            mana = {RC}

        Example:
            >>> from mtgmonte.mtgobjs import *  # NOQA
            >>> self = ManaSet(['WWURC'])
            >>> other = ManaCost([('W', 'colored'), ('W', 'colored'), ('U', 'colored'), ('1', 'uncolored')])
            >>> mana = self - other
            >>> result = ('mana = %r' % (mana,))
            >>> print(result)
        """
        if isinstance(other, ManaCost):
            colored_cost = ManaSet(other.type2_manas['colored'])
            remainder1 = self.sub(colored_cost)
            color2_remain = remainder1.get_colordict()
            uncolored_need = sum(other.type2_manas['uncolored'])
            # TODO: value different colors differently for payment
            if uncolored_need > 0:
                for color in list(color2_remain.keys()):
                    using = min(uncolored_need, color2_remain[color])
                    color2_remain[color] -= using
                    uncolored_need -= using
            if uncolored_need > 0:
                raise NotEnoughManaError('Cannot subtract more mana from less')
            # Todo hybrid / phyrexian
        else:
            color2_need = ut.dict_hist(other._manas)
            color2_remain = ut.ddict(lambda: 0, ut.dict_hist(self._manas))
            for color, num_need in color2_need.items():
                num_have = color2_remain[color]
                if num_have < num_need:
                    raise NotEnoughManaError('Cannot subtract more mana from less')
                color2_remain[color] -= num_need
        color2_remain = delete_dict_zeros(color2_remain)
        remainder = ManaSet(color2_remain)
        return remainder


#@six.add_metaclass(ut.ReloadingMetaclass)
class ManaCost(_ManaBase):
    r"""
    Represents mana costs of spells and abilities. Can represent conditional
    costs such as hybrid mana, phyrexian mana, delve, and snow mana.

    CommandLine:
        python -m mtgmonte.mtgobjs --exec-ManaCost --show

    Example:
        >>> from mtgmonte.mtgobjs import *  # NOQA
        >>> card = load_cards(['Everlasting Torment', 'Spectral Procession'])[0]
        >>> tokens = card._parse_manacost_tokens()
        >>> print('tokens = %r' % (tokens,))
        >>> self = ManaCost(tokens)
        >>> print(self)
        >>> print(self.hybrid)
        {2(B/R)}
    """
    def __init__(self, tokens):
        vals = ut.get_list_column(tokens, 0)
        types = ut.get_list_column(tokens, 1)
        self.type2_manas = dict(ut.group_items(vals, types))
        if 'uncolored' in self.type2_manas:
            self.type2_manas['uncolored'] = ut.lmap(int, self.type2_manas['uncolored'])

    def get_str(self):
        body = ''.join([str(m) for ms in self.type2_manas.values() for m in ms])
        return '{%s}' % (body,)

    def satisfies(self, manaset):
        try:
            remain = manaset.sub(self)
        except NotEnoughManaError:
            return False
        else:
            return True

    #def to_manaset(self):
    #    ManaSet(self.type2_manas['colored'] + self.type2_manas['uncolored'])

    def astuple(self):
        return (self.type2_manas,)

    def __len__(self):
        return sum(map(len, self.type2_manas.values()))

    def add(self, other):
        return ManaCost(self.get_tokens() + other.get_tokens())

    def get_tokens(self):
        tokens = [(color, type_)
                  for type_, color_list in self.type2_manas.items()
                  for color in color_list]
        return tokens

    @property
    def colored(self):
        return ManaCost([(c, 'colored') for c in self.type2_manas.get('colored', [])])

    @property
    def uncolored(self):
        return ManaCost([(c, 'uncolored') for c in self.type2_manas.get('uncolored', [])])

    @property
    def hybrid(self):
        return ManaCost([(c, 'hybrid') for c in self.type2_manas.get('hybrid', [])])

    @property
    def phyrexian(self):
        return ManaCost([(c, 'phyrexian') for c in self.type2_manas.get('phyrexian', [])])


#@six.add_metaclass(ut.ReloadingMetaclass)
class ManaPool(ManaSet):
    """ Only represents real colored and uncolored allocations of mana """
    def __init__(self, *args, **kwargs):
        super(self, ManaPool).__init__(*args, **kwargs)


def ensure_mana_list(manas=None, source=None):
    from mtgmonte import mtgobjs
    #if sources is None:
    #    source = None
    #else:
    #    source = None
    if manas is None:
        manas = []
    elif hasattr(manas, '_manas'):  # isinstance(manas, ManaSet):
        manas = manas._manas
    #elif isinstance(manas, mtgobjs.Mana):  # isinstance(manas, ManaSet):
    elif hasattr(manas, 'color'):
        manas = [manas]
    elif isinstance(manas, dict):  # isinstance(manas, ManaSet):
        manas = [mtgobjs.Mana(color, source, num) for color, num in manas.items()]
    elif isinstance(manas, six.string_types):
        colors = manas.strip('{}')
        manas = [mtgobjs.Mana(color, source) for color in colors]
    elif isinstance(manas, (list, tuple)):
        manas = ut.flatten([ensure_mana_list(m) for m in manas])
    else:
        print('mtgobjs.Mana = %r' % (mtgobjs.Mana,))
        print('type(manas)  = %r' % (type(manas),))
        print(type(manas) is mtgobjs.Mana)
        print(isinstance(manas, mtgobjs.Mana))
        raise ValueError('Cannot ensure unknown type=%r, manas=%r' % (type(manas), manas,))
    return manas


#@six.add_metaclass(ut.ReloadingMetaclass)
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
#@six.add_metaclass(ut.ReloadingMetaclass)
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

    def _parse_manacost_tokens(card):
        """

        CommandLine:
            python -m mtgmonte.mtgobjs --exec-Card2._parse_manacost_tokens --show

        Example:
            >>> # ENABLE_DOCTEST
            >>> from mtgmonte.mtgobjs import *  # NOQA
            >>> cards = load_cards(['Naya Hushblade', 'Gitaxian Probe', 'Spectral Procession', 'Emrakul, the Aeons Torn'])
            >>> print(ut.repr2([card._parse_manacost_tokens() for card in cards], nl=2, nobraces=True))

        """
        colored_pat = ut.named_field('colored', '[' + MANA_SYMBOLS + ']')
        uncolored_pat = ut.named_field('uncolored', '[0-9]+', )
        phyrexian_pat = ut.named_field('phyrexian', '\([' + MANA_SYMBOLS + ']/P\)')
        hybrid_pat = ut.named_field('hybrid', '\([0-9' + MANA_SYMBOLS + ']/[' + MANA_SYMBOLS + ']\)')
        patern = ut.regex_or([uncolored_pat, colored_pat, hybrid_pat, phyrexian_pat])
        groupdicts = [x.groupdict() for x in re.finditer(patern, card.mana_cost)]
        tokens = [(v, k) for d in groupdicts for k, v in d.items() if v is not None]
        # tokens = [x.groups() for x in re.finditer(patern, card.mana_cost)]
        # assert all([len(t) == 1 for t in tokens])
        # tokens = [t[0] for t in tokens]
        return tokens

    @property
    def mana_cost2(card):
        r"""
        Returns:
            ManaCost:

        CommandLine:
            python -m mtgmonte.mtgobjs --exec-Card2.mana_cost2 --show

        Example:
            >>> # ENABLE_DOCTEST
            >>> from mtgmonte.mtgobjs import *  # NOQA
            >>> cards = load_cards(['Cruel Ultimatum', 'Kitchen Finks', 'Gitaxian Probe', 'Spectral Procession', 'Emrakul, the Aeons Torn'])
            >>> print(ut.repr2([card.mana_cost for card in cards], nl=1, nobraces=True))
            >>> result = ut.repr2([card.mana_cost2 for card in cards], nl=1, nobraces=True)
            >>> print(result)
            {UUBBBRR},
            {(G/W)(G/W)},
            {(U/P)},
        """
        tokens = card._parse_manacost_tokens()
        return ManaCost([t for t in tokens])
        # print(card.mana_cost)
        # return [x for x in card.mana_cost if x in MANA_SYMBOLS]
        # return ManaCost([x for x in card.mana_cost if x in MANA_SYMBOLS])

    @property
    def cmc(card):
        r"""
        Returns:
            int: converted mana cost

        CommandLine:
            python -m mtgmonte.mtgobjs --exec-Card2.cmc --show

        Example:
            >>> # ENABLE_DOCTEST
            >>> from mtgmonte.mtgobjs import *  # NOQA
            >>> cards = load_cards(['Emrakul, the Aeons Torn', 'Kitchen Finks', 'Gitaxian Probe', 'Spectral Procession'])
            >>> #print(ut.repr2([card.converted_mana_cost for card in cards]))
            >>> result = ut.repr2([card.cmc for card in cards], nobraces=True)
            >>> print(result)
            15, 3, 1, 6
        """
        if len(card.mana_cost) > 0:
            try:
                cmc = int(card.converted_mana_cost)
            except AttributeError:
                cmc = len(card.mana_cost)
        else:
            cmc = 0
        return cmc

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

            if mtgrules.is_fetchland(block, card):
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
        from mtgmonte import mtgrules
        blocks = card.rules_text.split(';')
        return list(filter(mtgrules.is_ability_block, blocks))
        #return blocks

    def mana_potential2(card, deck=None, recurse=True):
        r"""Returns a list of mana sets or mana producers

        CommandLine:
            python -m mtgmonte.mtgobjs --exec-mana_potential2:1

        Example:
            >>> # ENABLE_DOCTEST
            >>> from mtgmonte import mtgobjs
            >>> deck = mtgobjs.Deck(mtgobjs.load_cards(['Tropical Island', 'Sunken Hollow', 'Island']))
            >>> cards = mtgobjs.load_cards(['Tundra', 'Ancient Tomb', 'Black Lotus'])
            >>> card = cards[-1]
            >>> result = ut.repr2([card.mana_potential2(deck) for card in cards])
            >>> print(str(result))

        Example:
            >>> # ENABLE_DOCTEST
            >>> from mtgmonte import mtgobjs
            >>> deck = mtgobjs.Deck(mtgobjs.load_cards(['Tropical Island', 'Sunken Hollow', 'Island']))
            >>> cards = mtgobjs.load_cards(['Flooded Strand', 'Tundra', 'Island', 'Shivan Reef', 'Ancient Tomb'])
            >>> card = cards[-1]
            >>> result = ut.repr2([card.mana_potential2(deck, recurse=True)
            >>>                    for card in cards], nl=1, strvals=1, nobr=1)
            >>> print(result)
            [{G}, {U}, {B}],
            [{W}, {U}],
            [{U}],
            [{C}, {U}, {R}],
            [{CC}],

        Example:
            >>> # ENABLE_DOCTEST
            >>> from mtgmonte import mtgobjs
            >>> deck = mtgobjs.Deck(mtgobjs.load_cards(['Tropical Island', 'Sunken Hollow', 'Island']))
            >>> cards = mtgobjs.load_cards(['Flooded Strand', 'Tundra', 'Island', 'Shivan Reef', 'Ancient Tomb'])
            >>> card = cards[-1]
            >>> result = ut.repr2([card.mana_potential2(deck, recurse=False)
            >>>                    for card in cards], nl=1, strvals=True, nobr=1)
            >>> print(result)
            [Tropical Island, Sunken Hollow, Island],
            [{W}, {U}],
            [{U}],
            [{C}, {U}, {R}],
            [{CC}],
        """
        from mtgmonte import mtgrules
        potential = ManaOption()
        #ManaOption()
        for block in card.ability_blocks:
            mana_generated = mtgrules.mana_generated(block, card)
            if mana_generated is not None:
                potential.extend(mana_generated)
            else:
                if mtgrules.is_fetchland(block, card):
                    fetch_targets = mtgrules.get_fetch_search_targets(block, card, deck)
                    if recurse:
                        mana_generated = [t.mana_potential2(deck) for t in fetch_targets]
                        mana_generated = ut.flatten(mana_generated)
                        mana_generated = ut.unique_ordered(mana_generated)
                        potential.extend(ManaOption(mana_generated))
                    else:
                        potential.extend(fetch_targets)
        return potential

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


#@ut.memoize
@ut.cached_func('lookup_card', appname='mtgmonte_', key_argx=[0], verbose=False)
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
    #card.rrr(verbose=False)
    return card


def delete_dict_zeros(dict_):
    for key, val in list(dict_.items()):
        if val == 0:
            del dict_[key]
    return dict_


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
