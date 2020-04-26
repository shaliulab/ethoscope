# USAGE
# python find_screen.py --query queries/query_marowak.jpg

# import the necessary packages
from skimage import exposure
import numpy as np
import argparse
import imutils
import cv2

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-q", "--query", required = True,
	help = "Path to the query image")
args = vars(ap.parse_args())

# load the query image, compute the ratio of the old height
# to the new height, clone it, and resize it
image = cv2.imread(args["query"])
print(image.shape)
ratio = image.shape[0] / 300.0
orig = image.copy()
image = imutils.resize(image, height = 300)
orig_resized = image.copy()

# convert the image to grayscale, blur it, and find edges
# in the image
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
gray = cv2.bilateralFilter(gray, 11, 17, 17)
edged = cv2.Canny(gray, 30, 200)

# find contours in the edged image, keep only the largest
# ones, and initialize our screen contour
cnts = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
cnts = imutils.grab_contours(cnts)
cnts = sorted(cnts, key = cv2.contourArea, reverse = True)[:10]
screenCnt = None

# loop over our contours
for c in cnts:
	# approximate the contour
	peri = cv2.arcLength(c, True)
	approx = cv2.approxPolyDP(c, 0.015 * peri, True)

	# if our approximated contour has four points, then
	# we can assume that we have found our screen
	if len(approx) == 4:
		screenCnt = approx
		break

# now that we have our screen contour, we need to determine
# the top-left, top-right, bottom-right, and bottom-left
# points so that we can later warp the image -- we'll start
# by reshaping our contour to be our finals and initializing
# our output rectangle in top-left, top-right, bottom-right,
# and bottom-left order
pts = screenCnt.reshape(4, 2)
rect = np.zeros((4, 2), dtype = "float32")

# the top-left point has the smallest sum whereas the
# bottom-right has the largest sum
s = pts.sum(axis = 1)
rect[0] = pts[np.argmin(s)]
rect[2] = pts[np.argmax(s)]

# compute the difference between the points -- the top-right
# will have the minumum difference and the bottom-left will
# have the maximum difference
diff = np.diff(pts, axis = 1)
rect[1] = pts[np.argmin(diff)]
rect[3] = pts[np.argmax(diff)]


# multiply the rectangle by the original ratio
rect *= ratio

# now that we have our rectangle of points, let's compute
# the width of our new image
(tl, tr, br, bl) = rect

widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))

# ...and now for the height of our new image
heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))

# take the maximum of the width and height values to reach
# our final dimensions
maxWidth = max(int(widthA), int(widthB))
maxHeight = max(int(heightA), int(heightB))

# construct our destination points which will be used to
# map the screen to a top-down, "birds eye" view
dst = np.array([
            # tr corner
	    #[maxWidth - 1, 0],
	    [0, -1],
            # br corner
	    #[maxWidth - 1, maxHeight - 1],
	    [-1, -1],
            # bl corner
	    #[0, maxHeight - 1],
	    [-1, 0],
        ],  dtype = "float32")

rect = rect[1:]

print(dst)

# Plot the rectangle that we will be cropping from the image
# on the origin (0,0) i.e. top left corner
colors = [(255, 0, 0), (0, 255,0), (0, 0, 255)]
for i, pt in enumerate(dst):
     print(pt)
     print(i)
     pos = tuple(int(c) for c in pt)
     pos = (pos[0], pos[1]+orig.shape[0] // 50)
     orig = cv2.circle(orig, pos, int(orig.shape[0]/50), colors[i], -1)
     orig = cv2.putText(orig, str(i), pos, cv2.FONT_HERSHEY_DUPLEX, 5, (0,0,0), 1)

orig_res = imutils.resize(orig, height = 700)
cv2.imshow("dst", orig_res)
cv2.waitKey(0)


# calculate the perspective transform matrix and warp
# the perspective to grab the screen
# M is a 2xn matrix
# every row represents a dimension
# every column represents a point
# we have 3 points so n = 3
# i.e. M is 2x3

print("Create affine transform matrix")
print(rect)
print(dst)

M = cv2.getAffineTransform(rect, dst)
max_dims = (maxWidth, maxHeight)

shift = np.dot(M, [1,1,0]) - rect[1] # point 1 is the ref, at 0,0

rect = np.append(rect, np.zeros((3,1)), axis=1)


print("Tansform rect")
print(rect.shape)
print(rect)

mapped_rectangle = np.dot(M, rect.T).T
print("Transformed")
print(mapped_rectangle)
mapped_rectangle -= shift
print(mapped_rectangle)

ct = mapped_rectangle.reshape((1,3,2)).astype(np.int32)

print(ct)

cv2.drawContours(orig,[ct], -1, (255,0,0),-1, cv2.LINE_AA)

orig = imutils.resize(orig, height=300)

# show our images
cv2.imshow("orig", orig)
cv2.imshow("dst", orig_res)
cv2.waitKey(0)
