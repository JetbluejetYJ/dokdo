import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.stats import spearmanr, pearsonr
import statsmodels.stats.multitest as multi
from qiime2 import Artifact, Metadata

def cross_association_table(
    artifact, target, method='spearman', normalize=None, alpha=0.05,
    multitest='fdr_bh', nsig=0
):
    """
    Compute cross-correlatation between feature table and target matrices.

    This method is essentially equivalent to the :meth:`associate` `function
    <https://rdrr.io/github/microbiome/microbiome/man/associate.html>`__
    from the ``microbiome`` R package.

    Parameters
    ----------
    artifact : str, qiime2.Artifact, or pandas.DataFrame
        Feature table. This can be an QIIME 2 artifact file or object with
        the semantic type ``FeatureTable[Frequency]``. If you are importing
        data from an external tool, you can also provide a
        :class:`pandas.DataFrame` object where rows indicate samples and
        columns indicate taxa.
    target : pandas.DataFrame
        Target :class:`pandas.DataFrame` object to be used for
        cross-correlation analysis.
    method : {'spearman', 'pearson'}, default: 'spearman'
        Association method.
    normalize : {None, 'log10', 'clr', 'zscore'}, default: None
        Whether to normalize the feature table:

        - None: Do not normalize.
        - 'log10': Apply the log10 transformation after adding a psuedocount
          of 1.
        - 'clr': Apply the centre log ratio (CLR) transformation adding a
          psuedocount of 1.
        - 'zscore': Apply the Z score transformation.
    alpha : float, default: 0.05
        FWER, family-wise error rate.
    multitest : str, default: 'fdr_bh'
        Method used for testing and adjustment of p values, as defined in
        :meth:`statsmodels.stats.multitest.multipletests`.
    nsig : int, default: 0
        Mininum number of significant correlations for each element.

    Returns
    -------
    pandas.DataFrame
        Cross-association table.

    See Also
    --------
    dokdo.api.cross_association.cross_association_heatmap
    dokdo.api.cross_association.cross_association_regplot

    Examples
    --------

    Below example is taken from a `tutorial <https://microbiome.github.io/
    tutorials/Heatmap.html>`__ by Leo Lahti and Sudarshan Shetty et al.

    .. code:: python3

        import pandas as pd
        import dokdo
        otu = pd.read_csv('/Users/sbslee/Desktop/dokdo/data/miscellaneous/otu.csv', index_col=0)
        lipids = pd.read_csv('/Users/sbslee/Desktop/dokdo/data/miscellaneous/lipids.csv', index_col=0)
        df = dokdo.cross_association_table(
            otu, lipids, normalize='log10', nsig=1
        )
        df.head(10)
        # Will print:
        #                              taxon      target      corr          pval      adjp
        # 0      Ruminococcus gnavus et rel.  TG(54:5).2  0.716496  4.516954e-08  0.002284
        # 1         Uncultured Bacteroidetes  TG(56:2).1 -0.698738  1.330755e-07  0.002345
        # 2                    Moraxellaceae   PC(40:3e) -0.694186  1.733720e-07  0.002345
        # 3      Ruminococcus gnavus et rel.    TG(50:4)  0.691191  2.058030e-07  0.002345
        # 4  Lactobacillus plantarum et rel.    PC(40:3) -0.687798  2.493210e-07  0.002345
        # 5      Ruminococcus gnavus et rel.  TG(54:6).1  0.683580  3.153275e-07  0.002345
        # 6      Ruminococcus gnavus et rel.  TG(54:4).2  0.682030  3.434292e-07  0.002345
        # 7      Ruminococcus gnavus et rel.    TG(52:5)  0.680622  3.709485e-07  0.002345
        # 8                     Helicobacter    PC(40:3) -0.673201  5.530595e-07  0.003108
        # 9                    Moraxellaceae  PC(38:4).1 -0.670050  6.530463e-07  0.003302
    """
    if isinstance(artifact, Artifact):
        feats = artifact.view(pd.DataFrame)
    elif isinstance(artifact, str):
        feats = Artifact.load(artifact).view(pd.DataFrame)
    elif isinstance(artifact, pd.DataFrame):
        feats = artifact.copy()
    else:
        raise TypeError(f"Incorrect feature table type: {type(artifact)}")

    if normalize == 'log10':
        feats = feats.applymap(lambda x: np.log10(x + 1))
    elif normalize == 'clr':
        feats = feats.apply(lambda x: clr(x + 1), axis=1,
            result_type='broadcast')
    elif normalize == 'zscore':
        feats = feats.apply(zscore, axis=1,
            result_type='broadcast')
    elif not normalize:
        pass
    else:
        raise ValueError(f"Incorrect normalization method: '{normalize}'")

    methods = {'pearson': pearsonr, 'spearman': spearmanr}

    corr = np.zeros((feats.shape[1], target.shape[1]))
    pval = np.zeros((feats.shape[1], target.shape[1]))

    for i in range(feats.shape[1]):
        for j in range(target.shape[1]):
            results = methods[method](feats[feats.columns[i]],
                target[target.columns[j]])
            corr[i, j] = results[0]
            pval[i, j] = results[1]

    corr = pd.DataFrame(corr, columns=target.columns, index=feats.columns)
    pval = pd.DataFrame(pval, columns=target.columns, index=feats.columns)

    corr = corr.melt(var_name='target', value_name='corr', ignore_index=False)
    pval = pval.melt(var_name='target', value_name='pval', ignore_index=False)

    df = pd.concat([corr, pval['pval']], axis=1)
    df.index.name = 'taxon'
    df = df.reset_index()
    df['adjp'] = multi.multipletests(df['pval'], method=multitest)[1]

    if nsig:
        adjp = df.pivot(index='taxon', columns='target', values='adjp')
        sig = adjp <= alpha
        s = sig.sum(axis=1)
        taxon_survivors = s[s >= nsig].index.to_list()
        s = sig.sum(axis=0)
        target_survivors = s[s >= nsig].index.to_list()
        df = df[df['taxon'].isin(taxon_survivors)]
        df = df[df['target'].isin(target_survivors)]

    df = df.sort_values('pval')
    df = df.reset_index(drop=True)

    return df

