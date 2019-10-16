"""Mimic Calibration of predicted probabilities."""
# Author: Pin-Ju Tien <pinju.tien@gmail.com>
# ref: NYC ML Meetup talk given by Sam Steingold.
# https://www.youtube.com/watch?v=Cg--SC76I1I
# Acknowledgements: Special thanks to Ritesh Bansal for
# the encouragment and support throughout the project.

import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.utils import indexable, column_or_1d
from sklearn.utils.validation import check_is_fitted
import sys


class _MimicCalibration(BaseEstimator, RegressorMixin):
    """ mimic calibration:
    A method to calibrate probability of binary classification model.
    """
    def __init__(self, threshold_pos=5, record_history=False):
        """
        Parameters
        ----------
        threshold_pos: int
            the number of positive at each bin at initial binning step.
        record_history: bool
            to record the merging bin process.
        """
        self.threshold_pos = threshold_pos
        self.boundary_choice = 2
        self.record_history = record_history
        self.history_record_table = []

    def get_bin_boundary(self, current_binning, boundary_choice):
        """
        Parameters
        ----------
        current_binning: array-like, shape (num_bins, 7)
        [[bl_index, score_min, score_max, score_mean,
          nPos_temp, total_temp, PosRate_temp]]

        boundary_choice: int
            0: choose socre_min, ie left boundary of bin
            1: choose socre_max, ie right boundary of bin
            2: choose socre_mean, ie mean score of bin

        Returns
        ----------
        boundary_table: array-like, shape (num_bins, 1)

        """
        num_rows = len(current_binning)
        boundary_table_temp = []
        k = None
        if (boundary_choice == 0):
            k = 1
        elif (boundary_choice == 1):
            k = 2
        elif (boundary_choice == 2):
            k = 3
        else:
            raise Exception("Un-identified boundary choice: {x}"
                            .format(x=boundary_choice))
        for i in range(num_rows):
            boundary_table_temp += [current_binning[i][k]]
        return boundary_table_temp

    def construct_initial_bin(self,
                              sorted_score,
                              sorted_target,
                              threshold_pos):
        """make each bin having the number of positives equal to
        threshold_pos.the default = 5.

        Parameters
        ----------
        sorted_score: the sorted probability from the model,
                      ie pre-calibrated score.
        sorted target: the target in the order of increasing score.
                       the number of target = 2.
        threshold_pos: number of positive in each bin, default=5

        Returns
        ----------
        bin_info: 2-D array, shape (number of bins, 6).
            [[bl_index, score_min, score_max, score_mean,
              nPos_temp, total_temp, nPosRate_temp]]
        total_number_pos: integer
            number of positive.
        """
        bin_right_index_array = []
        last_index = len(sorted_target)-1
        count = 0
        # make each bin having number of positive = threshold positive.
        # bin_right_index_array: right-boundary index of each bin.
        for i in range(len(sorted_target)):
            y = sorted_target[i]
            if y > 0:
                count += 1
            if (count == threshold_pos):
                bin_right_index_array += [i]
                count = 0
        if (len(sorted_target)-1 not in bin_right_index_array):
            bin_right_index_array += [last_index]

        # bl_index: left boundary index of each bin.
        bl_index = 0
        bin_info = []
        total_number_pos = 0
        for br_index in bin_right_index_array:
            # score stats
            score_temp = sorted_score[bl_index: br_index + 1]
            score_min = min(score_temp)
            score_max = max(score_temp)
            score_mean = np.mean(score_temp)
            # target
            target_row = sorted_target[bl_index: br_index + 1]
            nPos_temp = np.sum(target_row)
            if (br_index != last_index):
                assert (nPos_temp == threshold_pos),\
                    "The sum of positive must be equal to threshold pos \
                    except the last index."
            total_number_per_bin = len(target_row)
            nPosRate_temp = 1.0*nPos_temp/total_number_per_bin
            bin_info += [[bl_index, score_min, score_max, score_mean,
                          nPos_temp, total_number_per_bin, nPosRate_temp]]
            total_number_pos += nPos_temp
            bl_index = br_index + 1
        return bin_info, total_number_pos

    def merge_bins(self, binning_input, increasing_flag):
        """
        Parameters
        ----------
        binning_input: array-like, shape (number of bins, 7)
            [[bl_index, score_min, score_max,
              score_mean, nPos_temp, total_temp, PosRate_temp]]
        increasing_flag: bool

        Returns
        ----------
        result: array-like, shape (number of bins, 7)
            It merge bins to make sure the positive at each bin increasing.
        increasing_flag: bool
        """
        # binning_input
        # [[bl_index, score_min, score_max,
        #   score_mean, nPos_temp, total_temp, PosRate_temp]]
        nbins = len(binning_input)
        result = []
        for i in range(1, nbins):
            # current_bin: latest new bin in the result
            if (i == 1):
                result += [binning_input[0]]
            current_bin = result[-1]
            current_bin_PosRate = current_bin[-1]
            next_bin = binning_input[i]
            next_bin_PosRate = next_bin[-1]
            if(current_bin_PosRate > next_bin_PosRate):
                increasing_flag = False
                # merge two bins:
                # [[bl_index, score_min, score_max, score_mean,
                #   nPos_temp, total_temp, PosRate_temp]]
                new_bin_index_temp = min(current_bin[0], next_bin[0])
                new_score_min_temp = min(current_bin[1], next_bin[1])
                new_score_max_temp = max(current_bin[2], next_bin[2])
                new_score_mean_temp = (current_bin[3] + next_bin[3])/2.0
                new_pos_temp = current_bin[4] + next_bin[4]
                new_total_temp = current_bin[5] + next_bin[5]
                new_PosRate_temp = 1.0*new_pos_temp/new_total_temp
                # update the latest bin info in the latest result
                result[-1] = [new_bin_index_temp, new_score_min_temp,
                              new_score_max_temp, new_score_mean_temp,
                              new_pos_temp, new_total_temp, new_PosRate_temp]
            else:
                result += [next_bin]
        return result, increasing_flag

    def run_merge_function(self, current_binning, record_history=False):
        """ It keep merging bins together until
        the positive rate at each bin increasing.

        Parameters
        ----------
        current_binning: array-like, shape (number of bins, 7)
            [[bl_index, score_min, score_max,
              score_mean, nPos_temp, total_temp, PosRate_temp]]
        record_history: bool

        Returns
        ----------
        result: array-like, shape (number of bins, 7)
            it return the final binning result.
        """

        # current_binning
        # [[bl_index, score_min, score_max, score_mean,
        # nPos_temp, total_temp, PosRate_temp]]
        self.history_record_table = []
        if (record_history):
            self.history_record_table += [current_binning]

        keep_merge = True
        while(keep_merge):
            new_bin_temp, increasing_flag = self.merge_bins(current_binning,
                                                            True)
            if (record_history):
                self.history_record_table += [new_bin_temp]

            # update the current_binning
            current_binning = new_bin_temp
            # if it increasing monotonically, we stop merge
            keep_merge = not increasing_flag
        # if (record_history):
        #     return self.history_record_table
        return [new_bin_temp]

    def _mimic_calibration(self,
                           y_score,
                           y_target,
                           number_positive_within_bin=5):
        """Perform mimic calibration.

        Parameters
        ----------
        y_score: array-like, shape (number of row, 1)
            the probability prediction from binary model.
        y_target: array-like, shape (number of row, 1)
            the element of this array is 0 or 1.
        number_positive_within_bin: int
            number of positive in the initial binning.

        Returns
        -------
        boundary_table: array-like, shape (number of bin, 1)
            a seris of boundary of each bin.
        calibrated_model: array-like, shape (number of bins, 7).
            [bl_index, score_min, score_max, score_mean,
             nPos, total_num, PosRate]
        """
        assert ((y_score.min() >= 0) & (y_score.max() <= 1.0)), \
            "y_score is a probability which is between 0 and 1."
        # assert (len(np.unique(y_score)) > 2), \
        #     "y_score should be at least 3 different probability."
        assert np.array_equal(np.unique(y_target), np.array([0, 1])), \
            "y_traget must be 0 and 1."
        if (len(np.unique(y_score)) <= 2):
            print("[WARNING]: the unique number of probabilities is\
            less or equal than 2. {x}".format(x=np.unique(y_score)))
        y_score = column_or_1d(y_score)
        y_target = column_or_1d(y_target)
        # sort y_score
        sorted_index = y_score.argsort()
        y_score = y_score[sorted_index]
        y_target = y_target[sorted_index]
        threshold_pos = number_positive_within_bin
        # initial binning
        initial_binning, total_number_pos = self.construct_initial_bin(
            y_score,
            y_target,
            threshold_pos)
        # start to merge bin
        final_binning = self.run_merge_function(initial_binning,
                                                self.record_history)
        calibrated_model = final_binning[-1]
        boundary_table = self.get_bin_boundary(calibrated_model,
                                               self.boundary_choice)
        return boundary_table, calibrated_model

    def fit(self, X, y, sample_weight=None):
        """ perform mimic calibration.

        Parameters
        ----------
        X: array-like, shape (number of row, 1)
            the probability from the binary model.
        y: array-like, shape (number of row, 1)
            binary target, its element is 0 or 1.

        Returns
        -------
        self : object
            Returns an instance of self.
        """
        X = column_or_1d(X)
        y = column_or_1d(y)
        X, y = indexable(X, y)
        self.boundary_table, self.calibrated_model = self._mimic_calibration(
            X,
            y,
            self.threshold_pos)
        return self

    def predict(self, pre_calib_prob):
        """ prediction function of mimic calibration.
        It returns 1-d array, calibrated probability using mimic calibration.

        Parameters
        ----------
        pre_calib_prob: array-like
            the probability prediction from the binary model.

        Returns
        -------
        calib_prob : array-like
            the mimic-calibrated probability.
        """
        pre_calib_prob = column_or_1d(pre_calib_prob)
        # check_is_fitted(self, "calibrated_model")

        boundary_table = [cali[3] for cali in self.calibrated_model]
        x_start = np.array([0] + boundary_table)
        x_end = np.array(boundary_table + [1])

        calibration_table = [cali[6] for cali in self.calibrated_model]
        y_start = np.array([calibration_table[0]] + calibration_table)
        y_end = np.array(calibration_table + [calibration_table[-1]])

        bin_idx = np.digitize(pre_calib_prob, boundary_table, right=True)
        x_start = x_start[bin_idx]
        x_end = x_end[bin_idx]
        y_start = y_start[bin_idx]
        y_end = y_end[bin_idx]

        calib_prob = (pre_calib_prob - x_start) / (x_end - x_start) *\
                     (y_end - y_start) + y_start

        return calib_prob

    def get_one_history(self, one_history):
        score_array = []
        nP_array = []
        for row in one_history:
            # the mean of score at each bin
            score = row[3]
            # the nPos rate at each bin
            nP = row[6]
            score_array += [score]
            nP_array += [nP]
        return score_array, nP_array

    def output_history_result(self, show_history_array=[]):
        """ Output merging history.
        Parameters
        ----------
        show_history_array: array-like
            given history index.

        Returns
        -------
        score-posRate-array : array-like
            [[score_array, nPosRate_array, i]]
        """
        # import matplotlib.pyplot as plt
        # fig = plt.figure()
        data = None
        if (self.record_history):
            data = self.history_record_table
        else:
            data = self.calibrated_model

        number_of_history = len(data)
        print("plot history size: {x}".format(x=number_of_history))
        if (len(show_history_array) == 0):
            show_history_array = range(number_of_history)

        assert(max(show_history_array) <= number_of_history-1), \
            "The max of history index is {x}. \
            Please choose indexs between 0 and {x}"\
            .format(x=number_of_history-1)
        result = []
        for i in show_history_array:
            one_history = data[i]
            score_array, nPosRate_array = self.get_one_history(one_history)
            result += [[score_array, nPosRate_array, i]]
            # plt.plot(score_array, nPosRate_array, label=str(i))
        # plt.xlabel("pre calibrated prob", fontsize=18)
        # plt.ylabel("mimic calibrated prob", fontsize=18)
        # plt.legend()
        # fig.savefig('merging_bins_history.png')
        # plt.show()
        return result
