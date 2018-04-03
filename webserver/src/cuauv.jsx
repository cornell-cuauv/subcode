import React from 'react'
import {render} from 'react-dom'
import {Route, BrowserRouter} from 'react-router-dom'

import {Header} from './header.jsx'
import {Deadman} from './framework/deadman.jsx'
import {Index} from './modules/index.jsx'
import {Drive} from './modules/drive.jsx'
import {Test} from './modules/test.jsx'
import {SHM} from './modules/shm.jsx'
import {Admin} from './modules/admin.jsx'
import {VisionGuiIndex} from './modules/vision_gui_index.jsx'
import {VisionGuiModule} from './modules/vision_gui_module.jsx'

const blueprint = [
    {
        name: "Index",
        path: "/",
        component: Index,
        headerInclude: true,
    },
    {
        name: "Drive",
        path: "/drive",
        component: Drive,
        headerInclude: true,
    },
    {
        name: "Test",
        path: "/test",
        component: Test,
        headerInclude: true,
    },
    {
        name: "SHM",
        path: "/shm",
        component: SHM,
        headerInclude: true,
    },
    {
        name: "Admin",
        path: "/admin",
        component: Admin,
        headerInclude: true,
    },
    {
        name: "Vision GUI",
        path: "/vision-gui",
        component: VisionGuiIndex,
        headerInclude: true,
    },
    {
        name: "Vision GUI Module",
        path: "/vision-gui/:module",
        component: VisionGuiModule,
        headerInclude: false,
    },
];

function generateRoutes() {
    return (
        blueprint.map(component =>
            // we want "exact" matching for the url === location.pathname
            <Route exact key={component.name} path={component.path} component={component.component} />
        )
    );
}

class Layout extends React.Component {
    render() {
        return (
            <div>
                <Header links={blueprint.filter(component => component.headerInclude)} />
                <div class="container">
                    {generateRoutes()}
                </div>
                <Deadman />
            </div>
        )
    }
}

var r = (
    <BrowserRouter>
        <Layout />
    </BrowserRouter>
);

render(r, document.getElementById('app'));
