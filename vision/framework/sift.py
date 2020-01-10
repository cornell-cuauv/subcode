import cv2

class SIFT:
    """
    A wrapper for using SIFT in OpenCV

    SIFT is an algorithm used for feature detection and matching.
    Images are compared to multiple source images, and all matches of the source images are found.
    """
    # TODO: BFMatcher

    def __init__(self, checks=50):
        """
        checks: Specifies the number of times the trees should be recursively
                traversed. Higher checks give higher precision but lowers performance
        """
        self.sift = cv2.xfeatures2d.SIFT_create()

        # Because OpenCV is bad at porting enums
        FLANN_INDEX_KDTREE = 0

        # index_params specify the algorithm used by the matcher and its
        # parameters
        index_params = {"algorithm": FLANN_INDEX_KDTREE, "trees": 5}
        # search parameters specify the number of times the trees should be
        # recursively traversed
        # Higher checks give higher precision but lowers fps
        search_params = {"checks": checks}

        self.matcher = cv2.FlannBasedMatcher(index_params, search_params)
        self.sources = {}
        # self.debug = debug # TODO


    def add_source(self, name, source):
        """
        Adds an image as a source.
        name: Name of the source
        source: The source image
        """
        kp, des = self.detector.detectAndCompute(source, None)
        self.sources[name] = {"name": name, "source": source, "kp":kp, "des":des}


    def add_many(self, **kwargs):
        """
        Adds multiple images as a source.

        Sources are specified using keyword arguements, where the key is name
        of the source and the value is the image of the source.
        """
        for name, source in kwargs.items():
            add_source(name, source)


    def _ratio_test(matches, ratio=0.7):
        # I have no idea why I used the commented code below, probably because
        # something broke and I did something jank.

        good = []
        # for m,n in (x for x in matches if len(x) == 2):
        for m, n in matches:
            if m.distance < ratio * n.distance:
                good.append(m)
        return good


    def match(self, img, min_match=10, ratio=0.7, draw=False):
        # TODO: Draw shouldn't work rn
        """
        Find all instances of source images in an image.

        img:        The image to be matched.
        min_match:  The minimum number of keypoint matches to identify a
                    source.  Increasing this number allows sources to be
                    identified more accurately, but less reliably.
        ratio:      A number [0..1] that is used to identify a "good" match
                    using the ratio test. A higher number means more matches
                    are considered "good", but is also more likely to be noise.
        draw:       Whether to draw the matches. I really believe it is not
                    required, usually it is possible to just compare the
                    keypoints through human eye, but is a useful tool for
                    debugging.

        The function returns the following as a tuple in this order:
        - A list of identified sources, which is a tuple including the
          following in this order:
            - the name of the source
            - the good matches found
            - a single contour specifying the area of the match as a
              transformed rectangle,
            - a mask of the matched area;
        - The keypoints of the imaged passed
        - The feature descriptors of the image passed
        - An image showing all the matches found, or None if draw is False
        """
        kp, des = self.sift.detectAndCompute(img, None)
        matched = []
        drawim = np.copy(img) if draw else None
        draw_params = dict(matchColor=(0,255,0), singlePointColor=None,
            matchesMask=matchesMask, flags=2)
        for name, val in self.sources.items():
            matches = self.matcher.knnMatch(val[des], des, k=2)

            good = _ratio_test(matches, ratio=ratio)
            if len(good) < min_match:
                continue

            # TODO: What if we don't do homogenous transform?
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good])\
                .reshape(-1,1,2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good])\
                .reshape(-1,1,2)

            matrix, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            matchesMask = mask.ravel().tolist()

            h,w = img1.shape
            pts = np.float32([[PADDING,PADDING],
                [PADDING,h-1-PADDING],
                [w-1-PADDING,h-PADDING-1],
                [w-PADDING-1,PADDING]]).reshape(-1,1,2)

            try:
                # OpenCV sometimes throws assertion errors here. It should have
                # been fixed by updating opencv, but it's here just in case
                dst = np.int32(cv2.perspectiveTransform(pts, matrix))
            except cv2.error as e:
                print(e)
                continue

            if draw:
                draw_params[matchesMask] = matchesMask
                drawim = cv2.drawMatches(val[source], val[kp], img, kp, good, None, **draw_params)

            matched.append((val[name], good, dst, matchesMask)

        return matched, kp, des, drawim


def draw_transformed_box(im, dst, color=(0, 0, 255), thickness=3):
    """
    Draws a transformed box on the image similar to drawing contours.

    im: The image to be drawn on
    dst: The transformed rectangle
    color: The color of the rectangle drawn
    thickness: The thickness of each side of the rectangle.
    """
    return cv2.polylines(im, [dst], True, color, thickness, cv2.LINE_AA)


def draw_keypoints(im, kp, color=(0, 0, 255)):
    # TODO: This shouldn't work
    """
    Draws all the keypoints to an image

    im: The image to be drawn on
    kp: The keypoints to be drawn
    """
    out = np.copy(im)
    return cv2.drawKeypoints(im, kp, out)
