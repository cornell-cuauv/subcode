class Teagle extends Pool {
    constructor() {
        super('Teagle', 12.2, 22.8, true, [[0, 1.2], [3.9, 1.8], [7.0, 2.4],
                [10.4, 3.1], [13.6, 3.7], [17.2, 4.3]], 0)
    }

    drawAlignmentFeatures() {
        strokeWeight(1 / 3 * ppm)
        stroke(0, 50)
        strokeCap(SQUARE)
        for (let i = 1; i < 7; i++) {
            line(50 + this.width * i / 7 * ppm, 100 + 1 * ppm,
                    50 + this.width * i / 7 * ppm,
                    100 + (this.height - 1) * ppm)
        }
        noStroke()
        fill(120)
        ellipse(40, 100 + 4.5 * ppm, 5, 5)
        ellipse(40, 100 + (this.height - 4.5) * ppm, 5, 5)
        ellipse(50 + this.width * ppm + 10, 100 + 4.5 * ppm, 5, 5)
        ellipse(50 + this.width * ppm + 10, 100 + (this.height - 4.5) * ppm,
                5, 5)
    }
}

class SemisA extends Pool {
    constructor() {
        super('Semis A', 11.41, 22.8, false, [[0, 4.1], [7.1, 4.1],
                [49.4, 2.4]], 30000)
    }

    drawAlignmentFeatures() {
        strokeWeight(1 / 3 * ppm)
        stroke(0, 50)
        strokeCap(SQUARE)
        for (let x = 4.01; x < this.width; x += 2.135) {
            line(50 + x * ppm, 100 + 1.8 * ppm, 50 + x * ppm, 100 + (this.height - 1.8) * ppm)
        }
        for (let y = 1.8; y < this.height; y += 2.75) {
            line(50 + 4.01 * ppm, 100 + y * ppm, 50 + this.width * ppm, 100 + y * ppm)
        }
    }

    setDefaultPositions(elements) {
        elements["sub"].pos = createVector(this.width / 2, 0.7)
        elements["sub"].dir = HALF_PI
        elements["gate_approach"].pos = createVector(this.width / 4,
                this.height / 12)
        elements["gate_approach"].enabled = true
        elements["gate"].pos = createVector(this.width / 4, this.height / 6)
        elements["gate"].dir = HALF_PI
        elements["buoys_approach"].pos = createVector(this.width * 3 / 4,
                this.height * 3 / 12)
        elements["buoys_approach"].enabled = true
        elements["buoys"].pos = createVector(this.width * 3 / 4,
                this.height * 2 / 6)
        elements["buoys"].dir = HALF_PI
        elements["bins_approach"].pos = createVector(this.width / 4,
                this.height * 5 / 12)
        elements["bins_approach"].enabled = true
        elements["bins"].pos = createVector(this.width / 4, this.height * 3 / 6)
        elements["bins"].dir = HALF_PI
        elements["torpedoes_approach"].pos = createVector(this.width / 2,
                this.height / 2)
        elements["torpedoes_approach"].enabled = true
        elements["torpedoes"].pos = createVector(this.width * 3 / 4,
                this.height * 4 / 6)
        elements["torpedoes"].dir = HALF_PI
        elements["octagon_approach"].pos = createVector(this.width / 4,
                this.height * 8 / 12)
        elements["octagon_approach"].enabled = true
        elements["octagon"].pos = createVector(this.width / 4,
                this.height * 5 / 6)
        elements["octagon"].dir = 0
    }
}

class SemisB extends Pool {
    constructor() {
        super('Semis B', 13.47, 22.8, false, [[-12.2, 4.1], [-5.1, 4.1],
                [37.2, 2.4]], 40000)
    }

    drawAlignmentFeatures() {
        strokeWeight(1 / 3 * ppm)
        stroke(0, 50)
        strokeCap(SQUARE)
        for (let x = 1.00; x < this.width; x += 2.135) {
            line(50 + x * ppm, 100 + 1.8 * ppm, 50 + x * ppm, 100 + (this.height - 1.8) * ppm)
        }
        for (let y = 1.8; y < this.height; y += 2.75) {
            line(50, 100 + y * ppm, 50 + this.width * ppm, 100 + y * ppm)
        }
    }

