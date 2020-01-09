import cv2

class SIFT:
    # TODO: BFMatcher
    def __init__(self, checks=50, debug=False):
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
        self.debug = debug # TODO


    def add_source(self, name, source):
        kp, des = self.detector.detectAndCompute(source, None)
        self.sources[name] = {"name": name, "source": source, "kp":kp, "des":des}


    def add_many(self, **kwargs):
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


    def match(self, img, min_match=10, ratio=0.7, draw=True):
        kp, des = self.sift.detectAndCompute(img, None)
        matched = []
        for name, val in self.sources.items():
            matches = self.matcher.knnMatch(val[des], des, k=2)

            good = _ratio_test(matches, ratio=ratio)
            if len(good) < min_match:
                continue

            # TODO: What if we don't do homogenous transform?
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1,1,2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1,1,2)

            matrix, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC,5.0)
            matchesMask = mask.ravel().tolist()

            h,w = img1.shape
            pts = np.float32([[PADDING,PADDING],[PADDING,h-1-PADDING],[w-1-PADDING,h-PADDING-1],[w-PADDING-1,PADDING]]).reshape(-1,1,2)

            try:
                # OpenCV sometimes throws assertion errors here. It should be
                # fixed by updating opencv, but it's here just in case
                dst = np.int32(cv2.perspectiveTransform(pts, matrix))
            except cv2.error as e:
                print(e)
                continue

            matched.append((len(matches), val[name], val, good, dst, matchesMask)

        num_matches, name, val, good, dst, mask = min(matched)

        drawim = np.copy(img) if draw else None
        if draw:
            draw_params = dict(matchColor=(0,255,0), singlePointColor=None,
                matchesMask=matchesMask, flags=2)
            drawim = cv2.drawMatches(val[source], val[kp], img, kp, good, None, **draw_params)

        return name, dst, mask, drawim


def draw_transformed_box(im, dst, color=(0, 0, 255), thickness=3):
    return cv2.polylines(im, [dst], True, color, thickness, cv2.LINE_AA)


def draw_keypoints(im, kp, color=(0, 0, 255)):
    out = np.copy(im)
    return cv2.drawKeypoints(im, kp, out)
