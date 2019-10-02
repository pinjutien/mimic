.. -*- mode: rst -*-

|Travis|_ |AppVeyor|_ |CircleCI|_ |ReadTheDocs|_ |Codecov|_

.. |Travis| image:: https://travis-ci.org/scikit-learn-contrib/mimic.svg?branch=master
.. _Travis: https://travis-ci.org/scikit-learn-contrib/mimic

.. |AppVeyor| image:: https://ci.appveyor.com/api/projects/status/l27hftp120wehpai?svg=true
.. _AppVeyor: https://ci.appveyor.com/project/pinjutien/mimic

.. |CircleCI| image:: https://circleci.com/gh/scikit-learn-contrib/mimic.svg?style=shield&circle-token=:circle-token
.. _CircleCI: https://circleci.com/gh/scikit-learn-contrib/mimic/tree/master

.. |ReadTheDocs| image:: https://readthedocs.org/projects/sklearn-mimic/badge/?version=latest
.. _ReadTheDocs: https://sklearn-mimic.readthedocs.io/en/latest/?badge=latest

.. |Codecov| image:: https://codecov.io/gh/scikit-learn-contrib/mimic/branches/master/graph/badge.svg
.. _Codecov: https://codecov.io/gh/scikit-learn-contrib/mimic/

mimic calibration
==================================================

Introduction
------------
mimic calibration is a calibration method for binary classification model.
This method was presented at NYC ML Meetup talk given by Sam Steingold, see [*]_.


Implementation
---------------
It requires two inputs, the probability prediction from binary classification model and the binary target (0 and 1).                                                                                                  
Here is how it is implemented

1. Sort the probabitliy in the ascending. Merge neighbor data points into
   one bin until the number of positive equal to threshold positive at each bin.
   In this initial binning, only the last bin may have number of positive less than threshold positive.
2. Calculate the number of positive rate at each bin. Merge neighbor two bins
   if nPos rate in the left bin is greater than right bin.
3. Keep step 2. until the nPos rate in the increasing order.
4. In this step, we have information at each bin, such as nPos rate, the avg/min/max probability.
   we record those informations in two places. One is ``boundary_table``. The other is ``calibrated_model``.
   ``boundary_table``: it records probability at each bin. The default is recording the avg prob of bin.
   ``calibrated_model``: it records all the information of bin, such nPos rate, the avg/min/max probability.
5. The final step is linear interpolation.

Install:
---------------
  pip install -i https://test.pypi.org/simple/ mimiccalib==0.0.2
   
Parameters:
---------------
>>> _MimicCalibration(threshold_pos, record_history)

* threshold_pos: the number of positive in the initial binning. default = 5.
* record_history: boolean parameter, decide if record all the mergeing of bin history. default = False.

Usage
---------------

>>> from mimic import _MimicCalibration
>>> mimicObject = _MimicCalibration(threshold_pos=5, record_history=True)
>>> # y_calib_score: probability prediction from binary classification model
>>> # y_calib: the binary target, 0 or 1.
>>> mimicObject.fit(y_calib_score, y_calib)
>>> y_mimic_calib_score = mimicObject.predict(y_calib_score)

Results: calibration evaluation.
------------------------------------------------------------
- calibration curve and brier score.
  In our testing examples, mimic and isotonic have very similar brier score.
  But, as number of bins increase in calibration curve, mimic calibration has more smooth behavior.
  It is because the calibrated probability of mimic has more continuous prediction space compared to
  isotonic calibration which is step function.
  In the following plot, brier scores are 0.1028 (mimic) and 0.1027 (isotonic).


>>> calibration_curve(y_test, y_output_score, n_bins=10)

.. image:: https://github.com/pinjutien/mimic/blob/master/data/evaluation_calib_1.png

>>> calibration_curve(y_test, y_output_score, n_bins=20)

.. image:: https://github.com/pinjutien/mimic/blob/master/data/evaluation_calib_2.png

   
The above behavior is similar in the followings cases.
1. base model = GaussianNB, LinearSVC
2. positive rate in the data = 0.5, 0.2

Comparison :mimic, isotonic and platt calibration.
------------------------------------------------------------
.. image:: https://github.com/pinjutien/mimic/blob/master/data/mimic_calib_prob.png
   :width: 40pt
   
History of merging bins.
------------------------------------------------------------
.. image:: https://github.com/pinjutien/mimic/blob/master/data/merging_bins_history.png
   :width: 40pt
   
Run test
------------------------------------------------------------
>>> pytest -v --cov=mimic --pyargs mimic


Reference
----------
.. [*] https://www.youtube.com/watch?v=Cg--SC76I1I
