class Gate extends MissionElement {
    constructor() {
        super(createVector(0.2, 3.05), 0, 2)
        this.earthImage = loadImage('/static/images/map/gate_earth.jpg')
        this.abydosImage = loadImage('/static/images/map/gate_abydos.jpg')
    }

    drawInner() {
        push()
        rotate(HALF_PI)
        noStroke()
        fill(0)
        rect(-1.525 * ppm, -0.1 * ppm, 3.05 * ppm, 0.2 * ppm)
        if (this.config == 0) {
            image(this.earthImage, (-0.763 - 0.25) * ppm, 0.1 * ppm, 0.5 * ppm,
                    0.682 * ppm)
            image(this.abydosImage, (0.763 - 0.25) * ppm, 0.1 * ppm,
                    0.5 * ppm, 0.682 * ppm)
        } else {
            image(this.earthImage, (0.763 - 0.25) * ppm, 0.1 * ppm, 0.5 * ppm,
                    0.682 * ppm)
            image(this.abydosImage, (-0.763 - 0.25) * ppm, 0.1 * ppm,
                    0.5 * ppm, 0.682 * ppm)
        }
        pop()
    }
}

class Buoy extends MissionElement {
    constructor() {
        super(createVector(1.22, 1.22), 0, 2)
        this.buoyImage0 = loadImage('/static/images/map/buoy0.png')
        this.buoyImage1 = loadImage('/static/images/map/buoy1.png')
    }

    drawInner() {
        push()
        rotate(HALF_PI)
        if (this.config == 0) {
            image(this.buoyImage0, -0.61 * ppm, -0.61 * ppm, 1.22 * ppm, 1.22 * ppm)
        } else {
            image(this.buoyImage1, -0.61 * ppm, -0.61 * ppm, 1.22 * ppm, 1.22 * ppm)
        }
        pop()
    }
}

class EarthBin extends MissionElement {
    constructor() {
        super(createVector(0.60, 0.90), 0, 2)
        this.image0 = loadImage('/static/images/map/bin_earth0.png')
        this.image1 = loadImage('/static/images/map/bin_earth1.png')
    }

    drawInner() {
        push()
        rotate(HALF_PI)
        strokeWeight(0)
        fill(255)
        rect(-0.45 * ppm, -0.3 * ppm, 0.90 * ppm, 0.60 * ppm)
        if (this.config == 0) {
            image(this.image0, -0.30 * ppm, -0.15 * ppm, 0.60 * ppm, 0.30 * ppm)
        } else {
            image(this.image1, -0.30 * ppm, -0.15 * ppm, 0.60 * ppm, 0.30 * ppm)
        }
        pop()
    }
}

class AbydosBin extends MissionElement {
    constructor() {
        super(createVector(0.60, 0.90), 0, 2)
        this.image0 = loadImage('/static/images/map/bin_abydos0.png')
        this.image1 = loadImage('/static/images/map/bin_abydos1.png')
    }

    drawInner() {
        push()
        rotate(HALF_PI)
        strokeWeight(0)
        fill(255)
        rect(-0.45 * ppm, -0.3 * ppm, 0.90 * ppm, 0.60 * ppm)
        if (this.config == 0) {
            image(this.image0, -0.30 * ppm, -0.15 * ppm, 0.60 * ppm, 0.30 * ppm)
        } else {
            image(this.image1, -0.30 * ppm, -0.15 * ppm, 0.60 * ppm, 0.30 * ppm)
        }
        pop()
    }
}

class Torpedoes extends MissionElement {
    constructor() {
        super(createVector(1.22, 1.22), 0, 2)
        this.torpedoesImage0 = loadImage('static/images/map/torpedoes0.png')
        this.torpedoesImage1 = loadImage('static/images/map/torpedoes1.png')
    }

    drawInner() {
        push()
        rotate(HALF_PI)
        if (this.config == 0) {
            image(this.torpedoesImage0, -0.61 * ppm, -0.61 * ppm, 1.22 * ppm,
                    1.22 * ppm)
        } else {
            image(this.torpedoesImage1, -0.61 * ppm, -0.61 * ppm, 1.22 * ppm,
                    1.22 * ppm)
        }
        pop()
    }
}

class Octagon extends MissionElement {
    constructor() {
        super(createVector(2.74, 2.74), 0, 1)
        this.dhdImage = loadImage('static/images/map/dhd.png')
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
        push()
        rotate(HALF_PI)
        image(this.dhdImage, -0.61 * ppm, -0.61 * ppm, 1.22 * ppm, 1.22 * ppm)
        pop()
    }
}