    setDefaultPositions(elements) {
        elements["sub"].pos = createVector(this.width / 2, this.height - 0.7)
        elements["sub"].dir = -HALF_PI
        elements["gate_approach"].pos = createVector(this.width * 3 / 4,
                this.height * 11 / 12)
        elements["gate_approach"].enabled = true
        elements["gate"].pos = createVector(this.width * 3 / 4,
                this.height * 5 / 6)
        elements["gate"].dir = -HALF_PI
        elements["buoys_approach"].pos = createVector(this.width / 4,
                this.height * 9 / 12)
        elements["buoys_approach"].enabled = true
        elements["buoys"].pos = createVector(this.width / 4,
                this.height * 4 / 6)
        elements["buoys"].dir = -HALF_PI
        elements["bins_approach"].pos = createVector(this.width * 3 / 4,
                this.height * 7 / 12)
        elements["bins_approach"].enabled = true
        elements["bins"].pos = createVector(this.width * 3 / 4,
                this.height * 3 / 6)
        elements["bins"].dir = -HALF_PI
        elements["torpedoes_approach"].pos = createVector(this.width / 2,
                this.height / 2)
        elements["torpedoes_approach"].enabled = true
        elements["torpedoes"].pos = createVector(this.width / 4,
                this.height * 2 / 6)
        elements["torpedoes"].dir = -HALF_PI
        elements["octagon_approach"].pos = createVector(this.width * 3 / 4,
                this.height * 4 / 12)
        elements["octagon_approach"].enabled = true
        elements["octagon"].pos = createVector(this.width * 3 / 4,
                this.height / 6)
        elements["octagon"].dir = PI
    }
}

class SemisC extends Pool {
    constructor() {
        super('Semis C', 13.53, 22.8, false, [[-25, 4.1], [-17.9, 4.1],
                [24.4, 2.4]], 25000)
    }

    drawAlignmentFeatures() {
        strokeWeight(1 / 3 * ppm)
        stroke(0, 50)
        strokeCap(SQUARE)
        for (let x = 1.04; x < 8; x += 2.135) {
            line(50 + x * ppm, 100 + 1.8 * ppm, 50 + x * ppm, 100 + (this.height - 1.8) * ppm)
        }
        for (let y = 1.8; y < this.height; y += 2.75) {
            line(50, 100 + y * ppm, 50 + (this.width - 4.10) * ppm, 100 + y * ppm)
        }
    }

    setDefaultPositions(elements) {
        elements["sub"].pos = createVector(this.width / 2, 0.7)
        elements["sub"].dir = HALF_PI
        elements["gate_approach"].pos = createVector(this.width / 4,
                this.height / 12)
        elements["gate_approach"].enabled = true
        elements["gate"].pos = createVector(this.width / 4, this.height / 6)
        elements["gate"].dir = HALF_PI
        elements["buoys_approach"].pos = createVector(this.width * 3 / 4,
                this.height * 3 / 12)
        elements["buoys_approach"].enabled = true
        elements["buoys"].pos = createVector(this.width * 3 / 4,
                this.height * 2 / 6)
        elements["buoys"].dir = HALF_PI
        elements["bins_approach"].pos = createVector(this.width / 4,
                this.height * 5 / 12)
        elements["bins_approach"].enabled = true
        elements["bins"].pos = createVector(this.width / 4, this.height * 3 / 6)
        elements["bins"].dir = HALF_PI
        elements["torpedoes_approach"].pos = createVector(this.width / 2,
                this.height / 2)
        elements["torpedoes_approach"].enabled = true
        elements["torpedoes"].pos = createVector(this.width * 3 / 4,
                this.height * 4 / 6)
        elements["torpedoes"].dir = HALF_PI
        elements["octagon_approach"].pos = createVector(this.width / 4,
                this.height * 8 / 12)
        elements["octagon_approach"].enabled = true
        elements["octagon"].pos = createVector(this.width / 4,
                this.height * 5 / 6)
        elements["octagon"].dir = 0
    }
}

