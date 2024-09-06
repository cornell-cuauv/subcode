// Pixels per meter. Smaller values make the pool appear smaller in the webgui.
const ppm = 15

// Maps a category name to the array of pools in that category.
const pools = {
    "Cornell": [new Teagle()],
    "Semis": [new SemisAorD(), new SemisBorC()]
}

// An initial pool for when the webgui is started.
let selectedPool = pools["Cornell"][0]

// This function is responsible for returning a dictionary of elements, mapping
// their names to MissionElement objects.
function setupCustomElements() {
    return {
        "gate": new Gate(),
        "buoy": new Buoy(),
        "earth_bin": new EarthBin(),
        "abydos_bin": new AbydosBin(),
        "torpedoes": new Torpedoes(),
        "octagon": new Octagon()
    }
}

// This function is responsible for returning a vector, the x-coordinate of
// which gives the sub's length in meters, and the y-coordinate of which gives
// the sub's width.
function subDimensions() {
    return createVector(0.89, 0.63)
}
