# -*- coding: utf-8 -*- from __future__ import absolute_import, division, print_function, unicode_literals
import utool as ut


def shadowform_probability():
    """ its hearthstone, but whatev

    probability of
    raza + no shadowform on turn 5 +

    probability of
    raza + shadowform on turn 5 +

    probability of
    kazakus turn 4, raza turn 5, + no shadowform

    """
    from scipy.stats import hypergeom

    def p_badstuff_shadowform(turn=5, hand_size=3):
        deck_size = 30
        num_shadowform = 2

        def prob_nohave_card_never_mulled(copies=2, hand_size=3):
            deck_size = 30
            prb = hypergeom(deck_size, copies, hand_size)
            # P(initial_miss)
            p_none_premul = prb.cdf(0)

            # GIVEN that we mul our first 3 what is prob we still are unlucky
            # P(miss_turn0 | initial_miss)
            prb = hypergeom(deck_size - hand_size, copies, hand_size)
            p_none_in_mul = prb.cdf(0)
            # TODO: add constraints about 2 drops
            #  P(miss_turn0) = P(miss_turn0 | initial_miss) *  P(initial_miss)
            p_none_at_start = p_none_in_mul * p_none_premul
            return p_none_at_start

        def prob_nohave_card_always_mulled(copies=2, hand_size=3):
            # probability of getting the card initially
            p_none_premul = hypergeom(deck_size, copies, hand_size).cdf(0)
            # probability of getting the card if everything is thrown away
            # (TODO: factor in the probability that you need to keep something)
            # for now its fine because if we keep shadowform the end calculation is fine
            p_nohave_postmul_given_nohave = hypergeom(deck_size - hand_size, copies, hand_size).cdf(0)
            # not necessary, but it shows the theory
            p_nohave_postmul_given_had = 1
            p_nohave_turn0 = p_nohave_postmul_given_nohave * p_none_premul + (1 - p_none_premul) * p_nohave_postmul_given_had
            return p_nohave_turn0

        def prob_nohave_by_turn(p_none_turn0, turn, copies, hand_size):
            # P(miss_turnN | miss_mul)
            p_none_turnN_given_mulmis = hypergeom(deck_size - hand_size, copies, turn).cdf(0)
            # P(miss_turnN) = P(miss_turnN | miss_mul) P(miss_mul)
            p_none_turnN = p_none_turnN_given_mulmis * p_none_turn0
            return p_none_turnN

        p_no_shadowform_on_turn0 = prob_nohave_card_never_mulled(copies=num_shadowform,
                                                                 hand_size=hand_size)
        no_shadowform_turnN = prob_nohave_by_turn(p_no_shadowform_on_turn0,
                                                  turn, num_shadowform,
                                                  hand_size)

        # Assume you always mul raza
        p_noraza_initial = prob_nohave_card_always_mulled(copies=1, hand_size=hand_size)
        p_noraza_turnN = prob_nohave_by_turn(p_noraza_initial, turn, copies=1,
                                             hand_size=hand_size)
        p_raza_turnN = 1 - p_noraza_turnN

        # probability that you have raza and no shadowform by turn 5
        p_raza_and_noshadowform_turnN = p_raza_turnN * no_shadowform_turnN
        return p_raza_and_noshadowform_turnN

    import plottool as pt  # NOQA
    turns = list(range(0, 26))
    probs = [p_badstuff_shadowform(turn, hand_size=3) for turn in turns]
    pt.plot(turns, probs, label='on play')
    probs = [p_badstuff_shadowform(turn, hand_size=4) for turn in turns]
    pt.plot(turns, probs, label='with coin')
    pt.set_xlabel('turn')
    pt.set_ylabel('probability')
    pt.set_title('Probability of Having Raza without a Shadowform')
    pt.legend()
    pt.gca().set_ylim(0, 1)


