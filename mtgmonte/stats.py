

def coco_stats():
    """
    http://stattrek.com/online-calculator/hypergeometric.aspx
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
