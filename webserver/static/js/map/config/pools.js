class Semis extends Pool {
    setDefaultPositions(elements) {
        elements["sub"].pos = createVector(this.width / 2, this.height - 0.8)
        elements["sub"].dir = HALF_PI
        elements["gate_approach"].pos = createVector(this.width / 2, this.height - 2.5)
        elements["gate_approach"].enabled = false
        elements["gate"].pos = createVector(this.width / 2, this.height - 5)
        elements["gate"].dir = HALF_PI
        elements["buoy_approach"].pos = createVector(this.width / 2, this.height * 2 / 3)
        elements["buoy_approach"].enabled = false
        elements["buoy"].pos = createVector(this.width * 2 / 3, this.height * 2 / 3)
        elements["buoy"].dir = 0
        elements["bin_approach"].pos = createVector(this.width / 2, this.height / 2)
        elements["bin_approach"].enable = false
        elements["bin"].pos = createVector(this.width / 3, this.height / 2)
        elements["bin"].dir = 0
        elements["torpedoes_approach"].pos = createVector(this.width / 2, this.height / 3)
        elements["torpedoes_approach"].enabled = true
        elements["torpedoes"].pos = createVector(this.width * 2 / 3, this.height / 3)
        elements["torpedoes"].dir = HALF_PI
        elements["octagon_approach"].pos = createVector(this.width / 2, this.width * 2 / 3)
        elements["octagon_approach"].enabled = false
        elements["octagon"].pos = createVector(this.width / 2, this.height / 5)
        elements["octagon"].dir = 0
    }
}

class Finals extends Semis {
    constructor() {
        super('Finals', 26.37, 22.86, true, [[0, 2.13]], 0)
    }
    
    drawAlignmentFeatures() {
        strokeWeight(0.33 * ppm)
        strokeCap(SQUARE)
        stroke(0, 0, 255)
        for(let y = 0; y < 8; y++) {
            line(50, 100 + (1.83 + 2.74 * y) * ppm, 50 + this.width * ppm, 100 + (1.83 + 2.74 * y) * ppm)
        }
        stroke(0)
        for (let x = 0; x < 9; x++) {
            line(50 + (this.width - 3.05 - 2.74 * x) * ppm, 100 + 1.83 * ppm, 50 + (this.width - 3.05 - 2.74 * x) * ppm, 100 + (this.height - 1.83) * ppm)
        }
    }
}

class SemisA extends Semis {
    constructor() {
        super('A', 12.65, 22.86, true, [[0, 2.13]], 0)
    }

    drawAlignmentFeatures() {
        strokeWeight(0.33 * ppm)
        strokeCap(SQUARE)
        stroke(0, 0, 255)
        for(let y = 0; y < 8; y++) {
            line(50, 100 + (1.83 + 2.74 * y) * ppm, 50 + (this.width - 2.13) * ppm, 100 + (1.83 + 2.74 * y) * ppm)
        }
        stroke(0)
        for (let x = 0; x < 4; x++) {
            line(50 + (this.width - 3.05 - 2.74 * x) * ppm, 100 + 1.83 * ppm, 50 + (this.width - 3.05 - 2.74 * x) * ppm, 100 + (this.height - 1.83) * ppm)}
    }
}

class SemisB extends Semis {
    constructor() {
        super('B', 13.72, 22.86, true, [[0, 2.13]], 0)
    }

    drawAlignmentFeatures() {
        strokeWeight(0.33 * ppm)
        strokeCap(SQUARE)
        stroke(0, 0, 255)
        for(let y = 0; y < 8; y++) {
            line(50, 100 + (1.83 + 2.74 * y) * ppm, 50 + this.width * ppm, 100 + (1.83 + 2.74 * y) * ppm)
        }
        stroke(0)
        for (let x = 0; x < 5; x++) {
            line(50 + (1.37 + 2.74 * x) * ppm, 100 + 1.83 * ppm, 50 + (1.37 + 2.74 * x) * ppm, 100 + (this.height - 1.83) * ppm)
        }
    }
}

class SemisC extends Semis {
    constructor() {
        super('C', 10.97, 22.86, true, [[0, 2.13]], 0)
    }

    drawAlignmentFeatures() {
        strokeWeight(0.33 * ppm)
        strokeCap(SQUARE)
        stroke(0, 0, 255)
        for(let y = 0; y < 8; y++) {
            line(50, 100 + (1.83 + 2.74 * y) * ppm, 50 + this.width * ppm, 100 + (1.83 + 2.74 * y) * ppm)
        }
        stroke(0)
        for (let x = 0; x < 4; x++) {
            line(50 + (1.37 + 2.74 * x) * ppm, 100 + 1.83 * ppm, 50 + (1.37 + 2.74 * x) * ppm, 100 + (this.height - 1.83) * ppm)}
    }
}

class SemisD extends Semis {
    constructor() {
        super('D', 12.65, 22.86, true, [[0, 2.13]], 0)
    }

    drawAlignmentFeatures() {
        strokeWeight(0.33 * ppm)
        strokeCap(SQUARE)
        stroke(0, 0, 255)
        for(let y = 0; y < 8; y++) {
            line(50 + 2.13 * ppm, 100 + (1.83 + 2.74 * y) * ppm, 50 + this.width * ppm, 100 + (1.83 + 2.74 * y) * ppm)
        }
        stroke(0)
        for (let x = 0; x < 4; x++) {
            line(50 + (3.05 + 2.74 * x) * ppm, 100 + 1.83 * ppm, 50 + (3.05 + 2.74 * x) * ppm, 100 + (this.height - 1.83) * ppm)}
    }
}
