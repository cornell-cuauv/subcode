class Gate extends MissionElement {
    constructor() {
        super(createVector(0.2, 3.05), 0, 2)
        this.gmanImage = loadImage('/static/images/map/gman.png')
        this.bootleggerImage = loadImage('/static/images/map/bootlegger.png')
    }

    drawInner() {
        push()
        rotate(HALF_PI)
        noStroke()
        fill(0)
        rect(-1.525 * ppm, -0.1 * ppm, 3.05 * ppm, 0.2 * ppm)
        if (this.config == 0) {
            image(this.gmanImage, (-0.763 - 0.25) * ppm, 0.1 * ppm, 0.5 * ppm,
                    0.682 * ppm)
            image(this.bootleggerImage, (0.763 - 0.25) * ppm, 0.1 * ppm,
                    0.5 * ppm, 0.682 * ppm)
        } else {
            image(this.gmanImage, (0.763 - 0.25) * ppm, 0.1 * ppm, 0.5 * ppm,
                    0.682 * ppm)
            image(this.bootleggerImage, (-0.763 - 0.25) * ppm, 0.1 * ppm,
                    0.5 * ppm, 0.682 * ppm)
        }
        pop()
    }
}

class Buoys extends MissionElement {
    constructor() {
        super(createVector(1.30, 1.27), 0, 2)
        this.buoysImage = loadImage('/static/images/map/buoys.png')
    }

    drawInner() {
        push()
        rotate(HALF_PI)
        if (this.config == 0) {
            image(this.buoysImage, -0.635 * ppm, -0.65 * ppm, 0.635 * ppm,
                    1.30 * ppm, 0, 0, 522, 1068)
            image(this.buoysImage, 0, -0.65 * ppm, 0.635 * ppm, 1.30 * ppm, 522,
                    0, 522, 1068)
        } else {
            image(this. buoysImage, -0.635 * ppm, -0.65 * ppm, 0.635 * ppm,
                    1.30 * ppm, 522, 0, 522, 1068)
            image(this.buoysImage, 0, -0.65 * ppm, 0.635 * ppm, 1.30 * ppm, 0,
                    0, 522, 1068)
        }
        pop()
    }
}

class Bins extends MissionElement {
    constructor() {
        super(createVector(0.70, 0.66), 0, 1)
        this.binsImage = loadImage('/static/images/map/bins.png')
    }

    drawInner() {
        push()
        rotate(HALF_PI)
        image(this.binsImage, -0.33 * ppm, -0.35 * ppm, 0.66 * ppm, 0.70 * ppm)
        pop()
    }
}

class Torpedoes extends MissionElement {
    constructor() {
        super(createVector(1.23, 1.27), 0, 2)
        this.torpedoesImage = loadImage('static/images/map/torpedoes.png')
    }

    drawInner() {
        push()
        rotate(HALF_PI)
        if (this.config == 0) {
            image(this.torpedoesImage, -0.635 * ppm, -0.615 * ppm, 1.27 * ppm,
                    1.23 * ppm)
        } else {
            image(this.torpedoesImage, -0.635 * ppm, -0.615 * ppm, 0.635 * ppm,
                    1.23 * ppm, 251, 0, 251, 488)
            image(this.torpedoesImage, 0, -0.615 * ppm, 0.635 * ppm, 1.23 * ppm,
                    0, 0, 251, 488)
        }
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
