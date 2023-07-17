"""Detector to check if the two distributions are significantly different."""

from abc import ABC
from abc import abstractmethod

from scipy.stats import ks_2samp
import numpy as np

# import torch
from scipy.spatial.distance import jensenshannon
from lib.inspector import convert_dict_to_df


def obtain_raw_samples(summary_dict, representation='binary'):
    """Create raw samples.
    Params:
    - representation (default: 'binary')
        'binary', you get the string representation.
        'natural', you get the natural int representation.
    """
    raw_samples = []
    for value in summary_dict.keys():
        occurrences_of_value = summary_dict[value]
        if representation == 'natural':
            value = int(value, 2)
        raw_samples.extend([value] * occurrences_of_value)

    return raw_samples


def obtain_multivariate_samples(summary_dict):
    """Create raw samples with multivariate representation.

    Note that each outcome is now a sequence of random variable [0,1]
    and not a bit string.
    """
    samples = obtain_raw_samples(summary_dict, representation='binary')
    multivariate_samples = np.vstack([
        np.array([int(x) for x in bin_string])
        for bin_string in samples
    ])
    return multivariate_samples


class Detector(ABC):

    def load_results(self, result_A, result_B):
        self.statistics = None
        self.p_value = None
        self.result_A = result_A
        self.result_B = result_B
        self.samples_A = obtain_raw_samples(result_A)
        self.samples_B = obtain_raw_samples(result_B)

    @abstractmethod
    def check(self, result_A, result_B):
        """Check if the two distributions are significantly different."""
        pass


class KS_Detector(Detector):

    def __init__(self):
        self.name = "Kolmogorov–Smirnov Test"

    def check(self, result_A, result_B, random_seed=None):
        """Compare two distributions with KS Test"""
        self.load_results(result_A, result_B)
        self.statistics, self.p_value = ks_2samp(self.samples_A, self.samples_B)
        return self.statistics, np.float64(self.p_value)


class JS_Detector(Detector):

    def __init__(self):
        self.name = "Jensen–Shannon Distance"

    def check(self, result_A, result_B, random_seed=None):
        """Compare two distributions with JS Distance"""
        df = convert_dict_to_df(
            result_A, result_B, platform_a='A', platform_b='B')
        df = df.pivot(index='name', columns='string', values='counter')
        df = df.fillna(0)
        self.statistics = jensenshannon(p=list(df.loc["A"]), q=list(df.loc["B"]))
        self.p_value = -1
        return self.statistics, np.float64(self.p_value)


class ChiSquare_Detector(Detector):

    def __init__(self):
        self.name = "Chi-Square Test"

    def check(self, result_A, result_B, random_seed=None):
        """Compare two distributions with Chi-Square Test"""
        return 0, 0
        #self.load_results(result_A, result_B)
        #self.statistics, self.p_value = ks_2samp(self.samples_A, self.samples_B)
        #return self.statistics, self.p_value