class SemisD extends Pool {
    constructor() {
        super('Semis D', 11.45, 22.8, false, [[-37.2, 4.1], [-30.1, 4.1],
                [12.2, 2.4]], 35000)
    }

    drawAlignmentFeatures() {
        strokeWeight(1 / 3 * ppm)
        stroke(0, 50)
        strokeCap(SQUARE)
        for (let x = 1.04; x < 8; x += 2.135) {
            line(50 + x * ppm, 100 + 1.8 * ppm, 50 + x * ppm, 100 + (this.height - 1.8) * ppm)
        }
        for (let y = 1.8; y < this.height; y += 2.75) {
            line(50, 100 + y * ppm, 50 + (this.width - 4.10) * ppm, 100 + y * ppm)
        }
    }

    setDefaultPositions(elements) {
        elements["sub"].pos = createVector(this.width / 2, this.height - 0.7)
        elements["sub"].dir = -HALF_PI
        elements["gate_approach"].pos = createVector(this.width * 3 / 4,
                this.height * 11 / 12)
        elements["gate_approach"].enabled = true
        elements["gate"].pos = createVector(this.width * 3 / 4,
                this.height * 5 / 6)
        elements["gate"].dir = -HALF_PI
        elements["buoys_approach"].pos = createVector(this.width / 4,
                this.height * 9 / 12)
        elements["buoys_approach"].enabled = true
        elements["buoys"].pos = createVector(this.width / 4,
                this.height * 4 / 6)
        elements["buoys"].dir = -HALF_PI
        elements["bins_approach"].pos = createVector(this.width * 3 / 4,
                this.height * 7 / 12)
        elements["bins_approach"].enabled = true
        elements["bins"].pos = createVector(this.width * 3 / 4,
                this.height * 3 / 6)
        elements["bins"].dir = -HALF_PI
        elements["torpedoes_approach"].pos = createVector(this.width / 2,
                this.height / 2)
        elements["torpedoes_approach"].enabled = true
        elements["torpedoes"].pos = createVector(this.width / 4,
                this.height * 2 / 6)
        elements["torpedoes"].dir = -HALF_PI
        elements["octagon_approach"].pos = createVector(this.width * 3 / 4,
                this.height * 4 / 12)
        elements["octagon_approach"].enabled = true
        elements["octagon"].pos = createVector(this.width * 3 / 4,
                this.height / 6)
        elements["octagon"].dir = PI
    }
}

class FinalsAB extends Pool {
    constructor() {
        super('Finals A + B', 24.88, 22.8, false, [[0, 4.1], [7.1, 4.1],
                [49.4, 2.4]], 0)
    }

    drawAlignmentFeatures() {
        strokeWeight(1 / 3 * ppm)
        stroke(0, 50)
        strokeCap(SQUARE)
        for (let x = 4.01; x < this.width; x += 2.135) {
            line(50 + x * ppm, 100 + 1.8 * ppm, 50 + x * ppm,
                    100 + (this.height - 1.8) * ppm)
        }
        for (let y = 1.8; y < this.height; y += 2.75) {
            line(50 + 4.01 * ppm, 100 + y * ppm, 50 + this.width * ppm,
                    100 + y * ppm)
        }
    }
}

class FinalsCD extends Pool {
    constructor() {
        super('Finals C + D', 24.98, 22.8, false, [[-25, 4.1], [-17.9, 4.1],
                [24.4, 2.4]], 0)
    }

    drawAlignmentFeatures() {
        strokeWeight(1 / 3 * ppm)
        stroke(0, 50)
        strokeCap(SQUARE)
        for (let x = 1.79; x < 21.53; x += 2.135) {
            line(50 + x * ppm, 100 + 1.8 * ppm, 50 + x * ppm,
                    100 + (this.height - 1.8) * ppm)
        }
        for (let y = 1.8; y < this.height; y += 2.75) {
            line(50, 100 + y * ppm, 50 + (this.width - 4.10) * ppm,
                    100 + y * ppm)
        }
    }
}