def card_combos():
    import plottool as pt  # NOQA
    from scipy.stats import hypergeom

    N = pop_size = 60  # cards in deck  # NOQA
    K = num_success = 4  # number of creatures in deck  # NOQA
    n = sample_size = 7  # cards in opening hand  # NOQA
    nA = 4
    nB = 4
    nLands = 24

    def combo_in_top(n):
        prbA = hypergeom(N, nA, n)
        prbB = hypergeom(N, nB, n)
        prbL = hypergeom(N, nLands, n)

        # cdf is probabiliyt of k or fewer successes
        # prb.cdf(0)

        p_L_eq0 = prbL.cdf(0)
        p_L_le1 = prbL.cdf(1)
        p_L_le4 = prbL.cdf(4)
        # having between 2 to 4 lands
        p_L_ge2_le4 = p_L_le4 - p_L_le1
        p_keepable = p_L_ge2_le4

        # probability of having none
        p_A_eq0 = prbA.cdf(0)
        p_B_eq0 = prbB.cdf(0)
        # probability of having at least 1
        p_A_ge1 = 1 - p_A_eq0
        p_B_ge1 = 1 - p_B_eq0
        # http://math.stackexchange.com/questions/72589/calculating-probability-of-at-least-one-event-occurring

        def p_not_any_fail(p_A_fail, p_B_fail):
            p_and = (1 - p_A_fail) + (1 - p_B_fail) - (1 - p_A_fail * p_B_fail)
            return p_and

        p_and = (1 - p_A_eq0) + (1 - p_B_eq0) - (1 - p_A_eq0 * p_B_eq0)
        p_and = p_A_eq0 * p_B_eq0 - p_A_eq0 - p_B_eq0 + 1

        p_nor = p_A_eq0 * p_B_eq0  # chance_of_neither_combo_card
        p_or = 1 - p_nor  # chance of either card
        p_and = p_A_ge1 + p_B_ge1 - p_or  # chance of both cards
        p_xor = p_or - p_and  # change of either A or B but not both

        print('p_and = %r' % (p_and,))

        p_not_any_fail(1 - p_and, 1 - p_keepable)


def land_stats():
    """
    http://stattrek.com/online-calculator/hypergeometric.aspx

    CommandLine:
        python -m mtgmonte.stats --exec-land_stats --show

    Example:
        >>> # DISABLE_DOCTEST
        >>> from mtgmonte.stats import *  # NOQA
        >>> result = land_stats()
        >>> print(result)
        >>> ut.show_if_requested()
    """
    import plottool as pt
    from scipy.stats import hypergeom
    N = pop_size = 60  # cards in deck  # NOQA
    # K = num_success = 25  # lands in deck  # NOQA
    n = sample_size = 6  # cards seen by coco  # NOQA

    # prob of at least that many hits

    def prob_ge(k, prb):
        return (1 - prb.cdf(k)) + prb.pmf(k)  # P(X >= k)

    pt.ensure_pylab_qt4()

    N = deck_size = 60  # NOQA
    land_range = (24, 27 + 1)

    # N = deck_size = 40  # NOQA
    # land_range = (15, 18 + 1)

    xdata = range(0, 15)  # turn
    ydata_list = [[hypergeom(N, K, x + 7).expect() for x in xdata] for K in range(*land_range)]
    spread_list = [[hypergeom(N, K, x + 7).std() for x in xdata] for K in range(*land_range)]
    # spread_list = None
    import numpy as np
    label_list = ['%d lands' % (K,) for K in range(*land_range)]
    pt.multi_plot(xdata, ydata_list, spread_list=spread_list, label_list=label_list, num_xticks=15, num_yticks=13, fnum=1)
    min_lands_acceptable = np.minimum(np.array(xdata), [1, 2, 3, 4, 5, 6] + [6] * (len(xdata) - 6))
    pt.multi_plot(xdata, [min_lands_acceptable, (np.array(xdata) ** .9) * .5 + 4],
                  label_list=['minimum ok', 'maximum ok'], num_xticks=15, num_yticks=13, fnum=1, marker='o')


