# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
import utool as ut


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
