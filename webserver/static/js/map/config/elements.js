class Gate extends MissionElement {
    constructor() {
        super(createVector(0.2, 3.05), 0, 2)
        this.counterImg = loadImage('/static/images/map/gate_counter.png')
        this.clockwiseImg = loadImage('/static/images/map/gate_clockwise.png')
    }

    drawInner() {
        push()
        rotate(HALF_PI)
        noStroke()
        fill(0)
        rect(-1.525 * ppm, -0.1 * ppm, 3.05 * ppm, 0.2 * ppm)
        if (this.config == 0) {
            image(this.counterImg, (-0.763 - 0.25) * ppm, 0.1 * ppm, 0.5 * ppm,
                    0.682 * ppm)
            image(this.clockwiseImg, (0.763 - 0.25) * ppm, 0.1 * ppm,
                    0.5 * ppm, 0.682 * ppm)
        } else {
            image(this.clockwiseImg, (0.763 - 0.25) * ppm, 0.1 * ppm, 0.5 * ppm,
                    0.682 * ppm)
            image(this.counterImg, (-0.763 - 0.25) * ppm, 0.1 * ppm,
                    0.5 * ppm, 0.682 * ppm)
        }
        pop()
    }
}

class Buoy extends MissionElement {
    constructor() {
        super(createVector(0.23, 0.23), 0, 1)
    }

    drawInner() {
        noStroke()
        fill(255, 0, 0)
        ellipse(0, 0, 0.23 * ppm, 0.23 * ppm)
    }
}

class Bin extends MissionElement {
    constructor() {
        super(createVector(0.61, 0.91), 0, 1)
    }

    drawInner() {
        noStroke()
        fill(255)
        rect(-0.305 * ppm, -0.455 * ppm, 0.61 * ppm, 0.91 * ppm)
        fill(255, 0, 0)
        rect(-0.15 * ppm, -0.61 * ppm, 0.3 * ppm, 0.61 * ppm)
        fill(0, 0, 255)
        rect(-0.15 * ppm, 0, 0.3 * ppm, 0.61 * ppm)
    }
}

class Torpedoes extends MissionElement {
    constructor() {
        super(createVector(0.6, 0.6), 0, 1)
        this.img = loadImage('/static/images/map/torpedoes.png')
    }

    drawInner() {
        push()
        rotate(HALF_PI)
        image(this.img, -0.3 * ppm, -0.3 * ppm, 0.6 * ppm, 0.6 * ppm)
        pop()
    }
}

class Octagon extends MissionElement {
    constructor() {
        super(createVector(2.74, 2.74), 0, 1)
    }

    drawInner() {
        strokeWeight(0.2 * ppm)
        stroke(0)
        noFill()
        beginShape()
        vertex(1.37 * ppm, -0.568 * ppm),
        vertex(0.568 * ppm, -1.37 * ppm),
        vertex(-0.568 * ppm, -1.37 * ppm),
        vertex(-1.37 * ppm, -0.568 * ppm),
        vertex(-1.37 * ppm, 0.568 * ppm),
        vertex(-0.568 * ppm, 1.37 * ppm),
        vertex(0.568 * ppm, 1.37 * ppm),
        vertex(1.37 * ppm, 0.568 * ppm)
        endShape(CLOSE)
    }
}
