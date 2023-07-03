class Button {
    /**
     * Construct a new Button object. This is a general purpose class for
     * displaying a label on the screen which does something when clicked.
     *
     * title        -- The text to display on the button.
     * strokeColor  -- The button's outline color, when it is enabled.
     * fillColor    -- The button's fill color, when it is enabled.
     * onClick      -- A function which is run when the button is clicked.
     */
    constructor(title, strokeColor, fillColor) {
        this.title = title
        this.strokeColor = strokeColor
        this.fillColor = fillColor
    }

    /*
     * Return the position (as a canvas-space vector) at which the button's
     * upper-left corner should appear. Must be overridden by instances.
     */
    corner() { return createVector(0, 0) }

    /* 
     * Return if the button should appear colored as opposed to gray. Can be
     * overridden by instanced.
     */
    colored() { return true }

    /*
     * Return if the button should be visible and clickable. Can be overridden
     * by instances.
     */
    visible() { return true }

    /**
     * Do anything. Called when the button is clicked. Must be overridden by
     * instances.
     */
    onClick() { }

    /** Draw the button if it is visible. */
    draw() {
        if (!this.visible()) return
        strokeWeight(5)
        stroke(this.colored() ? this.strokeColor : 149)
        fill(this.colored() ? this.fillColor : 179)
        textSize(15)
        rect(this.corner().x, this.corner().y, textWidth(this.title) + 10, 25)
        noStroke()
        fill(0)
        text(this.title, this.corner().x + 5, this.corner().y + 18)
    }

    /** Call this.onClick with the button is clicked. */
    handleMousePress() {
        if (!this.visible()) return
        textSize(15)
        if (this.corner().x < mouseX &&
                mouseX < this.corner().x + textWidth(this.title) + 10 &&
                this.corner().y < mouseY && mouseY < this.corner().y + 25) {
            this.onClick()
        }
    }
}

/**
 * Creates (and returns) a specialized instance of the Button class which
 * switches the selected pool when clicked.
 *
 * leftX -- The x-coordinate of the left side of the button.
 * pool  -- The pool which clicking the created button selected.
 */
function makePoolButton(leftX, pool) {
    const button = new Button(pool.name, color(61, 125, 183),
            color(91, 155, 213))
    button.corner = () => createVector(leftX, 42)
    button.colored = () => selectedPool === pool
    button.visible = () => Object.values(pools).find(category =>
            category.includes(selectedPool)).includes(pool)
    button.onClick = () => {
        selectedPool = pool
        udpatedSinceSave = true
        updatedSinceLoad = true
    }
    return button
}

/**
 * Creates (and returns) a specialized instance of the Button class which
 * switches the category of pool buttons shown above the pool. Also switches
 * the selected pool to the first pool in the newly selected category.
 *
 * leftX -- The x-coordinate of the left side of the button.
 * name  -- The name of the category.
 */
function makeCategoryButton(leftX, name) {
    const button = new Button(name, color(61, 125, 183), color(91, 155, 213))
    button.corner = () => createVector(leftX, 3)
    button.colored = () => pools[name].includes(selectedPool)
    button.onClick = () => {
        selectedPool = pools[name][0]
        updatedSinceSave = true
        updatedSinceLoad = true
    }
    return button
}

/**
 * Creates (and returns) a specialized instance of the Button class which
 * which cycles the configuration of a given element.
 *
 * topY        -- The y-coordinate of the top of the button.
 * elementName -- The name of the element the button configures.
 */
function makeNextConfigButton(topY, elementName) {
    const button = new Button("Next " + elementName + " config", color(149),
            color(179))
    button.corner = () => createVector(80 + selectedPool.width * ppm, topY)
    button.onClick = () => {
        elements[elementName].config += 1
        elements[elementName].config %= elements[elementName].numConfigs
        updatedSinceSave = true
        updatedSinceLoad = true
    }
    return button
}

/**
 * Creates (and returns) a specialized instance of the Button class which loads
 * the selected pool's default positions and orientations for elements.
 *
 * numNextConfigButtons -- The total number of buttons which change element
 *                         configurations. This is needed because the load
 *                         preset button appears below ala these configuration
 *                         buttons and needs to place itself.
 */
function makeLoadPresetButton(numNextConfigButtons) {
    const button = new Button("Load preset", color(50, 168, 92),
            color(19, 191, 80))
    button.corner = () => createVector(80 + selectedPool.width * ppm,
            103 + 40 * numNextConfigButtons)
    button.visible = () => updatedSinceLoad
    button.onClick = () => {
        selectedPool.setDefaultPositions(elements)
        updatedSinceSave = true
        updatedSinceLoad = false
    }
    return button
}

/**
 * Creates (and returns) a specialized instance of the Button class which sends
 * the state of elements to the the webserver.
 */
function makeSaveToShmButton() {
    const button = new Button("Save to SHM", color(50, 168, 92),
            color(19, 191, 80))
    button.corner = () => createVector(50, 190 + selectedPool.height * ppm)
    button.visible = () => updatedSinceSave
    button.onClick = () => {
        updatedSinceSave = false
        sendDataThroughWebsockets()
    }
    return button
}