def coco_stats():
    """
    http://stattrek.com/online-calculator/hypergeometric.aspx

    CommandLine:
        python -m mtgmonte.stats --exec-coco_stats --show

    Example:
        >>> # DISABLE_DOCTEST
        >>> from mtgmonte.stats import *  # NOQA
        >>> result = coco_stats()
        >>> print(result)
        >>> ut.show_if_requested()
    """
    import plottool as pt
    from scipy.stats import hypergeom
    N = pop_size = 60  # cards in deck  # NOQA
    K = num_success = 21  # number of creatures in deck  # NOQA
    n = sample_size = 6  # cards seen by coco  # NOQA

    # prob of at least that many hits
    hypergeom
    prb = hypergeom(N, K, n)

    k = number_of_success = 1  # number of hits you want  # NOQA

    prb.pmf(k)  # P(X = k)
    #
    prb.cdf(k)  # P(X <= k)

    1 - prb.cdf(k)  # P(X > k)

    (1 - prb.cdf(k)) + prb.pmf(k)  # P(X >= k)

    def prob_ge(k, prb=prb):
        return (1 - prb.cdf(k)) + prb.pmf(k)  # P(X >= k)

    pt.ensure_pylab_qt4()

    import numpy as np

    k = np.arange(1, 3)

    K_list = np.arange(15, 30)

    label_list = [str(K_) + ' creatures in deck' for K_ in K_list]

    ydata_list = [prob_ge(k, prb=hypergeom(N, K_, n)) for K_ in K_list]

    pt.multi_plot(k, ydata_list, label_list=label_list,
                  title='probability of at least k hits with coco', xlabel='k', ylabel='prob',
                  num_xticks=len(k), use_darkbackground=True)


def limited_power_toughness_histogram():
    r"""
    CommandLine:
        python -m mtgmonte.stats --exec-limited_power_toughness_histogram --show

    Example:
        >>> # DISABLE_DOCTEST
        >>> from mtgmonte.stats import *  # NOQA
        >>> result = limited_power_toughness_histogram()
        >>> print(result)
        >>> ut.show_if_requested()
    """
    from mtgmonte import mtgobjs
    from mtglib.gatherer_request import SearchRequest
    from mtglib.card_extractor import CardExtractor
    #from mtglib.card_renderer import CardList
    request = SearchRequest({'set': 'Oath of the Gatewatch'})

    def add_page(url, page):
        parts = url.split('/')
        part1 = '/'.join(parts[:-1])
        part2 = '/Default.aspx?page=%d&' % (page,)
        part3 = parts[-1].replace('Default.aspx?', '')
        url2 =  part1 + part2 + part3
        return url2

    card_list = []
    for page in range(0, 10):
        url = request.url
        url2 = add_page(url, page)
        extract = CardExtractor(url2)
        card_list0 = extract.cards

        for card in card_list0:
            card2 = mtgobjs.Card2()
            card2.__dict__.update(card.__dict__)
            card_list.append(card2)

        if len(card_list0) != 100:
            break

    for c in card_list:
        c.nice_attrs += ['rarity']

    creats = [_card2 for _card2 in card_list if 'Creature' in card2.types]
    creats = [_card2 for _card2 in creats if _card2.rarity in ['Common', 'Uncommon']]

    powtough = []

    for c in creats:
        try:
            powtough.append((int(c.power), int(c.toughness)))
        except ValueError:
            pass

    import plottool as pt
    pt.ensure_pylab_qt4()
    import numpy as np
    scores_list = np.array(list(zip(*powtough)))
    xdata = np.arange(0, np.max(scores_list) + 1)
    powhist = np.histogram(scores_list[0], bins=xdata)[0]
    toughist = np.histogram(scores_list[1], bins=xdata)[0]
    pt.multi_plot(xdata, [powhist, toughist], label_list=['power', 'toughness'], kind='bar')

    bothhist = ut.dict_hist(powtough)
    xdata = np.arange(len(bothhist))
    dat = sorted(bothhist.items())
    xticklabels = ut.take_column(dat, 0)
    ydata = ut.take_column(dat, 1)

    pt.multi_plot(xdata, [ydata], xticklabels=xticklabels, kind='bar')


if __name__ == '__main__':
    r"""
    CommandLine:
        python -m mtgmonte.stats
        python -m mtgmonte.stats --allexamples
    """
    import multiprocessing
    multiprocessing.freeze_support()  # for win32
    import utool as ut  # NOQA
    ut.doctest_funcs()
