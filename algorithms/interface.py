"""Interface for all the algorithms in MSAF."""
import numpy as np
import msaf.input_output as io
import msaf.utils as U


class SegmenterInterface:
    """This class is an interface for all the segmenter algorithms included
    in MSAF. These segmenters must inherit from it and implement the
    process() method.

    Additionally, two private helper functions are provided:
        - preprocess
        - postprocess

    These are meant to do common tasks for all the segmenters and they
    should be called inside the process method if needed.

    All segmenters must return estimates times for the boundaries (est_times),
    and estimated labels (est_labels), **even if they can't compute them**.

    The following three types of algorithms with their behaviors are:
        - Computes boundaries and labels:
            If in_bound_times is None:
                Compute the est_times
            Else:
                Do not compute est_times, simply use in_bound_times instead
            If in_labels is None:
                Compute the est_labels
            Else:
                Do not compute est_labels, simply use in_labels instead

        - Computes boundaries only:
            Compute boundaries and return est_labels as None.

        - Computes labels only:
            Use in_bound_times in order to compute the labels.
            Return est_times as in_bound_times and the computed labels.

    In these cases, est_times or est_labels will be empty (None).
    """
    def __init__(self, audio_file, in_bound_times=None, in_labels=None,
                 feature="hpcp", annot_beats=False, framesync=False, **config):
        """Inits the Segmenter."""
        self.audio_file = audio_file
        self.in_bound_times = in_bound_times
        self.in_labels = in_labels
        self.feature_str = feature
        self.annot_beats = annot_beats
        self.framesync = framesync
        self.config = config

    def process(self):
        """Main process. You must implement it yourself if you want to use
        this interface."""
        raise NotImplementedError("This method must be implemented")

    def _preprocess(self, valid_features=["hpcp", "tonnetz", "mfcc"]):
        """This method obtains the actual features, their frame times,
        and the boundary indeces in these features if needed."""
        # Read features
        hpcp, mfcc, tonnetz, beats, dur, anal = io.get_features(
            self.audio_file, annot_beats=self.annot_beats,
            framesync=self.framesync)

        # Use correct frames to find times
        frame_times = beats
        if self.framesync:
            frame_times = U.get_time_frames(dur, anal)

        # Read input bounds if necessary
        bound_idxs = None
        if self.in_bound_times is not None:
            bound_idxs = io.align_times(self.in_bound_times, frame_times)

        # Use specific feature
        if self.feature_str not in valid_features:
            raise RuntimeError("Feature %s in not valid for algorithm: %s" %
                               (self.feature_str, __name__))
        else:
            if self.feature_str == "hpcp":
                F = U.lognormalize_chroma(hpcp)  # Normalize chromas
            elif "mfcc":
                F = mfcc
            elif "tonnetz":
                F = U.lognormalize_chroma(tonnetz)  # Normalize tonnetz
            else:
                raise RuntimeError("Feature %s in not supported by MSAF" %
                                   (self.feature_str))

        return F, frame_times, dur, bound_idxs

    def _postprocess(self, est_times, est_labels):
        """Post processes the estimations from the algorithm, removing empty
        segments and making sure the lenghts of the boundaries and labels
        match."""
        if self.in_labels is not None:
            est_labels = np.ones(len(est_times) - 1) * -1

        # Remove empty segments if needed
        est_times, est_labels = U.remove_empty_segments(est_times, est_labels)

        assert len(est_times) - 1 == len(est_labels), "Number of boundaries " \
            "(%d) and number of labels(%d) don't match" % (len(est_times),
                                                           len(est_labels))
        return est_times, est_labels
