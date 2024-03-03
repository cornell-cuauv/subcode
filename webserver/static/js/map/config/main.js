// Pixels per meter. Smaller values make the pool appear smaller in the webgui.
const ppm = 20

// Maps a category name to the array of pools in that category.
const pools = {
    "Cornell": [new Teagle()],
    "Semifinals": [new SemisA(), new SemisB(), new SemisC(), new SemisD()],
    "Finals": [new FinalsAB(), new FinalsCD()]
}

// An initial pool for when the webgui is started.
let selectedPool = pools["Cornell"][0]

// This function is responsible for returning a dictionary of elements, mapping
// their names to MissionElement objects.
function setupCustomElements() {
    return {
        "gate": new Gate(),
        "buoys": new Buoys(),
        "bins": new Bins(),
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
