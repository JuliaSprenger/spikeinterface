Comparison module
=================


SpikeInterface has a :py:mod:`~spikeinterface.comparison` module contains functions and tools to compare 
spike trains and templates (useful for tracking units over multiple sessions).

In addition, the :py:mod:`~spikeinterface.comparison` module contains advanced benchmarking tools to evaluate 
the effects of spike collisions on spike sorting results, and to construct hybrid recordings for comparison.

Spike train comparison
----------------------

For spike train comparison, there are three use cases:

  1. compare a spike sorting output with a ground-truth dataset
  2. compare the output of two spike sorters (symmetric comparison)
  3. compare the output of multiple spike sorters

1. Comparison with ground truth
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A ground-truth dataset can be a paired recording, in which a neuron is recorded both extracellularly and with
a patch or juxtacellular electrode (either **in vitro** or **in vivo**), or it can be a simulated dataset
(**in silico**) using spiking activity simulators such as `MEArec`_.

The comparison to ground-truth datasets is useful to benchmark spike sorting algorithms.

As an example, the SpikeForest platform benchmarks the performance of several spike sorters on a variety of
available ground-truth datasets on a daily basis. For more details see
`spikeforest notes <https://spikeforest.flatironinstitute.org/metrics>`_.


This is the main workflow used to compute performance metrics:

Given:
  * **i = 1, ..., n_gt** the list ground-truth (GT) units
  * **k = 1, ...., n_tested** the list of tested units from spike sorting output
  * **event_counts_GT[i]** the number of spikes for each units of GT unit
  * **event_counts_ST[k]** the number of spikes for each units of tested unit

  1. **Matching firing events**

    For all pairs of GT unit and tested unit we first count how many
    events are matched within a *delta_time* tolerance (0.4 ms by default).

    This gives a matrix called **match_event_count** of size *(n_gt X n_tested)*. This is an example of such matrices:

    .. image:: ../images/spikecomparison_match_count.png
        :scale: 100 %

    Note that this matrix represents the number of **true positive** (TP) spikes
    of each pair. We can also compute the number of **false negatives** (FN) and **false positive** (FP) spikes.

      *  **num_tp** [i, k] = match_event_count[i, k]
      *  **num_fn** [i, k] = event_counts_GT[i] - match_event_count[i, k]
      *  **num_fp** [i, k] = event_counts_ST[k] - match_event_count[i, k]

  2. **Compute agreement score**

    Given the **match_event_count** we can then compute the **agreement_score**, which is normalized in the range [0, 1].

    This is done as follows:

      * agreement_score[i, k] = match_event_count[i, k] / (event_counts_GT[i] + event_counts_ST[k] - match_event_count[i, k])

    which is equivalent to:

      * agreement_score[i, k] = num_tp[i, k] / (num_tp[i, k] + num_fp[i, k] + num_fn[i,k])

    or more practically:

      * agreement_score[i, k] = intersection(I, K) / union(I, K)

    which is also equivalent to the **accuracy** metric.


    Here is an example of the agreement matrix, in which only scores > 0.5 are displayed:

    .. image:: ../images/spikecomparison_agreement_unordered.png
        :scale: 100 %

    This matrix can be ordered for a better visualization:

    .. image:: ../images/spikecomparison_agreement.png
        :scale: 100 %



   3. **Match units**

      During this step, given the **agreement_score** matrix each GT units can be matched to a tested units.
      For matching, a minimum **match_score** is used (0.5 by default). If the agreement is below this threshold,
      the possible match is discarded.

      There are two methods to perform the match: **hungarian** and **best** match.


      The `hungarian method <https://en.wikipedia.org/wiki/Hungarian_algorithm>`_
      finds the best association between GT and tested units. With this method, both GT and tested units can be matched
      only to another unit, or not matched at all.

      For the **best** method, each GT unit is associated to a tested unit that has
      the **best** agreement_score, independently of all others units. Using this method
      several tested units can be associated to the same GT unit. Note that for the "best match" the minimum
      score is not the match_Score, but the **chance_score** (0.1 by default).

      Here is an example of matching with the **hungarian** method. The first column represents the GT unit id
      and the second column the tested unit id. -1 means that the tested unit is not matched:

      .. parsed-literal::

          GT    TESTED
          0     49
          1     -1
          2     26
          3     44
          4     -1
          5     35
          6     -1
          7     -1
          8     42
          ...

      Note that the SpikeForest project uses the **best** match method.


   4. **Compute performances**

      With the list of matched units we can compute performance metrics.
      Given : **tp** the number of true positive events, **fp** number of false
      positive event, **fn** the number of false negative event, **num_gt** the number
      of event of the matched tested units, the following metrics are computed for each GT unit:

        * accuracy = tp / (tp + fn + fp)
        * recall = tp / (tp + fn)
        * precision = tp / (tp + fp)
        * false_discovery_rate = fp / (tp + fp)
        * miss_rate = fn / num_gt

      The overall performances can be visualised with the **confusion matrix**, where
      the last columns counts **FN** and the last row counts **FP**.

    .. image:: ../images/spikecomparison_confusion.png
        :scale: 100 %



