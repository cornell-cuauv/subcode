// Note: From config/main.js, gets ppm, pools, selectedPool,
// setupCustomElements(), and subDimensions(). See details there.

let elements
let buttons
let websockets
let updatedSinceSave = false
let updatedSinceLoad = false
let shouldAcceptData = true

/** Called once when the GUI is loaded. */
function setup() {
    createCanvas(windowWidth, windowHeight)
    elements = setupElements()
    selectedPool.setDefaultPositions(elements)
    buttons = setupButtons(elements)
    websockets = establishWebSockets()
}

/**
 * Populate the elements array with the custom elements defined in the config,
 * their approach points, and the sub.
 */
function setupElements() {
    let elements = setupCustomElements()
    for (let element of Object.keys(elements)) {
        const approachPoint = new ApproachPoint()
        elements[element].approachPoint = approachPoint
        elements[element + "_approach"] = approachPoint
    }
    elements["sub"] = new Sub(subDimensions())
    return elements
}

/**
 * Populate the buttons array with category and pool selection buttons, element
 * configuration toggle buttons, the "Load preset" button, and the "Save to SHM"
 * button.
 */
function setupButtons(elements) {
    let buttons = []

    // Category and pool buttons.
    textSize(15)
    let categoryCornerX = 50
    for (let category of Object.keys(pools)) {
        // The category button.
        buttons.push(makeCategoryButton(categoryCornerX, category,
                pools[category]))
        categoryCornerX += textWidth(category) + 23

        // The associated pool buttons.
        let poolCornerX = 50
        for (let pool of pools[category]) {
            buttons.push(makePoolButton(poolCornerX, pool))
            poolCornerX += textWidth(pool.name) + 23
        }
    }
    
    // Next config buttons.
    let cornerY = 103
    let numNextConfigButtons = 0
    for (let element of Object.keys(elements)) {
        if (elements[element].numConfigs > 1) {
            buttons.push(makeNextConfigButton(cornerY, element))
            cornerY += 40
            numNextConfigButtons++
        }
    }

    buttons.push(makeLoadPresetButton(numNextConfigButtons))
    buttons.push(makeSaveToShmButton())

    return buttons
}

/**
 * Establish web socket connections with mainsub, minisub, and (if the webgui
 * was served from a local docker container) the simulator. This allows the
 * mapping tool to send data to both subs simultaneously.
 */
function establishWebSockets() {
    let mainsubTopY = 103 + 40 * (Object.values(elements).filter(element =>
            element.numConfigs > 1).length + 1)
    let websockets = []
    websockets.push(new SocketManager('Mainsub',
            'ws://192.168.0.93:8080/map/ws', mainsubTopY))
    websockets.push(new SocketManager('Minisub',
            'ws://192.168.0.91:8080/map/ws', mainsubTopY + 25))
    if (CUAUV_LOCALE === 'simulator') {
        websockets.push(new SocketManager('Simulator',
                'ws://' + window.location.host + '/map/ws', mainsubTopY + 50))
    }
    return websockets
}

/** Called every frame, ~60 times per second. */
function draw() {
    background(255)
    selectedPool.drawPool()
    buttons.forEach(button => { button.draw() })
    websockets.forEach(manager => manager.drawIndicator())
    writeUsageInstructions()

    // Draw and update each enabled element (e.g. not disabled approach points).
    // See the functions' implementations (in missionelement.js) for more info.
    const enabled = Object.values(elements).filter(element => element.enabled)
    enabled.forEach(element => element.moveIfDragging())
    enabled.forEach(element => element.draw())
}

/** Write usage instructions below the pool. */
function writeUsageInstructions() {
    textSize(12)
    noStroke()
    fill(0)
    text(`Drag mission elements to their real-world locations.
After selecting an element, use ',' and '.' to rotate it.
Leave elements outside the bounds of the pool to mark them not present.
When an element is selected, press 'a' to toggle its approach point.`,
            50, 130 + selectedPool.height * ppm)
        
}

/** Called each time the mouse is pressed. */
function mousePressed() {
    buttons.forEach(button => button.handleMousePress())
    Object.values(elements)
        .filter(element => element.enabled)
        .forEach(element => element.handleMousePress())
    websockets.forEach(manager => manager.handleMousePress())
}

/** Called each time the mouse is released. */
function mouseReleased() {
    Object.values(elements)
        .filter(element => element.enabled)
        .forEach(element => element.handleMouseRelease())
}

/** Called each time any key is pressed. */
function keyPressed() {
    Object.values(elements)
        .filter(element => element.enabled)
        .forEach(element => element.handleKeyPress())
}

/** Return a (canvas-space) vector from the origin to the mouse pointer. */
function mouseVector() {
    return createVector(mouseX, mouseY)
}

/** Convert a pool-space vector to canvas-space. */
function toCanvasSpace(vector) {
    return createVector(50 + vector.x * ppm, 100 + vector.y * ppm)
}

/** Convert a canvas-space vector to pool-space. */
function toPoolSpace(vector) {
    return createVector((vector.x - 50) / ppm, (vector.y - 100) / ppm)
}

/**
 * Send JSON data, derived from the mission element, through each connected
 * websocket. This will be written to the dead_reckoning_virtual SHM group by
 * the webserver.
 */
function sendDataThroughWebsockets() {
    websockets.forEach(websocket => websocket.sendData())
}

