        # features = []
        # for i, ct in enumerate(full_contours):
        #     rect = cv2.boundingRect(ct)
        #     x,y,w,h = rect   
        #     roi = np.array([(x,y), (x+w, y), (x+w,y+h), (x, y+h)])
        #     left, top = find_quadrant(bin_rotated, roi)
        #     out_left, out_right, out_top, out_bottom = (np.nan,)*4
        #     if left:
        #         out_left = x
        #     else:
        #         out_right = x+w
        #     if top:
        #         out_top = y
        #     else:
        #         out_botom = y+h

        #     features.append((w,h, out_left, out_right, out_top, out_bottom))

        # features = np.array(features)
        # median_width = np.median([e[0] for e in features])
        # median_height = np.median([e[1] for e in features])
        # median_out_left = np.nanmedian([e[2] for e in features])
        # median_out_right = np.nanmedian([e[3] for e in features])
        # median_out_top = np.nanmedian([e[4] for e in features])
        # median_out_bottom = np.nanmedian([e[5] for e in features])
        
        # mask = np.zeros_like(bin_rotated)
        # mask[:, (2*mask.shape[1]//5):(3*mask.shape[1]//5)] = 255

        # # cut 5 slices vertically and get the central one
        # bin_rotated_center = cv2.bitwise_and(bin_rotated, bin_rotated, mask=mask)

        # cv2.imshow("bin_rotated_center", bin_rotated_center)
        # cv2.imshow("bin_rotated", bin_rotated)
        # cv2.waitKey(0)

        # # detect contours
        # if CV_VERSION == 3:
        #     _, masked_contours, _ = cv2.findContours(bin_rotated_center, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # else:
        #     masked_contours, _ = cv2.findContours(bin_rotated_center, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)
        
        
        # rois = []
        # # for each contour compute the smallest horizontal rectangle
        # # around it
        # x_margin = 200
        # width = median_width
        # height = median_height

        # centers = np.stack((bin_rotated,bin_rotated, bin_rotated), axis=2)