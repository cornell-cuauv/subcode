import React from "react"
import { Navbar, OverlayTrigger, Tooltip } from 'react-bootstrap'
import { CUAUV_VEHICLE, CUAUV_LOCALE} from './framework/environment.jsx'
import CONTROLLER_LOGO from '../static/images/controller.svg'

export class Controlpoint extends React.Component {
    constructor(props) {
        super(props)
        this.state = {
            active: false
        }
        window.addEventListener("keydown", (event) => {
            if (this.state.active) {
                if (event.key === "ArrowUp") fetch("/controlpoint/relative/depth/-0.1")
                if (event.key === "ArrowDown") fetch("/controlpoint/relative/depth/0.1")
                if (event.key === "ArrowLeft") fetch("/controlpoint/relative/heading/-5")
                if (event.key === "ArrowRight") fetch("/controlpoint/relative/heading/5")
                const speedMap = {'1': 0, '2': 0.1, '3': 0.2, '4': 0.3, '5': 0.5,
                    '6': 0.5, '7': 0.6, '8': 0.7, '9': 0.8, '0': 0.9, '!': 0, '@': -0.1,
                    '#': -0.2, '$': -0.3, '%': -0.4, '^': -0.5, '&': -0.6, '*': -0.7,
                    '(': -0.8, ')': -0.9}
                if (speedMap[event.key] !== undefined) {
                    fetch("/controlpoint/absolute/speed/" + speedMap[event.key])
                }
                event.preventDefault()
            }
        })
    }

    render() {
        const tooltip = (
            <Tooltip style={{fontSize: 1}}>
                                  
                <span dangerouslySetInnerHTML={{__html: CONTROLLER_LOGO}}></span>
                                  
            </Tooltip>
        )
        return (
            <OverlayTrigger placement="bottom" overlay={tooltip}>
                <Navbar.Text
                    pullRight
                    onMouseEnter={() => this.setState({active: true})}
                    onMouseLeave={() => this.setState({active: false})}
                    style={{display: 'inline-block'}}
                >
                    {CUAUV_VEHICLE} @ {CUAUV_LOCALE}
                </Navbar.Text>
            </OverlayTrigger>
        )
    }
}