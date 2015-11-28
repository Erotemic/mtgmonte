from __future__ import absolute_import, division, print_function, unicode_literals
import utool as ut
import itertools
print, rrr, profile = ut.inject2(__name__, '[mtgutils]')


# Then check for color considerations
def can_cast(spell_sequence, land_list):
    """
    Returns if a spell sequence is castable given the currents lands
    (hacky because it doesnt take into account other mana sources
     like dark ritual or birds of paradise)
    """
    mana_combos = possible_mana_combinations(land_list)
    color_costs = [s.manacost_colored for s in spell_sequence]
    any_costs = [s.manacost_uncolored for s in spell_sequence]

    combined_any_cost = sum(any_costs)
    color2_num = ut.dict_hist(ut.flatten(color_costs))

    valid = True
    for mana_combo in mana_combos:
        color2_have = ut.dict_hist(mana_combo)
        color2_have = ut.ddict(lambda: 0, color2_have)
        valid = True

        for color, num_need in color2_num.items():
            num_have = color2_have[color]
            if num_have < num_need:
                valid = False
                break
            color2_have[color] -= num_need

        num_leftover = sum(color2_have.values())
        if num_leftover < combined_any_cost:
            valid = False

        if valid:
            break

    return valid


@ut.memoize
def possible_mana_combinations(land_list, deck=None):
    avail_mana = [land.mana_potential(deck=deck) for land in land_list]
    mana_combos = list(ut.iprod(*avail_mana))
    mana_combos = list(set([tuple(sorted(x)) for x in mana_combos]))
    return mana_combos


def get_max_avail_cmc(land_list):
    max_avail_cmc = sum([
        max(map(len, land.mana_potential()))
        for land in land_list])
    return max_avail_cmc


def get_cmc_feasible_sequences(spell_list, land_list):
    max_avail_cmc = get_max_avail_cmc(land_list)
    # Get spells castable on their own
    flags = [spell.cmc <= max_avail_cmc for spell in spell_list]
    feasible_spells = ut.compress(spell_list, flags)
    cmc_feasible_sequences = []
    for num in range(len(spell_list)):
        spell_combos = list(itertools.combinations(feasible_spells, num))
        for combo in spell_combos:
            total = sum([spell.cmc for spell in combo])
            if total <= max_avail_cmc:
                cmc_feasible_sequences.append(combo)
    return cmc_feasible_sequences



#def hacky_knapsack_solns():
#    # first determine which spells are castable without color consideration
#    # make knapsack items
#    total_avail_mana = len(land_list)
#    flags = [spell.cmc < total_avail_mana for spell in spell_list]
#    feasible_spells = ut.compress(spell_list, flags)

#    items = [(1, spell.cmc, idx) for idx, spell in enumerate(feasible_spells)]
#    total_val, subset = ut.knapsack(items, total_avail_mana)
#    spell_sequence = ut.take(feasible_spells, ut.get_list_column(subset, 2))

#    # http://stackoverflow.com/questions/30007102/number-of-all-combinations-in-knapsack-task
#    # TODO:
#    # http://stackoverflow.com/questions/30554290/how-to-derive-all-solutions-from-knapsack-dp-matrix
#    #items = [1,1,3,4,5]
#    items = [2, 3, 4, 3, 3, 5, 4, 1, 1, 3]
#    knapsack = []
#    limit = 7

#    #@util_decor.memoize_nonzero
#    def print_solutions(current_item, knapsack, current_sum):
#        #if all items have been processed print the solution and return:
#        if current_item == len(items):
#            print(knapsack)
#            return

#        #don't take the current item and go check others
#        print_solutions(current_item + 1, list(knapsack), current_sum)

#        #take the current item if the value doesn't exceed the limit
#        if (current_sum + items[current_item] <= limit):
#            knapsack.append(items[current_item])
#            current_sum += items[current_item]
#            #current item taken go check others
#            print_solutions(current_item + 1, knapsack, current_sum )
#print_solutions(0, knapsack, 0)
