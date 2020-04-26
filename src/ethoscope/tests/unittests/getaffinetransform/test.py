import cv2
import numpy as np
from ethoscope.roi_builders.target_roi_builder import FSLSleepMonitorWithTargetROIBuilder

dst_points = np.array([(0,-1),
                       (0,0),
                       (-1,0)], dtype=np.float32)

pts = [(167, 847), (1104, 825), (1067, 228)]
sorted_src_pts = np.array(pts, dtype = np.float32)

wrap_mat = cv2.getAffineTransform(dst_points, sorted_src_pts)


img = cv2.imread("dark_targets_above.png")

roi_builder = FSLSleepMonitorWithTargetROIBuilder()
#roi_builder._rois_from_img
self = roi_builder

sorted_src_pts = self._find_target_coordinates(img, self._find_blobs_new)

dst_points = np.array([(0,-1),
                       (0,0),
                       (-1,0)], dtype=np.float32)

wrap_mat = cv2.getAffineTransform(dst_points, sorted_src_pts)

rectangles = self._make_grid(self._n_cols, self._n_rows,
                             self._top_margin, self._bottom_margin,
                             self._left_margin,self._right_margin,
                             self._horizontal_fill, self._vertical_fill,
                             self._horizontal_pad, self._vertical_pad,
                             self._horizontal_offset, self._vertical_offset,
                             )

print("Targets")
print(pts)
print("Affine transformation matrix")
print(wrap_mat)
print("Destination")
print(dst_points)

shift = np.dot(wrap_mat, [1,1,0])
print("Shift")
print(shift)


#print(rectangles)
