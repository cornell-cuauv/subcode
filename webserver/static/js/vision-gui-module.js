var socket;
var imagesContainer;
var optionsContainer;
var preprocessorToggle;

function togglePreprocessorItems() {
    var preprocessorItems = $("li.list-group-item").filter(function(k, v) {
        return v.innerHTML.indexOf("PPX_") !== -1;
    });
    preprocessorItems.each(function(k, v) {
        v.style.backgroundColor = "#cccccc";
    });
    if (preprocessorToggle.prop("checked")) {
        preprocessorItems.slideDown();
    }
    else {
        preprocessorItems.slideUp();
    }
}

function format_id(name) {
    return name.replace(/\ /g, "_");
}

function update_value(msg) {
    var value_name = format_id(msg.option_name);
    var slider_name = format_id(msg.option_name) + '_slider';
    var value_id = '#' + value_name;
    var slider_id = '#' + slider_name;

    if (! $( value_id ).is(":focus")) {
        if ('min_value' in msg && 'max_value' in msg) {
            if (! $( slider_id ).is(":focus")) {
                $( value_id ).val( msg.value );
                $(slider_id).slider( "value", msg.value );
            }
        }
        else {
            $( value_id ).val( msg.value );
        }
    }
}

function send_option_update(msg, value) {
    const moduleName = window.location.pathname.substring(window.location.pathname.lastIndexOf('/'));
    socket.send(JSON.stringify({module: moduleName,
                 option: msg.option_name,
                 value: value}));
    //console.log('sending ' + value);
}

function add_int(msg, parser) {
    if (parser === undefined)
        parser = parseInt;
    var value_name = format_id(msg.option_name);
    var slider_name = format_id(msg.option_name) + '_slider';
    var value_id = '#' + value_name;
    var slider_id = '#' + slider_name;
    optionsContainer.append("<li class=\"list-group-item col-xs-12\" data-index=\"" + msg.option_index + "\">" +
                           msg.option_name + ': ' +
                           '<input type="text" class=\"slider_value\" id=\"' +
                           value_name +
                           '\">' +
                           "<br>" +
                           "<div id=\"" + slider_name + '"></div>' +
                           "</li>");
    sort_options();

    if ('min_value' in msg && 'max_value' in msg) {
        $(slider_id).slider({ min:msg.min_value,
                              max:msg.max_value,
                              value: msg.value,
                              slide: function( event, ui ) {
                                  $( value_id ).val( ui.value );
                                  send_option_update(msg, ui.value);
                              }});
    }
        $( value_id ).change(function() {
            if ('min_value' in msg && 'max_value' in msg) {
                $(slider_id).slider( "value", this.value );
            }
            send_option_update(msg, parser(this.value));
        });
}

function add_double(msg) {
    add_int(msg, parseFloat);
    var js_name = format_id(msg.option_name);
    var id = '#' + js_name;
    if ('min_value' in msg && 'max_value' in msg) {
        $( id + '_slider' ).slider( "option", "step", 0.001 );
    }
}

function add_bool(msg) {
    var js_name = format_id(msg.option_name);
    var id = '#' + js_name;
    optionsContainer.append("<li class=\"list-group-item col-xs-12\" data-index=\"" + msg.option_index + "\">" +
                           '<input type="checkbox" id="' + js_name + '">' +
                           msg.option_name +
                           "</li>");
    sort_options();
    $( id ).change(function() {
        send_option_update(msg, this.checked);
    });
}

function add_str(msg) {
    var js_name = format_id(msg.option_name);
    var id = '#' + js_name;
    optionsContainer.append("<li class=\"list-group-item col-xs-12\" data-index=\"" + msg.option_index + "\">" +
                           msg.option_name + ': ' +
                           '<input type="text" id=\"' +
                           js_name +
                           '\" class="text_input">' +
                           "</li>");
    sort_options();
    $( id ).change(function() {
        send_option_update(msg, this.value);
    });
}

function sort_images() {
    var images = $.makeArray(imagesContainer.children("li"));
    for (var i = 1; i < images.length; ++i) {
        var j = i;
        while (j > 0 && parseInt(images[j].getAttribute('data-index')) < parseInt(images[j-1].getAttribute('data-index'))) {
            var tmp = images[j-1];
            images[j-1] = images[j];
            images[j] = tmp;
            --j;
        }
    }
    imagesContainer.append(images);
    window.requestAnimationFrame(togglePreprocessorItems);
}

function sort_options() {
    var options = $.makeArray(optionsContainer.children("li"));
    for (var i = 1; i < options.length; ++i) {
        var j = i;
        while (j > 0 && parseInt(options[j].getAttribute('data-index')) < parseInt(options[j-1].getAttribute('data-index'))) {
            var tmp = options[j-1];
            options[j-1] = options[j];
            options[j] = tmp;
            --j;
        }
    }
    optionsContainer.append(options);
    window.requestAnimationFrame(togglePreprocessorItems);
}

function resize_grid() {
    // Note: We use manual control, rather than allowing Bootstrap's media
    // queries to dynamically resize the grid, so that we have better control at
    // high resolutions
    var width = $(window).width();
    $('.image-container').each(function() {
        var container = $(this);
        var currentClass = container.attr("class").match(/col[^ ]*/)[0];
        container.removeClass(currentClass);
        if (width > 4000) {
            container.addClass("col-xs-2");
        }
        else if (width > 2000) {
            container.addClass("col-xs-3");
        }
        else if (width > 1500) {
            container.addClass("col-xs-4");
        }
        else {
            container.addClass("col-xs-6");
        }
    });
}

$(document).ready(function(){
    let webSocketPath = location.pathname.split('/');
    // Construct path to websocket handler
    webSocketPath.splice(2, 0, 'ws');
    webSocketPath = webSocketPath.join('/');
    socket = new WebSocket('ws://' + document.domain + ':' + location.port + webSocketPath);
    socket.onmessage = function(evt) {
        const msg = JSON.parse(evt.data);
        //console.log("Received", msg);
        if ("image_name" in msg) {
            var js_name = format_id(msg.image_name);
            if (imagesContainer.find("img#" + js_name).length === 0) {
                imagesContainer.append("<li class=\"image-container list-group-item col-xs-6\" data-index=\"" + msg.image_index + "\"><img id=\"" + js_name + "\" src=\"\" class=\"posted\"><br>" +
                                      msg.image_name + "</li>");
                sort_images();
                resize_grid();
            }

            document.getElementById(js_name).src = 'data:image/jpeg;base64,' + msg.image;
        }
        else if ("option_name" in msg) {
            var id = "#" + format_id(msg.option_name);
            if ($(id).length === 0) {
                if (msg.type === 'int')
                    add_int(msg)
                else if (msg.type === 'double')
                    add_double(msg)
                else if (msg.type === 'bool')
                    add_bool(msg)
                else if (msg.type === 'str')
                    add_str(msg)
            }

            if (msg.type === 'str')
                msg.value = String.fromCharCode.apply(null, new Uint8Array(msg.value));


            if (msg.type === 'int' || msg.type === 'double' || msg.type === 'str')
                update_value(msg)
            else if (msg.type === 'bool') {
                $( id ).prop("checked", msg.value);
            }
        }
    };

    imagesContainer = $("ul#images");
    optionsContainer = $("ul#options");
    preprocessorToggle = $("#preprocessor-toggle");
    clearImagesBtn = $("#clear-images");
    preprocessorToggle.click(togglePreprocessorItems);
    clearImagesBtn.click(function() {
        imagesContainer.empty();
    });
    $(window).resize(resize_grid);

});
