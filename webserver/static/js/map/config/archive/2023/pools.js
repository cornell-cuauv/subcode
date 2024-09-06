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

    setDefaultPositions(elements) {        
        elements["sub"].pos = createVector(this.width / 2, 0.7)
        elements["sub"].dir = HALF_PI
        elements["gate_approach"].pos = createVector(this.width / 4,
                this.height / 12)
        elements["gate_approach"].enabled = true
        elements["gate"].pos = createVector(this.width / 4, this.height / 6)
        elements["gate"].dir = HALF_PI
        elements["buoy_approach"].pos = createVector(this.width * 3 / 4,
                this.height * 3 / 12)
        elements["buoy_approach"].enabled = true
        elements["buoy"].pos = createVector(this.width * 3 / 4,
                this.height * 2 / 6)
        elements["buoy"].dir = HALF_PI
        elements["earth_bin_approach"].pos = createVector(this.width / 4,
                this.height * 5 / 12)
        elements["earth_bin_approach"].enabled = true
        elements["earth_bin"].pos = createVector(this.width / 4, this.height * 3 / 6)
        elements["earth_bin"].dir = 0
        elements["abydos_bin_approach"].enabled = false
        elements["abydos_bin"].pos = createVector(this.width / 4 + 1, this.height * 3 / 6)
        elements["abydos_bin"].dir = 0
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

class SemisAorD extends Pool {
    constructor() {
        super('Semis A or D', 45.72, 30.48, true, [[0, 4.88]], 30000)
    }

    drawAlignmentFeatures() {
        // Make the pool a quarter-ellipse
        noStroke()
        fill(255)
        rect(50, 100, this.width * ppm + 1, this.height * ppm + 1)
        fill(91, 155, 213)
        arc(50, 100, 2 * 45.72 * ppm, 2 * 30.48 * ppm, 0, HALF_PI)

        // Draw the deeper circle darker
        fill(71, 135, 193)
        arc(50, 100, 49 * ppm, 49 * ppm, 0, HALF_PI)

        // Draw the dock
        fill(0, 0, 0)
        rect(50 + 7 * ppm, 100 + this.height * ppm - 3.1 * ppm, 6 * ppm, 1.85 * ppm)
    }

    setDefaultPositions(elements) {
        elements["sub"].pos = createVector(10, 26.95)
        elements["sub"].dir = PI * 3 / 2
        elements["gate"].pos = createVector(15, 25)
        elements["gate"].dir = -HALF_PI / 4
        elements["gate_approach"].pos = createVector(15 - 0.92 * 3, 25 + 0.38 * 3)
        elements["gate_approach"].enabled = false
        elements["buoy"].pos = createVector(25, 21)
        elements["buoy"].dir = -HALF_PI / 4
        elements["buoy_approach"].pos = createVector(25 - 0.92 * 3, 21 + 0.38 * 3)
        elements["buoy_approach"].enabled = false
        elements["earth_bin"].pos = createVector(30, 17)
        elements["earth_bin"].dir = 0
        elements["earth_bin_approach"].pos = createVector(29, 17)
        elements["earth_bin_approach"].enabled = false
        elements["abydos_bin"].pos = createVector(31, 17)
        elements["abydos_bin"].dir = 0
        elements["abydos_bin_approach"].pos = createVector(29, 17)
        elements["abydos_bin_approach"].enabled = false
        elements["torpedoes"].pos = createVector(25, 10)
        elements["torpedoes"].dir = -HALF_PI
        elements["torpedoes_approach"].pos = createVector(25, 15)
        elements["torpedoes_approach"].enabled = true
        elements["octagon"].pos = createVector(40, 5)
        elements["octagon"].dir = 0
        elements["octagon_approach"].pos = createVector(35, 10)
        elements["octagon_approach"].enabled = true
    }
}

class SemisBorC extends Pool {
    constructor() {
        super('Semis B or C', 45.72, 30.48, true, [[0, 4.88]], 30000)
    }

    drawAlignmentFeatures() {
        // Make the pool a quarter-ellipse
        noStroke()
        fill(255)
        rect(50, 100, this.width * ppm + 1, this.height * ppm + 1)
        fill(91, 155, 213)
        arc(50 + this.width * ppm, 100, 2 * 45.72 * ppm, 2 * 30.48 * ppm, HALF_PI, PI)

        // Draw the deeper circle darker
        fill(71, 135, 193)
        arc(50 + this.width * ppm, 100, 49 * ppm, 49 * ppm, HALF_PI, PI)

        // Draw the dock
        fill(0, 0, 0)
        rect(50 + (this.width - 13) * ppm, 100 + this.height * ppm - 3.1 * ppm, 6 * ppm, 1.85 * ppm)
    }

    setDefaultPositions(elements) {
        elements["sub"].pos = createVector(35.72, 26.95)
        elements["sub"].dir = PI * 3 / 2
        elements["gate"].pos = createVector(30.72, 25)
        elements["gate"].dir = PI + HALF_PI / 4
        elements["gate_approach"].pos = createVector(30.72 + 0.92 * 3, 25 + 0.38 * 3)
        elements["gate_approach"].enabled = false
        elements["buoy"].pos = createVector(20.72, 21)
        elements["buoy"].dir = PI + HALF_PI / 4
        elements["buoy_approach"].pos = createVector(20.72 + 0.92 * 3, 21 + 0.38 * 3)
        elements["buoy_approach"].enabled = false
        elements["earth_bin"].pos = createVector(15.72, 17)
        elements["earth_bin"].dir = PI
        elements["earth_bin_approach"].pos = createVector(16.72, 17)
        elements["earth_bin_approach"].enabled = false
        elements["abydos_bin"].pos = createVector(14.72, 17)
        elements["abydos_bin"].dir = PI
        elements["abydos_bin_approach"].pos = createVector(16.72, 17)
        elements["abydos_bin_approach"].enabled = false
        elements["torpedoes"].pos = createVector(20.72, 10)
        elements["torpedoes"].dir = -HALF_PI
        elements["torpedoes_approach"].pos = createVector(20.72, 15)
        elements["torpedoes_approach"].enabled = true
        elements["octagon"].pos = createVector(5.72, 5)
        elements["octagon"].dir = 0
        elements["octagon_approach"].pos = createVector(10.72, 10)
        elements["octagon_approach"].enabled = true
    }
}