def cross_association_heatmap(
    artifact, target, method='spearman', normalize=None, alpha=0.05,
    multitest='fdr_bh', nsig=0, marksig=False, figsize=None, cmap=None,
    **kwargs
):
    """
    Create a heatmap showing cross-correlatation between feature table and
    target matrices.

    Parameters
    ----------
    artifact : str, qiime2.Artifact, or pandas.DataFrame
        Feature table. This can be an QIIME 2 artifact file or object with
        the semantic type ``FeatureTable[Frequency]``. If you are importing
        data from an external tool, you can also provide a
        :class:`pandas.DataFrame` object where rows indicate samples and
        columns indicate taxa.
    target : pandas.DataFrame
        Target :class:`pandas.DataFrame` object to be used for
        cross-correlation analysis.
    method : {'spearman', 'pearson'}, default: 'spearman'
        Association method.
    normalize : {None, 'log10', 'clr', 'zscore'}, default: None
        Whether to normalize the feature table:

        - None: Do not normalize.
        - 'log10': Apply the log10 transformation after adding a psuedocount
          of 1.
        - 'clr': Apply the centre log ratio (CLR) transformation adding a
          psuedocount of 1.
        - 'zscore': Apply the Z score transformation.
    alpha : float, default: 0.05
        FWER, family-wise error rate.
    multitest : str, default: 'fdr_bh'
        Method used for testing and adjustment of p values, as defined in
        :meth:`statsmodels.stats.multitest.multipletests`.
    nsig : int, default: 0
        Mininum number of significant correlations for each element.
    marksig : bool, default: False
        If True, mark statistically significant associations with asterisk.
    figsize : tuple, optional
        Width, height in inches. Format: (float, float).
    cmap : str, optional
        Name of the colormap passed to :meth:`matplotlib.cm.get_cmap()`.
    kwargs : other keyword arguments
        All other keyword arguments are passed to :meth:`seaborn.clustermap`.

    Returns
    -------
    seaborn.matrix.ClusterGrid
        A ClusterGrid instance.

    See Also
    --------
    dokdo.api.cross_association.cross_association_table
    dokdo.api.cross_association.cross_association_regplot

    Examples
    --------

    Below example is taken from a `tutorial <https://microbiome.github.io/
    tutorials/Heatmap.html>`__ by Leo Lahti and Sudarshan Shetty et al.

    .. code:: python3

        import dokdo
        import matplotlib.pyplot as plt
        %matplotlib inline
        import pandas as pd

        otu = pd.read_csv('/Users/sbslee/Desktop/dokdo/data/miscellaneous/otu.csv', index_col=0)
        lipids = pd.read_csv('/Users/sbslee/Desktop/dokdo/data/miscellaneous/lipids.csv', index_col=0)
        dokdo.cross_association_heatmap(
           otu, lipids, normalize='log10', nsig=1,
           figsize=(15, 15), cmap='vlag', marksig=True,
           annot_kws={'fontsize': 6, 'ha': 'center', 'va': 'center'}
        )

    .. image:: images/cross_association_heatmap_1.png
    """
    df = cross_association_table(
        artifact, target, method=method, normalize=normalize, alpha=alpha,
        multitest=multitest, nsig=nsig
    )

    corr = df.pivot(index='target', columns='taxon', values='corr')

    if marksig:
        pval = df.pivot(index='target', columns='taxon', values='pval')
        def val2sig(x):
            if x <= alpha:
                return '*'
            return ''
        annot = pval.applymap(val2sig)
        fmt = ''
    else:
        annot = None
        fmt = '.2g'

    g = sns.clustermap(
        corr, figsize=figsize, cmap=cmap, annot=annot, fmt=fmt, **kwargs
    )

    ax = g.ax_heatmap
    ax.set_xlabel('')
    ax.set_ylabel('')

    return g

