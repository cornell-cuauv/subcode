class SocketManager {
    /**
     * Construct a new SocketManager object, each of which manages one socket
     * connection. This handles communication with the webserver. A manager is
     * created for each sub and, if the GUI's origin is a non-sub container,
     * the user's local server as well.
     *
     * name          -- The name of the destination, used for the indicator.
     * url           -- The url at which to find the webserver. Should start
     *                  with ws:// and end with /map/ws.
     * indicatorTopY -- The y-coordinate (in canvas-space) at which the top of
     *                  the indicator should be drawn.
     */
    constructor(name, url, indicatorTopY) {
        this.name = name
        this.url = url
        this.indicatorTopY = indicatorTopY
        this.socket = new WebSocket(url)
        this.socket.onmessage = this.receiveData
    }

    /** Close the socket if it is open, or re-establish it if it is closed. */
    toggleSocket() {
        if (this.socket.readyState == WebSocket.OPEN) {
            this.socket.close()
        } else {
            this.socket = new WebSocket(this.url)
            this.socket.onmessage = this.receiveData
        }
    }

    /**
     * Process JSON data received through the socket. This data sets the pool
     * and the properties of each mission element based on what's in the
     * dead_reckoning_virtual SHM group.
     */
    receiveData(message) {
        // TODO: Understand what's going on here.
        if (this.url === window.location.host && !shouldAcceptData) {
            return
        }

        const data = JSON.parse(message["data"])

        selectedPool = Object.values(pools).flat().find(pool =>
                pool.name === data["pool"]) || selectedPool

        // For each mission element, set its north and east coordinates and its
        // heading. For approach points, set whether or not they are enabled.
        for (const element of Object.keys(elements)) {
            elements[element].pos.x = data[element + "_north"]
            elements[element].pos.y = data[element + "_east"]
            if ((element + "_heading") in data) {
                elements[element].dir = data[element + "_heading"] * PI / 180
            }
            if ((element + "_config") in data) {
                elements[element].config = data[element + "_config"]
            }
            if (elements[element] instanceof ApproachPoint) {
                elements[element].enabled = data[element + "_in_pool"]
            }
        }
        
        updatedSinceLoad = true
        shouldAcceptData = false
    }

    /**
     * Send JSON data, derived from the mission elements, through the socket.
     * This will be written to the dead_reckoning_virtual SHM group by the
     * webserver.
     */
    sendData() {
        if (this.socket.readyState != WebSocket.OPEN) {
            return
        }
        let data = {}
        for (const element of Object.keys(elements)) {
            data[element + "_in_pool"]  = selectedPool.contains(
                    elements[element].pos) && elements[element].enabled
            data[element + "_north"]    = elements[element].pos.x
            data[element + "_east"]     = elements[element].pos.y
            data[element + "_heading"]  = elements[element].dir * 180 / PI
            data["depth_at_" + element] = selectedPool.depthAt(
                    elements[element].pos)
            if (elements[element].numConfigs > 1) {
                data[element + "_config"] = elements[element].config
            }
        }
        data["pool"] = selectedPool.name
        data["pinger_frequency"] = selectedPool.pingerFrequency
        this.socket.send(JSON.stringify(data))
    }

    /** Draw the socket's status indicator on the right side of the canvas. */
    drawIndicator() {
        // When the mouse is atop the indicator, shade its background.
        if (mouseX > 75 + selectedPool.width * ppm &&
                mouseX < 105 + selectedPool.width * ppm +
                textWidth(this.name) && mouseY > this.indicatorTopY &&
                mouseY < this.indicatorTopY + 20) {
            noStroke()
            fill(200)
            rect(75 + selectedPool.width * ppm, this.indicatorTopY,
                    30 + textWidth(this.name), 20)
        }

        // The indicator itself.
        strokeWeight(10)
        if (this.socket.readyState === WebSocket.OPEN) {
            stroke(19, 191, 80)
        } else {
            stroke(201, 23, 10)
        }
        point(85 + selectedPool.width * ppm, this.indicatorTopY + 10)
        noStroke()
        fill(0)
        text(this.name, 96 + selectedPool.width * ppm, this.indicatorTopY + 15)
    }

    /** Clicking the indicator toggles the socket. */
    handleMousePress() {
        if (mouseX > 75 + selectedPool.width * ppm &&
                mouseX < 105 + selectedPool.width * ppm +
                textWidth(this.name) && mouseY > this.indicatorTopY &&
                mouseY < this.indicatorTopY + 20) {
            this.toggleSocket()
        }       
    }
}
