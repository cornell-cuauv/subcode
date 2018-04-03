// TODO: Add prop-types
// TODO: Port option updating
// TODO: Port dynamic grid resizing
import React from "react";

function formatId(name) {
    return name.replace(/\ /g, "_");
}

class ImageContainer extends React.Component {
    render() {
        const img = this.props.image;
        return (
            <li className="image-container list-group-item col-xs-6"
                data-index={img.image_index}>
                <img id={formatId(img.image_name)} src={'data:image/jpeg;base64,' + img.image} className="posted"/>
                <br/>
                {img.image_name}
            </li>
        );
    }
}

class OptionItem extends React.Component {
    constructor(props) {
        super(props);
        this.option = this.props.option;
        this.onChange = this.props.onChange;
        this.type = this.option.type;
        this.valueName = formatId(this.option.option_name);
        this.sliderName = formatId(this.option.option_name) + '_slider';
        this.valueId = '#' + this.valueName;
        this.sliderId = '#' + this.sliderName;
        this.handleOptionUpdate = this.handleOptionUpdate.bind(this);
    }

    handleOptionUpdate(evt) {
        if (this.type == 'int' || this.type == 'double') {
            // Update slider when value is changed
            if ('min_value' in this.option && 'max_value' in this.option) {
                $(this.sliderId).slider('value', evt.target.value);
            }
        }
        // Propagate update event to parent component
        this.props.onChange(evt);
    }

    componentDidMount() {
        if (this.type == 'int' || this.type == 'double') {
            // Initialize JQuery-UI slider
            if ('min_value' in this.option && 'max_value' in this.option) {
                $(this.sliderId).slider({
                    min: this.option.min_value,
                    max: this.option.max_value,
                    value: this.option.value,
                    slide: function(event, ui) {
                        $(this.valueId).val(ui.value);
                    }.bind(this)
                });
                if (this.type == 'double') {
                    $(this.sliderId).slider("option", "step", 0.001);
                }
            }
        }
    }

    render() {
        if (this.type == 'int' || this.type == 'double') {
            // Display input box and slider for number option
            return (
                <li className="list-group-item col-xs-12" data-index={this.option.option_index}>
                    {this.option.option_name + ': '}
                    <input type="text" className="slider_value" id={this.valueName} value={this.option.value}/>
                    <br/>
                    <div id={this.sliderName} onChange={this.handleOptionUpdate}></div>
                </li>
            );
        }
        else if (this.type == 'bool') {
            // Display checkbox for boolean option
            return (
                <li className="list-group-item col-xs-12" data-index={this.option.option_index}>
                    <input type="checkbox" id={this.valueName} onChange={this.handleOptionUpdate} checked={this.option.value}/>
                    {this.option.option_name}
                </li>
            );
        }
        else if (this.type == 'str') {
            // Display input box for string option
            return (
                <li className="list-group-item col-xs-12" data-index={this.option.option_index}>
                    {this.option.option_name + ': '}
                    <input type="text" id={this.valueName} className="text_input" value={this.option.value}/>
                </li>
            );
        }
    }
}

export class VisionGuiModule extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            images: {},
            options: {},
        };
        this.socket = null;
        this.handleOptionUpdate = this.handleOptionUpdate.bind(this);
    }

    getOrderedImages() {
        let orderedImages = [];
        for (let imgName in this.state.images) {
            orderedImages.push(this.state.images[imgName]);
        }
        orderedImages.sort((a, b) => a.image_index - b.image_index);
        return orderedImages;
    }

    getOrderedOptions() {
        let orderedOptions = [];
        for (let optionName in this.state.options) {
            orderedOptions.push(this.state.options[optionName]);
        }
        orderedOptions.sort((a, b) => a.option_index - b.option_index);
        return orderedOptions;
    }

    handleOptionUpdate(evt) {
        console.log(evt);
    }

    componentDidMount() {
        let webSocketPath = location.pathname.split('/');
        // Construct path to websocket handler
        webSocketPath.splice(2, 0, 'ws');
        webSocketPath = webSocketPath.join('/');
        this.socket = new WebSocket('ws://' + document.domain + ':' + location.port + webSocketPath);
        this.socket.onmessage = function(evt) {
            const msg = JSON.parse(evt.data);
            //console.log("Received", msg);
            if ("image_name" in msg) {
                this.setState({images: Object.assign({}, this.state.images, {[msg.image_name]: msg})});
                //    resize_grid();
            }
            else if ("option_name" in msg) {
                if (msg.type === 'str') {
                    msg.value = String.fromCharCode.apply(null, new Uint8Array(msg.value));
                }
                this.setState({options: Object.assign({}, this.state.options, {[msg.option_name]: msg})});
            }
        }.bind(this);
    }

    render() {
        return (
            <div>
                <span>{JSON.stringify(this.state)}</span>
                <div id="body" class="container-fluid" role="main">
                    <input type="checkbox" id="preprocessor-toggle"/>
                    <label for="preprocessor-toggle">Toggle Preprocessor Options</label>
                    <button id="clear-images">Clear Images</button>
                    <div class="row">
                        <div class="col-xs-10">
                        <ul class="list-group row" id="images">
                            {this.getOrderedImages().map(img => <ImageContainer image={img} key={img.image_index}/>)}
                        </ul>
                        </div>
                        <div class="col-xs-2">
                        <ul class="list-group row" id="options">
                            {this.getOrderedOptions().map(option => <OptionItem option={option} onChange={this.handleOptionUpdate} key={option.option_index}/>)}
                        </ul>
                        </div>
                    </div>
                </div>
            </div>
        );
    }
}