def cross_association_regplot(
    artifact, target, taxon, name, ax=None, figsize=None
):
    """
    Create a scatter plot showing the cross-correlatation of a specific pair
    between feature table and target matrices.

    Parameters
    ----------
    artifact : str, qiime2.Artifact, or pandas.DataFrame
        Feature table. This can be an QIIME 2 artifact file or object with
        the semantic type ``FeatureTable[Frequency]``. If you are importing
        data from an external tool, you can also provide a
        :class:`pandas.DataFrame` object where rows indicate samples and
        columns indicate taxa.
    target : pandas.DataFrame
        Target :class:`pandas.DataFrame` object to be used for
        cross-correlation analysis.
    taxon : str
        Taxon in feature table.
    name : str
        Target name.
    ax : matplotlib.axes.Axes, optional
        Axes object to draw the plot onto, otherwise uses the current Axes.
    figsize : tuple, optional
        Width, height in inches. Format: (float, float).

    Returns
    -------
    matplotlib.axes.Axes
        Axes object with the plot drawn onto it.

    See Also
    --------
    dokdo.api.cross_association.cross_association_table
    dokdo.api.cross_association.cross_association_heatmap

    Examples
    --------

    .. code:: python3

        import dokdo
        import matplotlib.pyplot as plt
        %matplotlib inline
        import pandas as pd

        otu = pd.read_csv('/Users/sbslee/Desktop/dokdo/data/miscellaneous/otu.csv', index_col=0)
        lipids = pd.read_csv('/Users/sbslee/Desktop/dokdo/data/miscellaneous/lipids.csv', index_col=0)
        dokdo.cross_association_regplot(otu, lipids, 'Ruminococcus gnavus et rel.', 'TG(54:5).2')
        plt.tight_layout()

    .. image:: images/cross_association_regplot.png
    """
    df = pd.concat([artifact[taxon], target[name]], axis=1)

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)

    sns.regplot(data=df, x=taxon, y=name, ax=ax)

    return ax
