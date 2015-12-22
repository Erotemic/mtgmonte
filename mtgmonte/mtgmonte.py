# -*- coding: utf-8 -*-
"""
References:
    mtg forge http://mtgrares.blogspot.com/
    http://svn.slightlymagic.net/websvn/listing.php?repname=forge
    http://svn.slightlymagic.net/websvn/listing.php?repname=forge&path=%2Ftrunk%2Fforge-ai%2Fsrc%2Fmain%2Fjava%2Fforge%2Fai%2F&#a882f1d0caaba54135bcb4877bc0cac72

sudo apt-get install libxml2-dev libxslt1-dev -y
pip install cython
# pip install git+git://github.com/chigby/mtg.git@master
pip install mtg

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
from six import text_type
import numpy as np
import re
from mtgmonte import mtgrules
from mtgmonte import mtgobjs
#from six.moves import
ut.util_cache.VERBOSE_CACHE = False
print, rrr, profile = ut.inject2(__name__, '[mtgmonte]')


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
    print(ut.list_str([card.name + ': ' + text_type(stats) for card, stats in zip(hand, manastats_list)]))
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


@six.add_metaclass(ut.ReloadingMetaclass)
class Player(object):
    """
    An agent
    player = Player()
    """
    def __init__(player, deck):
        player.deck = deck
        player.id_ = 0
        player.hand = []
        player.bfield = []
        player.graveyard = []
        player.exiled = []
        player.turn = 0
        player.life = 20
        player.verbose = 2

    def find_maxval_spell_sequence(player):
        # sim land in play
        # really need available mana
        from mtgmonte import mtgutils
        land_in_play = player.get_cards_in_play(['Land'])
        nonland_in_hand = player.get_cards_in_hand(['Land'], invert=True)

        land_list = land_in_play
        spell_list = nonland_in_hand

        max_avail_cmc = mtgutils.get_max_avail_cmc(land_list, deck=player.deck)
        cmc_feasible_sequences = mtgutils.get_cmc_feasible_sequences(
            spell_list, max_avail_cmc)

        if len(cmc_feasible_sequences) == 0:
            sequence = []
            value = 0
        else:
            mana_combos = mtgutils.possible_mana_combinations(land_list, player.deck)
            flags = [mtgutils.can_cast(spell_sequence, mana_combos)
                     for spell_sequence in cmc_feasible_sequences]
            feasible_sequences = ut.compress(cmc_feasible_sequences, flags)
            if len(feasible_sequences) == 0:
                sequence = []
                value = 0
            else:
                # Find best value in feasible solutions
                value_list = [
                    sum([card.get_goldfish_value() for card in combo])
                    for combo in feasible_sequences
                ]
                index = ut.list_argmax(value_list)
                sequence = feasible_sequences[index]
                value = len(sequence)
        return sequence, value

    def get_ability_targets(player, card, ability):
        def get_valid_targets(effects, card, player):
            valid_targets_list = []
            target_values_list = []
            for effect in effects:
                if effect.startswith('Search your'):
                    targets = mtgrules.get_fetch_search_targets(effect, card, player.deck)
                    # allow fail to find, but it doesnt add any value
                    # (except maybe a shuffle value)
                    valid_targets_list += [targets + [None]]
                    # TODO: assign values
                    target_values_list += [[1] * len(targets) + [0]]
                elif effect == 'shuffle your library':
                    valid_targets_list += [[None]]
                    target_values_list += [[0]]
            return valid_targets_list, target_values_list

        def choose_targets(effects, card, player, valid_targets_list, target_values_list):
            targets_list = []
            effect_value = 0
            for effect, valid_targets, values in zip(effects, valid_targets_list, target_values_list):
                # TODO: Make Intelligent Choice
                # TODO: Disllow casting if targeted spells with illegal targets
                if len(valid_targets) == 0:
                    raise Exception('Illegal targets, fail to find should be None')
                idx = ut.list_argmax(values)
                targets_list += [valid_targets[idx]]
                effect_value += values[idx]
            return targets_list, effect_value

        effects = ability['effects']
        valid_targets_list, target_values_list = get_valid_targets(
            effects, card, player)
        targets_list, effect_value = choose_targets(
            effects, card, player, valid_targets_list, target_values_list)
        return targets_list, effect_value

    def execute_costs(player, card, costs):
        for cost in costs:
            match = re.search(r'Pay (?P<num>\d+) life', cost)
            if cost == '{T}':
                player.tap_card(card)
            elif match:
                groupdict = match.groupdict()
                num = float(groupdict['num'])
                player.lose_life(num)
            elif cost == 'Sacrifice ' + card.name:
                player.sacrifice_card(card)
            else:
                raise NotImplementedError('UNKNOWN COST: ' + cost)

    def execute_effects(player, effects, targets_list):
        for effect, targets in zip(effects, targets_list):
            if effect.startswith('Search your library for'):
                if targets is None:
                    print('Fail to find')
                else:
                    player.deck.library.remove(targets)
                    if effect.endswith('and put it onto the battlefield'):
                        player.put_on_battlefield(targets)
                    elif effect.endswith('and put it onto the battlefield tapped'):
                        player.put_on_battlefield(targets, ['tapped'])
            elif effect == 'shuffle your library':
                player.shuffle()
            else:
                raise NotImplementedError('UNKNOWN EFFECT: ' + effect)

    def execute_ability(player, card, ability, targets_list):
        costs = ability['costs']
        effects = ability['effects']
        with ut.Indenter('    '):
            player.execute_costs(card, costs)
            player.execute_effects(effects, targets_list)

    def main_phase1_step(player):
        player.play_land()
        fetchland_heuristic(player)
        sequence, value = player.find_maxval_spell_sequence()
        for card in sequence:
            player.play_card_from_hand(card)

    def play_land(player, method='brute1'):
        r"""
        Returns:
            list: value_list

        CommandLine:
            cd ~/code/mtgmonte
            python -m mtgmonte --exec-play_land --cmd

        Example:
            >>> # DISABLE_DOCTEST
            >>> from mtgmonte.mtgmonte import *  # NOQA
            >>> decklist_text, mydiff = testdata_deck()
            >>> deck = mtgobjs.load_list(decklist_text, mydiff)
            >>> player = Player(deck)
            >>> rng = np.random
            >>> rng = np.random.RandomState(2)
            >>> player.reset(rng=rng)
            >>> player.initial_draw()
            >>> player.print_state()
            >>> # player.draw_cards(10)
            >>> #[player.play_land(method='naive') for _ in range(3)]
            >>> for tx in range(4):
            >>>     player.untap_step()
            >>>     player.draw_step()
            >>>     player.main_phase1_step()
            >>>     player.print_state()

            # >>> # ----
            # >>> player.play_land()
            # >>> player.print_state()
        """
        if player.verbose >= 1:
            print('+ --- Play Land')

        # Choose best land to play
        land_in_hand = player.get_cards_in_hand(['Land'])
        if len(land_in_hand) == 0:
            if player.verbose >= 2:
                print('Missed land drop')
            return
        else:
            if method == 'naive':
                value_list = []
                for land in land_in_hand:
                    if player.turn == 1:
                        if 'tap' in land.heuristic_types:
                            value_list += [2]
                        else:
                            value_list += [1]
                    else:
                        value_list += [1]
            elif method == 'brute1':
                # See what is the maximum value over all possible lands
                value_list = []
                for land in land_in_hand:
                    future_player = player.copy()
                    future_player.verbose = 0
                    land_ =  player.deck.reflect_card_list([land], future_player.deck)[0]
                    future_player.play_card_from_hand(land_)
                    # For now just several turns in the future in a greedy fashion.
                    # Turn this into a dynamic program later
                    total_value = 0
                    for tx in range(4):
                        sequence, value = future_player.find_maxval_spell_sequence()
                        turn_modifier = np.log(2) / np.log(2 + tx)
                        [future_player.play_card_from_hand(card) for card in sequence]
                        future_player.untap_step()
                        total_value += (value * turn_modifier)
                    # print('total_value = %r' % (total_value,))
                    value_list.append(total_value)
                print('\nChecking value land drops: %r' % (dict(zip(land_in_hand, value_list)),))

            idx = ut.list_argmax(value_list)
            land = land_in_hand[idx]
            player.play_card_from_hand(land)
        if player.verbose >= 3:
            player.print_state()

        """
        # Need to formulate as a sequencing problem
        # Find the sequence of land drops that maximizes mana efficiency
        # We temporarilly ignore the issue of when playing a card effects
        # mana in the subsequent turns.
        # Mana Sources = {B}, {R}, {W,G}T, {G}
        # Cards = [R], [RB], [W], [GG], [2B]
        # Get land with maximum play value
        # Land choice is a dynamic programming algorithm
        t = turn
        l = land

        value(t, l) - value of playing land l on turn t
        hand(t) - lands in hand on turn t
        #castable(l) - value of castable cards after playing land l
        cast(l) - value of cast cards after playing land l

        value(t) = value(t - 1) + max([value(l) for l in hand(t)])
        """

    def _on_reload(player):
        player.deck.rrr(False)

    def copy(player):
        """
        CommandLine:
            cd ~/code/mtgmonte
            python -m mtgmonte --exec-Player.copy --cmd

        Example:
            >>> # DISABLE_DOCTEST
            >>> from mtgmonte.mtgmonte import *  # NOQA
            >>> decklist_text, mydiff = testdata_deck()
            >>> deck = mtgobjs.load_list(decklist_text, mydiff)
            >>> player = Player(deck)
            >>> rng = np.random.RandomState(3)
            >>> player.reset(rng=rng)
            >>> player.initial_draw()
            >>> player.print_state()
            >>> player.draw_cards(10)
            >>> [player.play_land() for _ in range(2)]
            >>> player2 = player.copy()
            >>> str1 = player.get_statestr()
            >>> str2 = player2.get_statestr()
            >>> assert str1 == str2
            >>> assert player.deck.card_list[0] is not player2.deck.card_list[0]
            >>> assert player.hand[0] in player.deck.card_list
            >>> assert player.hand[0] not in player2.deck.card_list
            >>> assert player2.hand[0] in player2.deck.card_list
            >>> assert player2.hand[0] not in player2.deck.library
            >>> print(str1)
            >>> player2.play_land()
            >>> player2.play_land()
            >>> player2.play_land()
            >>> player.print_state()
            >>> player2.print_state()
        """
        other_deck = player.deck.copy()
        other = Player(other_deck)
        other.id_ = player.id_
        other.hand = player.deck.reflect_card_list(player.hand, other_deck)
        other.graveyard = player.deck.reflect_card_list(player.graveyard, other_deck)
        other.bfield = player.deck.reflect_card_list(player.bfield, other_deck)
        other.exiled = player.deck.reflect_card_list(player.exiled, other_deck)
        other.turn = player.turn
        other.life = player.life
        return other

    def reset(player, rng=None):
        player.deck.reset(rng=rng)
        player.turn = 0
        player.life = 20
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

    def infodict2(player):
        infodict = ut.odict([
            #('id_', player.id_),
            ('turn', player.turn),
            ('life', player.life),
            ('library_hash', ut.hashstr27(str(player.deck.library))),
            ('library_size', len(player.deck)),
            ('hand_size', len(player.hand)),
            ('bfield_size', len(player.bfield)),
            ('graveyard_size', len(player.graveyard)),
            ('exiled_size', len(player.exiled)),
            ('hand', mtgobjs.CardGroup(player.hand).infohist),
            ('bfield', mtgobjs.CardGroup(player.bfield).infohist),
            ('graveyard', mtgobjs.CardGroup(player.graveyard).infohist),
        ])
        return infodict

    def get_statestr(player):
        statestr = ut.repr2(player.infodict2(), nl=2, strvals=True)
        return statestr

    def print_state(player):
        statestr = player.get_statestr()
        print(ut.highlight_code(statestr))

    def initial_draw(player):
        if player.verbose >= 1:
            print('+ --- Initial Draw')
        player.draw_cards(num=7)
        if player.verbose >= 3:
            player.print_state()

    def untap_step(player):
        player.turn += 1
        if player.verbose >= 1:
            print('\n===================')
            print('+ --- Untap Step. Turn %r ' % (
                player.turn,))
        max_land_drops = 1
        player.land_drops_left = max_land_drops
        for card in player.bfield:
            if 'tapped' in card.state:
                player.untap_card(card)
        if player.verbose >= 3:
            player.print_state()

    def upkeep_step(player):
        if player.verbose >= 1:
            print('+ --- Upkeep Step')
        if player.verbose >= 3:
            player.print_state()

    def draw_step(player):
        if player.verbose >= 1:
            print('+ --- Draw Step')
        player.draw_cards(num=1)
        if player.verbose >= 3:
            player.print_state()

    def draw_cards(player, num=1):
        cards = player.deck.draw_card(num)
        if player.verbose >= 2:
            print('Player draws %d cards: %s' % (num, ut.repr2(mtgobjs.CardGroup(cards).infohist, nl=1),))
        player.hand.extend(cards)

    def play_card_from_hand(player, card, verbose=None):
        if verbose is None:
            verbose = player.verbose
        if verbose:
            print('Player plays %s from hand' % (card,))
        player.hand.remove(card)
        if card.is_permanent():
            player.put_on_battlefield(card)
        else:
            player.put_in_graveyard(card)

    def put_on_battlefield(player, card, modifiers=None, verbose=None):
        if verbose is None:
            verbose = player.verbose
        modifiers_ = card.get_etb_modifiers(player=player)
        if modifiers is None:
            modifiers = []
        modifiers = modifiers_ + modifiers
        if verbose >= 1:
            print('%s enters the battlefield, modifiers=%r' % (card, modifiers))
        card.state.extend(modifiers)
        player.bfield.append(card)

    def remove_from_battlefield(player, card):
        if player.verbose >= 1:
            print('%s leaves the battlefield' % (card,))
        player.bfield.remove(card)
        card.state = []

    def put_in_graveyard(player, card):
        if player.verbose >= 1:
            print('%s enters the graveyard' % (card,))
        # CARD ENTERS BATTLEFIELD
        player.graveyard.append(card)

    def shuffle(player):
        if player.verbose >= 1:
            print('shuffling')
        player.deck.shuffle()

    def lose_life(player, num):
        if player.verbose >= 1:
            print('Losing %d life' % (num,))
        player.life -= num

    def tap_card(player, card):
        if player.verbose >= 1:
            print('Tapping ' + card.name)
        card.state.append('tapped')

    def untap_card(player, card):
        if player.verbose >= 1:
            print('Untapping ' + card.name)
        card.state.remove('tapped')

    def sacrifice_card(player, card):
        print('Sacrificing ' + card.name)
        with ut.Indenter('     '):
            player.remove_from_battlefield(card)
            player.put_in_graveyard(card)

    def get_cards_in_play(player, valid_types=None):
        return [
            c for c in player.bfield
            if valid_types is None or ut.is_superset(c.types, valid_types)
        ]

    def get_cards_in_hand(player, valid_types=None, invert=False):
        card_list = player.hand
        if valid_types is None:
            valid_cards = card_list
        else:
            flags = [ut.is_superset(c.types, valid_types)
                     for c in card_list]
            if invert:
                flags = ut.not_list(flags)
            valid_cards = ut.list_compress(card_list, flags)
        return valid_cards


def get_cost_value(player, card, costs):
    total_cost_value = 0
    for cost in costs:
        match = re.search(r'Pay (?P<num>\d+) life', cost)
        if match:
            groupdict = match.groupdict()
            num = float(groupdict['num'])
            denom =  (player.life - 1)
            if denom <= 0:
                total_cost_value += np.inf
            else:
                total_cost_value += (num / denom)
    return total_cost_value


def fetchland_heuristic(player):
    for card in player.bfield:
        if 'fetch' in card.heuristic_types:
            ability = card.get_abilities()[0]
            targets_list, effect_value = player.get_ability_targets(card, ability)
            cost_value = get_cost_value(player, card, ability['costs'])
            #print('effect_value = %r' % (effect_value,))
            #print('cost_value = %r' % (cost_value,))
            #print('total_value = %r' % (total_value,))
            total_value = (effect_value - cost_value)
            # print('Ability Value =  %r' % (total_value,))
            if total_value > 0:
                print('Activating %s, ability 0.' % (card.name,))
                player.execute_ability(card, ability, targets_list)
            elif total_value == 0:
                # print('No value to cracking ' + card.name)
                player.execute_ability(card, ability, targets_list)
            else:
                pass
                # print('Negative value to crack ' + card.name)


def goldfish(deck):
    player = Player(deck)

    print('Starting Goldfish')

    def get_resources():
        resources = {}
        resources['land_drops_left'] = player.land_drops_left
        #group = CardGroup(player.bfield)
        untapped_lands = [
            c for c in player.bfield
            if ut.is_superset(c.types, ['Land']) and 'tapped' not in c.state]
        mana_potential = [
            c.mana_source_stats()
            for c in untapped_lands]
        resources['mana_potential'] = mana_potential
        resources['life'] = 20

    player.rrr(False)

    player.reset()
    player.initial_draw()

    player.print_state()

    print(' GAME START')

    for global_turn in range(0, 10):

        player.untap_step()

        if global_turn > 0:
            player.draw_step()
        else:
            print('+ --- Skip First Draw Phase')

        player.play_land()

        fetchland_heuristic(player)

        player.print_state()
        print('END TURN %d\n' % (player.turn,))

    #print(ut.repr3([card.heuristic_infodict for card in player.hand]))
    pass


def main():
    r"""
    CommandLine:
        python mtgmonte.py --exec-main
        python -m mtgmonte --exec-main

    Example:
        >>> # SCRIPT
        >>> from mtgmonte.mtgmonte import *  # NOQA
        >>> result = main()
        >>> print(result)
    """
    decklist_text, mydiff = testdata_deck()
    deck = mtgobjs.load_list(decklist_text, mydiff)
    #inspect_deck(deck)
    goldfish(deck)


if __name__ == '__main__':
    """
    cd ~/code/mtgmonte
    >>> from mtgmonte.mtgmonte import *  # NOQA

    """
    #from mtgmonte import mtgmonte
    #mtgmonte.main()

if __name__ == '__main__':
    r"""
    CommandLine:
        set PYTHONPATH=%PYTHONPATH%;C:/Users/joncrall/code/mtgmonte
        python -B %HOME%/code/mtgmonte/mtgmonte.py
        python -B %HOME%/code/mtgmonte/mtgmonte.py --allexamples
    """
    import multiprocessing
    multiprocessing.freeze_support()  # for win32
    import utool as ut  # NOQA
    res = ut.doctest_funcs()
    if res[1] == 0:
        main()