More information about **hungarian** or **best** match methods
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


    * **Hungarian**:

      Finds the best paring. If the matrix is square, then all units are associated.
      If the matrix is rectangular, then each row is matched.
      A GT unit (row) can be match one time only.

      * Pros

        * Each spike is counted only once
        * Hit score near chance levels are set to zero
        * Good FP estimation


      * Cons

        * Does not catch units that are split in several sub-units. Only the best math will be listed
        * More complicated implementation

    * **Best**

        Each GT units is associated to the tested unit that has the best **agreement score**.

      * Pros:

        * Each GT unit is matched totally independently from others units
        * The accuracy score of a GT unit is totally independent from other units
        * It can identify over-merged units, as they would match multiple GT units

      * Cons:

        * A tested unit can be matched to multiple GT units, so some spikes can be counted several times
        * FP scores for units associated several times can be biased
        * Less robust with units having high firing rates


Classification of identified units
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Tested units are classified depending on their performance. We identify three different classes:

  * **well-detected** units
  * **false positive** units
  * **redundant** units
  * **over-merged** units

A **well-detected** unit is a unit whose performance is good. By default, a good performance is measured by an accuracy
greater than 0.8-

A **false positive** unit has low agreement scores for all GT units and it is not matched.

A **redundant** unit has a relatively high agreement (>= 0.2 by default), but it is not a best match. This means that
it could either be an oversplit unit or a duplicate unit.

An **over-merged** unit has a relatively high agreement (>= 0.2 by default) for more than one GT unit.


**Example: compare one sorter to ground-truth**

.. code-block:: python

    local_path = download_dataset(remote_path='mearec/mearec_test_10s.h5')
    recording, sorting_true = read_mearec(local_path)


    # run a sorter and compare to ground truth
    sorting_HS = run_sorter('herdingspike', recording)
    cmp_gt_HS = sc.compare_sorter_to_ground_truth(sorting_true, sorting_HS, exhaustive_gt=True)


    # To have an overview of the match we can use the ordered agreement matrix
    plot_agreement_matrix(cmp_gt_HS, ordered=True)

    # This function first matches the ground-truth and spike sorted units, and
    # then it computes several performance metrics: accuracy, recall, precision
    #
    perf = cmp_gt_HS.get_performance()


    # The confusion matrix is also a good summary of the score as it has
    # the same shape as agreement matrix, but it contains an extra column for FN
    # and an extra row for FP
    plot_confusion_matrix(cmp_gt_HS)

    # We can query the well and bad detected units. By default, the threshold
    # on accuracy is 0.95.
    cmp_gt_HS.get_well_detected_units(well_detected_score=0.95)

    cmp_gt_HS.get_false_positive_units(redundant_score=0.2)

    cmp_gt_HS.get_redundant_units(redundant_score=0.2)


