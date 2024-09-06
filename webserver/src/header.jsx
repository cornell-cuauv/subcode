import React from 'react'
import { Nav, Navbar, NavItem} from 'react-bootstrap'
import { LinkContainer } from 'react-router-bootstrap'
import { StatusIndicator } from './framework/statusIndicator.jsx'
import { Controlpoint } from './controlpoint.jsx'
import CUAUV_LOGO_INVERSE from '../static/images/cuauv-inverse.svg'

class HeaderLinks extends React.Component {
    constructor(props) {
        super(props);
    }

    generateLinks() {
        return this.props.links.map(link => (
            // we want "exact" matching for the url === location.pathname
            <LinkContainer exact key={link.name} to={link.path} activeClassName="active">
                <NavItem eventKey={link.name} onClick={window.location.reload}>{link.name}</NavItem>
            </LinkContainer>
        ));
    }

    render() {
        return (
            <Nav>
                {this.generateLinks()}
            </Nav>
        );

    }
}

export class Header extends React.Component {
    constructor(props) {
        super(props);
        this.host = window.location.host;
        this.state = {
            thinWindow: window.innerWidth < 768
        }
        window.addEventListener("resize", () => this.setState({thinWindow: window.innerWidth < 768}))
    }

    render() {
        return (
            <Navbar inverse collapseOnSelect>
                <Navbar.Header>
                    <Navbar.Brand>
                        <a class="navbar-brand" href="/">
                            <div class="navbar-logo" dangerouslySetInnerHTML={{__html: CUAUV_LOGO_INVERSE}} />
                            <StatusIndicator />
                        </a>
                    </Navbar.Brand>
                    <Navbar.Toggle />
                    {this.state.thinWindow ? <Controlpoint /> : null}
                </Navbar.Header>
                <Navbar.Collapse>
                    <HeaderLinks links={this.props.links} />
                    {this.state.thinWindow ? null : <Controlpoint />}
                </Navbar.Collapse>
            </Navbar>
        );
    }
}
