class Pool {
    /**
     * Construct a new Pool object. This class is intended to be subclassed.
     * Subclasses should optionally (but probably) override
     * drawAlignmentFeatures and setDefaultPositions, found below.
     *
     * name              -- The pool's name. Must be at most 16 characters.
     * width             -- The pool's real size along the axis displayed
     *                      horizontally in the GUI. Given in meters.
     * height            -- The pool's real size along the axis displayed
     *                      vertically in the GUI. Given in meters.
     * depthAxisVertical -- If depth varies along the pool's vertical axis, as
     *                      opposed to along its horizontal axis. The tool does
     *                      not currently support more complex schemes of depth
     *                      variance.
     * depthKeypoints    -- A collection of distances from the origin along the
     *                      axis of variable depth and the depths of the pool
     *                      at those distances. Given as an array of length-two
     *                      arrays, each of which has the form [distance,
     *                      depth], both in meters. Must include at least one
     *                      keypoint.
     * pingerFrequency   -- The frequency of the pinger present in the pool. Use
     *                      0 as a default value if no frequency is appropriate.
     */
    constructor(name, width, height, depthAxisVertical, depthKeypoints,
            pingerFrequency) {
        this.name = name
        this.width = width
        this.height = height
        this.depthAxisVertical = depthAxisVertical
        this.depthKeypoints = depthKeypoints
        this.pingerFrequency = pingerFrequency
    }

    /** Draw the pool and its accompaniments, but not the mission elements. */
    drawPool() {
        // The blue rectangle itself.
        noStroke()
        fill(91, 155, 213)
        rect(50, 100, this.width * ppm, this.height * ppm)
        
        // Tick marks along the pool's sides, 1 meter apart.
        strokeWeight(1)
        stroke(0)
        for (let x = 0; x < this.width; x++) {
            line(50.5 + x * ppm, 90, 50.5 + x * ppm, 95)
        }
        for (let y = 0; y < this.height; y++) {
            line(40, 100.5 + y * ppm, 45, 100 + y * ppm)
        }

        this.labelDepthKeypoints()
        this.drawAlignmentFeatures()
    }

    /** Along the axis of variable depth, mark depth keypoints for reference. */
    labelDepthKeypoints() {
        noStroke()
        fill(0)
        textSize(8)
        if (this.depthAxisVertical) {
            text(this.depthAt(createVector(0, 0)).toFixed(1),
                    60 + this.width * ppm, 101)
            for (const keypoint of this.depthKeypoints) {
                if (keypoint[0] > 0 && keypoint[0] < this.height) {
                    text(this.depthAt(createVector(0, keypoint[0])).toFixed(1),
                            60 + this.width * ppm, 101 + keypoint[0] * ppm)
                }
            }
            text(this.depthAt(createVector(0, this.height)).toFixed(1),
                    60 + this.width * ppm, 101 + this.height * ppm)
        } else {
            textAlign(CENTER)
            text(this.depthAt(createVector(0, 0)).toFixed(1),
                    50, 110 + this.height * ppm)
            for (const keypoint of this.depthKeypoints) {
                if (keypoint[0] > 0 && keypoint[0] < this.width) {
                    text(this.depthAt(createVector(keypoint[0], 0)).toFixed(1),
                            50 + keypoint[0] * ppm, 110 + this.height * ppm)
                }
            }
            text(this.depthAt(createVector(this.width, 0)).toFixed(1),
                    50 + this.width * ppm, 110 + this.height * ppm)
            textAlign(LEFT)
        }
    }

    /** Return if a point (in pool-space) is within the confines of the pool. */
    contains(vector) {
        return vector.x > 0 && vector.x < this.width && vector.y > 0 &&
                vector.y < this.height
    }

    /** 
     * Return the depth (in meters) of the pool at a location, provided as a
     * (pool-space) vector. Performs linear interpolation between keypoints. If
     * the point is past the first or last keypoint, use the depth at that most
     * extreme keypoint.
     */
    depthAt(vector) {
        const coord = this.depthAxisVertical ? vector.y : vector.x
        if (this.depthKeypoints[0][0] > coord) {
            return this.depthKeypoints[0][1]
        }
        for (let i = 1; i < this.depthKeypoints.length; i++) {
            if (this.depthKeypoints[i][0] > coord) {
                const change = this.depthKeypoints[i][1] -
                        this.depthKeypoints[i - 1][1]
                const dist = this.depthKeypoints[i][0] -
                        this.depthKeypoints[i - 1][0]
                const rate = change / dist
                return this.depthKeypoints[i - 1][1] +
                        rate * (coord - this.depthKeypoints[i - 1][0])
            }
        }
        return this.depthKeypoints[this.depthKeypoints.length - 1][1]
    }

    /**
     * Draw additional features in and around the pool to help members
     * accurately position elements. This should be optionally overridden by
     * subclasses of Pool. Examples of helpful features include lines along the
     * pool's bottom and objects around the pool's edges.
     */
    drawAlignmentFeatures() { }

    /**
     * Set the positions and orientations of mission elements to good default
     * values for the specific pool. This should be optionally overridden by
     * subclassess of Pool. The default implementation given here arranges
     * elements in a vertical column.
     */
    setDefaultPositions(elements) {
        let topY = 20 / ppm
        for (let element of Object.values(elements)) {
            if (element instanceof ApproachPoint) {
                element.enabled = false
                continue
            }
            element.pos = createVector(20 / ppm + element.size.x / 2,
                    topY + element.size.y / 2)
            element.dir = 0
            topY += element.size.y + 20 / ppm
            if (element.approachPoint != null) {
                element.approachPoint.pos =
                        createVector(element.size.x + 40 / ppm, element.pos.y)
            }
        }
    }
}