**Example: compare many sorters with a Ground Truth Study**

We also have a high level class to compare many sorter against ground truth : 
:py:func:`~spiekinterface.comparison.GroundTruthStudy()`

A study is a systematic performance comparisons several ground truth recordings with several sorters.

The study class  propose high level tools functions to run many groundtruth comparison with many sorter
on many recordings and then collect and aggregate results in an easy way.

The all mechanism is based on an intrinsic organization into a "study_folder" with several subfolder:

  * raw_files : contain a copy in binary format of recordings
  * sorter_folders : contains output of sorters
  * ground_truth : contains a copy of sorting ground  in npz format
  * sortings: contains light copy of all sorting in npz format
  * tables: some table in cvs format

In order to run and rerun the computation all gt_sorting and recordings are copied to a fast and universal format :
binary (for recordings) and npz (for sortings).


.. code-block:: python

    import matplotlib.pyplot as plt
    import seaborn as sns

    import spikeinterface.extractors as se
    import spikeinterface.widgets as sw
    from spikeinterface.comparison import GroundTruthStudy

    # Setup study folder
    rec0, gt_sorting0 = se.toy_example(num_channels=4, duration=10, seed=10, num_segments=1)
    rec1, gt_sorting1 = se.toy_example(num_channels=4, duration=10, seed=0, num_segments=1)
    gt_dict = {
        'rec0': (rec0, gt_sorting0),
        'rec1': (rec1, gt_sorting1),
    }
    study_folder = 'a_study_folder'
    study = GroundTruthStudy.create(study_folder, gt_dict)

    # all sorters on all recordings in one functions.
    sorter_list = ['herdingspikes', 'tridesclous', ]
    study.run_sorters(sorter_list, mode_if_folder_exists="keep")

    # You can re run **run_study_sorters** as many time as you want.
    # By default **mode='keep'** so only uncomputed sorters are rerun.
    # For instance, so just remove the "sorter_folders/rec1/herdingspikes" to re-run
    # only one sorter on one recording.
    #
    # Then we copy the spike sorting outputs into a separate subfolder.
    # This allow to remove the "large" sorter_folders.
    study.copy_sortings()

    # Collect comparisons
    #  
    # You can collect in one shot all results and run the
    # GroundTruthComparison on it.
    # So you can access finely to all individual results.
    #  
    # Note that exhaustive_gt=True when you exactly how many
    # units in ground truth (for synthetic datasets)

    study.run_comparisons(exhaustive_gt=True)

    for (rec_name, sorter_name), comp in study.comparisons.items():
        print('*' * 10)
        print(rec_name, sorter_name)
        # raw counting of tp/fp/...
        print(comp.count_score)
        # summary
        comp.print_summary()
        perf_unit = comp.get_performance(method='by_unit')
        perf_avg = comp.get_performance(method='pooled_with_average')
        # some plots
        m = comp.get_confusion_matrix()
        w_comp = sw.plot_agreement_matrix(comp)

    # Collect synthetic dataframes and display
    # As shown previously, the performance is returned as a pandas dataframe.
    # The :py:func:`~spikeinterface.comparison.aggregate_performances_table()` function,
    # gathers all the outputs in the study folder and merges them in a single dataframe.

    dataframes = study.aggregate_dataframes()

    # Pandas dataframes can be nicely displayed as tables in the notebook.
    print(dataframes.keys())

    # we can also acces to run times
    print(dataframes['run_times'])

    # Easy plot with seaborn
    run_times = dataframes['run_times']
    fig1, ax1 = plt.subplots()
    sns.barplot(data=run_times, x='rec_name', y='run_time', hue='sorter_name', ax=ax1)
    ax1.set_title('Run times')

    ##############################################################################

    perfs = dataframes['perf_by_unit']
    fig2, ax2 = plt.subplots()
    sns.swarmplot(data=perfs, x='sorter_name', y='recall', hue='rec_name', ax=ax2)
    ax2.set_title('Recall')
    ax2.set_ylim(-0.1, 1.1)


