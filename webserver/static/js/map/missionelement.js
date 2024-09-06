// Note: At the bottom of this file are defined the ApproachPoint and Sub
// classes, each of which extends MissionElement.

class MissionElement {
    /** 
     * Construct a new MissionElement object. This class is intended to be
     * subclassed. Subclasses must override drawInner, found below.
     *
     * size       -- The size of the element's bounding box, given as a vector,
     *               with size.x representing its width and size.y its height,
     *               both in meters.
     * config     -- The element's default configuration number. Configurations
     *               can be quickly cycled using buttons in the GUI. An example
     *               of a use case for multiple configurations is an element on
     *               which either of two images could appear on the left.
     * numConfigs -- The number of configurations the element can take on.
     */
    constructor(size, config, numConfigs) {
        this.size = size
        this.config = config
        this.numConfigs = numConfigs

        // A (pool-space) vector representing the element's center location.
        this.pos = createVector(0, 0)

        // The direction the element is facing, in radians, with 0 being to the
        // right and increasing angles going counter-clockwise.
        this.dir = 0

        // If the element should be visible and interactable in the GUI.
        // Generally, only approach points are ever disabled.
        this.enabled = true

        // The approach point object attached to this mission element, or null
        // if there is none.
        this.approachPoint = null

        this.dragging = false
        this.draggingOffset = null
        this.selected = false
    }

    /**
     * Draw the element. When this.dir is 0, the element should appear to be
     * pointing to the right (meaning a sub facing the element would be facing
     * to the right). Implementations often have to use p5.js's rotate function
     * to manipulate the canvas. This must be overriden by suclasses of
     * MissionElement.
     */
    drawInner() { }

    /**
     * Move the element to match the mouse pointer's movement, if the element is
     * currently being dragged.
     */
    moveIfDragging() {
        if (this.dragging) {
            if (!this.pos.equals(toPoolSpace(p5.Vector.sub(mouseVector(), this.draggingOffset)))) {
                updatedSinceSave = true
                updatedSinceLoad = true
            }
            this.pos = toPoolSpace(p5.Vector.sub(mouseVector(), this.draggingOffset))
        }
    }

    /** Draw the element. This should *not* be overridden. */
    draw() {
        if (this.approachPoint !== null && this.approachPoint.enabled) {
            this.drawLineToApproachPoint()
        }
        push()
        translate(toCanvasSpace(this.pos))
        rotate(this.dir)
        this.drawInner()
        pop()
        this.drawSelectionIfSelected()
    }

    /**
     * Draw the green line between the mission element and its approach point.
     * This is only called when this.approachPoint is not null.
     */
    drawLineToApproachPoint() {
        strokeWeight(3)
        stroke(0, 255, 0)
        const approachVec = p5.Vector.sub(this.pos, this.approachPoint.pos)
        const lineEndpointOffset = approachVec.copy().setMag(5)
        line(50 + this.pos.x * ppm, 100 + this.pos.y * ppm,
            50 + this.approachPoint.pos.x * ppm + lineEndpointOffset.x,
            100 + this.approachPoint.pos.y * ppm + lineEndpointOffset.y)
        strokeWeight(3)
        point(50 + this.pos.x * ppm, 100 + this.pos.y * ppm)
    }

    /** Draw four red dots at the mission element's corners if it is selected. */
    drawSelectionIfSelected() {
        if (this.selected) {
            strokeWeight(5)
            stroke(255, 0, 0)
            this.getCorners().forEach(vector =>
                point(vector.x, vector.y)
            )
        }
    }

    /**
     * Return the corners of the mission element's bounding box, as a length-four
     * array of (canvas-space) vectors. A padding (given in canvas-space)
     * pushes the returned corners outward.
     */
    getCorners(padding = 0) {
        return [
            createVector(this.size.x / 2 + padding / ppm,
                         -this.size.y / 2 - padding / ppm),
            createVector(-this.size.x / 2 - padding / ppm,
                         -this.size.y / 2 - padding / ppm),
            createVector(-this.size.x / 2 - padding / ppm,
                         this.size.y / 2 + padding / ppm),
            createVector(this.size.x / 2 + padding / ppm,
                         this.size.y / 2 + padding / ppm)
        ]
        .map(vector => p5.Vector.rotate(vector, this.dir))
        .map(vector => p5.Vector.add(vector, this.pos))
        .map(toCanvasSpace)
    }

    /**
     * When the mission element is clicked, select it and set it up to be
     * dragged around. Alternatively, if the mouse is outside the element,
     * deselect it.
     */
    handleMousePress() {
        if (collidePointPoly(mouseX, mouseY, this.getCorners(15))) {
            this.dragging = true
            this.selected = true
            this.draggingOffset = p5.Vector.sub(mouseVector(), toCanvasSpace(this.pos))
        } else {
            this.selected = false
        }
    }

    /** Stop the element being dragged when the mouse is released. */
    handleMouseRelease() {
        this.dragging = false
    }

    /**
     * Rotate the element with the ',' and '.' keys, and toggle its approach
     * point (or itself if it is an approach point) with the 'a' key.
     */
    handleKeyPress() {
        if (this.selected) {
            if (key == ',' || key == '<') {
                this.dir -= HALF_PI / 9
                updatedSinceSave = true
                updatedSinceLoad = true
            }
            if (key == '.' || key == '>') {
                this.dir += HALF_PI / 9
                updatedSinceSave = true
                updatedSinceLoad = true
            }
            if (key == 'a' || key =='A') {
                if (this instanceof ApproachPoint) {
                    this.enabled = !this.enabled
                } else if (this.approachPoint !== null) {
                    this.approachPoint.enabled = !this.approachPoint.enabled
                }
                updatedSinceSave = true
                updatedSinceLoad = true
            }
        }
    }
}

class ApproachPoint extends MissionElement {
    /**
     * Approach points are special elements attached to regular, custom
     * elements. The initial idea behind them was that the sub could go to an
     * element's approach point before heading to the element itself in cases
     * where an element must be approached from a specific direction. But they
     * can be used for any purpose for which an additional control point is
     * helpful. An approach point is automatically generated for each custom
     * (non-sub) mission element.
     */
    constructor() {
        super(createVector(0.5, 0.5), 0, 1)
    }

    /** Represent the approach point as a small green circle. */
    drawInner() {
        strokeWeight(3)
        stroke(0, 255, 0)
        noFill()
        ellipse(0, 0, 10, 10)
    }
}

class Sub extends MissionElement {
    /**
     * The sub is a special element which is always included.
     *
     * size -- The size of the sub's bounding box, with size.x representing the
     *         sub's length and size.y its width, both in meters.
     */
    constructor(size) {
        super(size, 0, 1)
    }

    /** 
     * Represent the sub as a red rectangle. An arrow is included to show
     * its direction.
     */
    drawInner() {
        noStroke()
        fill(201, 23, 10)
        rect(-0.445 * ppm, -0.315 * ppm, 0.89 * ppm, 0.63 * ppm)
        strokeWeight(1)
        stroke(0)
        line(-0.3 * ppm, 0, 0.3 * ppm, 0)
        line(0.3 * ppm, 0, 0.1 * ppm, -0.2 * ppm)
        line(0.3 * ppm, 0, 0.1 * ppm, 0.2 * ppm)
    }

    moveIfDragging() {
        super.moveIfDragging()
        this.dir = -HALF_PI
        //this.dir = Math.atan2(elements['gate'].pos.y - elements['sub'].pos.y, elements['gate'].pos.x - elements['sub'].pos.x)
    }
}
