__author__ = 'antonio'

import logging

import numpy as np
from ethoscope.core.variables import CoreMovement, PeripheryMovement
from ethoscope.trackers.adaptive_bg_tracker import AdaptiveBGModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class RichAdaptiveBGModel(AdaptiveBGModel):
    """
    Extract extra behavioral features inspired by
    https://elifesciences.org/articles/34497
    These features are:
      (1) periphery movement (PM), which characterizes movements of the legs, head and wings.
      (2) core movement (CM), which quantifies movements of the thorax and abdomen.
      (3) centroid displacement (CD), which quantifies whole body displacement.

      (3) Is implemented in the AdaptiveBGModel class as the XYDistance instance,
      however (1) and (2) are not and could potentially be very useful to distinguish
      micromovements like grooming. See figure 1.E from https://science.sciencemag.org/content/367/6476/440
      for a similar implementation of the same ideas.

      Distinguishing between stillness and micromovements holds the potential power to
      better estimate sleep by not overestimating it,
      thus leading to more accurate behavioral monitoring and thus
      a more accurate representation of the biological phenomena.
    """

    _body_parts = ("core", "periphery")
    _description = {
        "overview": "An extended tracker for fruit flies. One animal per ROI.",
        "arguments": []
    }


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fly_pixel_count = None


    def _get_coordinates_of_parts(self, foreground):
        """
        Compute coordinates of the core and the periphery of the fly.
        The coordinates of each part are represented with a list of tuples
        where each tuple contains the x and y coordinate of one pixel.
        """

        non_zero_index = np.where(foreground > 0)

        self._fly_pixel_count = len(non_zero_index)

        median = np.median(non_zero_index)

        core = list(zip(*np.where(foreground < median)))
        periphery = list(zip(*np.where(foreground > median)))

        coordinates = {"core": core, "periphery": periphery}
        return coordinates

    def _get_parts_mask(self, foreground):
        """
        Return a mask of the ROI for each fly part
        The mask has the same shape as the ROI
        and is True on pixels that belong to the part.
        The masks are packed in a dictionary.
        """

        non_zero_index = np.where(foreground > 20)
        self._fly_pixel_count = len(non_zero_index)
        median = np.median(non_zero_index)

        coordinates = {"core": foreground < median, "periphery": foreground > median}
        return coordinates

    @staticmethod
    def _get_non_overlapping(coords_1, coords_2):
        """
        Count how many pixels are on one of the coordinates sets
        and not the other.
        """

        not_in_2 = sum([coord not in coords_2 for coord in coords_1])
        not_in_1 = sum([coord not in coords_1 for coord in coords_2])

        total_count = not_in_2 + not_in_1
        return total_count


    def _process_raw_feature(self, raw_feature, w_im):
        """
        Make the feature distance-like and normalize with the area of the fly,
        so it can be compared to the centroid displacement variable
        Normalize with the area of the fly to compensate for minor changes
        due to the fly exposing less of its body and viceversa.
        Finally take the log10 and multiply by 1000 to put in the same scale as CD
        as computed in the AdaptiveBGModel GG implementation.
        """
        distance = np.sqrt(raw_feature) / np.sqrt(self._fly_pixel_count)
        log10_xy_dist_x_1000 = np.log10(distance + 1 / w_im) * 1000
        logging.warning(log10_xy_dist_x_1000)
        return log10_xy_dist_x_1000
        # return np.sqrt(raw_feature) / np.sqrt(self._fly_pixel_count)



    def _track(self, *args, **kwargs):
        """
        Append two extra features called core_movement and periphery_movement
        to the datapoints returned by the abstract class's _track method.
        """

        old_foreground = np.copy(self._buff_fg_backup)

        # first do the same as in the AdaptiveBGModel
        datapoints = super()._track(*args, **kwargs)

        assert isinstance(args[1], np.ndarray)
        shape = args[1].shape
        # h_im = min(shape)
        w_im = max(shape)
        null_dist = round(np.log10(1. / float(w_im)) * 1000)

        # if an old foreground is available, compute the features
        # otherwise just return the null movements,
        # defined as 1 / number of pixels on x dimension
        if old_foreground is not None:
            new_foreground = self._buff_fg_backup

            # get the old and new coordinates of both parts
            old_masks = self._get_parts_mask(old_foreground)
            new_masks = self._get_parts_mask(new_foreground)
            features = {part: None for part in self._body_parts}

            for part in ["core", "periphery"]:
                # count how many pixels belong to the part on only one but noth both masks
                raw_feature = np.sum(np.bitwise_xor(old_masks[part], new_masks[part]))
                # take a sqroot to make it distance-like and normalize with the sqroot of the area of the fly
                features[part] = self._process_raw_feature(raw_feature, w_im)

            # instantiate the distances with a wrapper
            # that streamlines saving to output
            core_movement = CoreMovement(features["core"])
            periphery_movement = PeripheryMovement(features["periphery"])

        else:
            core_movement = CoreMovement(null_dist)
            periphery_movement = PeripheryMovement(null_dist)

        # add the extra features to datapoints and return it
        datapoints[0].append(core_movement)
        datapoints[0].append(periphery_movement)


        return datapoints