.. _symmetric:

2. Compare the output of two spike sorters (symmetric comparison)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The comparison of two sorter is a quite similar to the procedure of **compare to ground truth**.
The difference is that no assumption is done on which is the units are ground-truth.

So the procedure is the following:

  * **Matching firing events** : same a ground truth comparison
  * **Compute agreement score** : same a ground truth comparison
  * **Match units** : only with **hungarian** method

As there is no ground-truth information, performance metrics are not computed.
However, the confusion and agreement matrices can be visualised to assess the level of agreement.

The :py:func:`~spikeinterface.comparison.compare_two_sorters()` return the comparison object to handle this.


**Example: compare 2 sorters**

.. code-block:: python


    # First, let's download a simulated dataset
    local_path = si.download_dataset(remote_path='mearec/mearec_test_10s.h5')
    recording, sorting = se.read_mearec(local_path)

    # Then run two spike sorters and compare their output.
    sorting_HS = ss.run_sorter('herdingspikes', recording)
    sorting_TDC = ss.run_sorter('tridesclous', recording)

    # run the comparison
    # Let’s see how to inspect and access this matching.
    cmp_HS_TDC = sc.compare_two_sorters(
        sorting1=sorting_HS,
        sorting2=sorting_TDC,
        sorting1_name='HS',
        sorting2_name='TDC',
    )

    # We can check the agreement matrix to inspect the matching.
    plot_agreement_matrix(cmp_HS_TDC)

    # Some useful internal dataframes help to check the match and count
    #  like **match_event_count** or **agreement_scores**
    print(cmp_HS_TDC.match_event_count)
    print(cmp_HS_TDC.agreement_scores)

    # In order to check which units were matched, the :code:`get_matching`
    # methods can be used. If units are not matched they are listed as -1.
    sc_to_tdc, tdc_to_sc = cmp_HS_TDC.get_matching()
    print('matching HS to TDC')
    print(sc_to_tdc)
    print('matching TDC to HS')
    print(tdc_to_sc)


.. _multiple:

3. Compare the output of multiple spike sorters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

With 3 or more spike sorters, the comparison is implemented with a graph-based method. The multiple sorter comparison
also allows to clean the output by applying a consensus-based method which only selects spike trains and spikes
in agreement with multiple sorters.

Comparison of multiple sorters uses the following procedure:

  1. Perform pairwise symmetric comparisons between spike sorters
  2. Construct a graph in which nodes are units and edges are the agreements between units (of different sorters)
  3. Extract units in agreement between two or more spike sorters
  4. Build agreement spike trains, which only contain the spikes in agreement for the comparison with the
     highest agreement score


**Example: compare many sorters**

.. code-block:: python

    # download a simulated dataset
    local_path = si.download_dataset(remote_path='mearec/mearec_test_10s.h5')
    recording, sorting = se.read_mearec(local_path)

    # Then run 3 spike sorters and compare their output.
    sorting_MS4 = ss.run_sorter('mountainsort4', recording)
    sorting_HS = ss.run_sorter('herdingspikes', recording)
    sorting_TDC = ss.run_sorter('tridesclous', recording)

    # Compare multiple spike sorter outputs
    mcmp = sc.compare_multiple_sorters(
        sorting_list=[sorting_MS4, sorting_HS, sorting_TDC],
        name_list=['MS4', 'HS', 'TDC'],
        verbose=True,
    )

    # The multiple sorters comparison internally computes pairwise comparison,
    # that can be accessed as follows:
    print(mcmp.comparisons[('MS4', 'HS')].sorting1, mcmp.comparisons[('MS4', 'HS')].sorting2)
    print(mcmp.comparisons[('MS4', 'HS')].get_matching())

    print(mcmp.comparisons[('MS4', 'TDC')].sorting1, mcmp.comparisons[('MS4', 'TDC')].sorting2)
    print(mcmp.comparisons[('MS4', 'TDC')].get_matching())

    # The global multi comparison can be visualized with this graph
    sw.plot_multicomp_graph(mcmp)

    # Consensus-based method
    #  
    # We can pull the units in agreement with different sorters using the
    # :py:func:`~spikeinterface.comparison.MultiSortingComparison.get_agreement_sorting` method.
    # This allows to make spike sorting more robust by integrating the output of several algorithms.
    # On the other hand, it might suffer from weak performance of single algorithms.
    # When extracting the units in agreement, the spike trains are modified so
    # that only the true positive spikes between the comparison with the best
    # match are used.

    agr_3 = mcmp.get_agreement_sorting(minimum_agreement_count=3)
    print('Units in agreement for all three sorters: ', agr_3.get_unit_ids())

    agr_2 = mcmp.get_agreement_sorting(minimum_agreement_count=2)
    print('Units in agreement for at least two sorters: ', agr_2.get_unit_ids())

    agr_all = mcmp.get_agreement_sorting()

    # The unit index of the different sorters can also be retrieved from the
    # agreement sorting object (:code:`agr_3`) property :code:`sorter_unit_ids`.

    print(agr_3.get_property('unit_ids'))

    print(agr_3.get_unit_ids())
    # take one unit in agreement
    unit_id0 = agr_3.get_unit_ids()[0]
    sorter_unit_ids = agr_3.get_property('unit_ids')[0]
    print(unit_id0, ':', sorter_unit_ids)


Template comparison
-------------------

For template comparisons, the underlying ideaa are very similar to :ref:`symmetric` and :ref:`multiple`, for 
pairwise and multiple comparisons, respectively. Differently than spike trains comparisons, however, in this case the 
agreement is not the matching of spiking events, but rather the similarity between templates. 
This enables us to use exatly the same tools for both types of comparisons, just by changing the way that agreement 
scores are computed.

The functions to compare templates take a list of :py:class:`~spikeinterface.core.WaveformExtractor` objects as input, 
which are assumed to be from different sessions of the same animal over time. In this case, let's assume we have 5 
waveform extractors from day 1 (:code:`we_day1`) to day 5 (:code:`we_day5`):

.. code-block:: python

    we_list = [we_day1, we_day2, we_day3, we_day4, we_day5]

    # match only day 1 and 2
    p_tcmp = sc.compare_templates(we_day1, we_day2, we1_name="Day1", we2_name="Day2")

    # match all
    m_tcmp = sc.compare_multiple_templates(we_list, 
                                           name_list=["D1", "D2", "D3", "D4", "D5"])
    


Benchmark spike collisions
--------------------------

SpikeInterface also have a specific toolset to benchmark how good sorter are to recover spikes in "collision".

We have three classes to handle collision-specific comparisons, and also to quantify the effects on correlogram 
estimation: 

  * :py:class:`~spikeinterface.comparison.CollisionGTComparison`
  * :py:class:`~spikeinterface.comparison.CorrelogramGTComparison`
  * :py:class:`~spikeinterface.comparison.CollisionGTStudy`
  * :py:class:`~spikeinterface.comparison.CorrelogramGTStudy`

For more details, checkout the following paper:

`Samuel Garcia, Alessio P. Buccino and Pierre Yger. "How Do Spike Collisions Affect Spike Sorting Performance?" <https://doi.org/10.1523/ENEURO.0105-22.2022>`_


Hybrid recording
----------------

To benchmark spike sorting results, we need ground-truth spiking activity.
This can be generated with artificial simulations, e.g., using `MEArec <https://mearec.readthedocs.io/>`_, or 
alternatively by generating so-called "hybrid" recordings.

The :py:mod:`~spikeinterface.comparison` module includes functions to generate such "hybrid" recordings:

  * :py:func:`~spikeinterface.comparison.create_hybrid_units_recording`: add new units to an existing recording
  * :py:func:`~spikeinterface.comparison.create_hybrid_spikes_recording`: add new spikes to existing units in a recording
