/*!
 * Javascript for general Auto-Subliminal stuff
 */

/* ================
 * Global variables
 * ================ */

var base_url = window.location.protocol + '//' + window.location.host + webroot;

/* ======
 * Navbar
 * ====== */

// Highlight the active navigation button (without page submit)
$('.navbar .nav a').on('click', function () {
    $('.navbar').find('.nav').find('.active').removeClass('active');
    $(this).parent().addClass('active');
});

//Highlight the active navigation button (after page submit)
var base_path = '/' + location.pathname.replace(webroot, '').split('/')[1] + '/';
$('.navbar').find('.nav').find('a[href=\'' + base_path + '\']').closest('li').addClass('active');

/* ========
 * Checkbox
 * ======== */

// Usage (hidden field reflects the values of the checkbox):
// <input type='checkbox' data-toggle='toggle' data-on='Enabled' data-off='Disabled' data-size='small'>
// <input type='hidden' id='<id/name>' name='<id/name>' value='<variable_true_or_false>'>

// Handle the toggle checkbox values with a hidden field (to support both 'on' and 'off' values on submit)
$('input[type=checkbox][data-toggle=toggle][data-on=Enabled][data-off=Disabled]').on('change', function () {
    // We need to get the parent first because bootstrap-toggle adds a toggle-group div around the checkbox
    var target = $(this).parent().next('input[type=hidden]').val();
    if (target == 'False') {
        target = 'True';
    } else {
        target = 'False';
    }
    $(this).parent().next('input[type=hidden]').val(target);
});

/* ========
 * Popovers
 * ======== */

// Enable the popovers
$('[data-toggle=popover]').popover();

/* =========
 * Countdown
 * ========= */

// Setup the countdown until scandisk next run date
var scandisk_next_run_date = new Date();
scandisk_next_run_date.setTime($('#scandisk-nextrun-time-ms').val());
$('#scandisk-nextrun').countdown(scandisk_next_run_date, function (event) {
    if (event.strftime('%H:%M:%S') == '00:00:00') {
        $(this).text('Running...');
    } else {
        $(this).text(event.strftime('%H:%M:%S'));
    }
});

// Setup the countdown until checksub next run date
var checksub_next_run_date = new Date();
checksub_next_run_date.setTime($('#checksub-nextrun-time-ms').val());
$('#checksub-nextrun').countdown(checksub_next_run_date, function (event) {
    if (event.strftime('%H:%M:%S') == '00:00:00') {
        $(this).text('Running...');
    } else {
        $(this).text(event.strftime('%H:%M:%S'));
    }
});

/* =============
 * Notifications
 * ============= */

// By default we will use desktop notifications, but we also provide settings for fallback to browser notifications

// Bottom right stack - to be aligned with desktop notifications at the right bottom
var stack_bottomright = {
    'dir1': 'up',
    'dir2': 'left',
    'firstpos1': 10,
    'firstpos2': 10,
    'spacing1': 10,
    'spacing2': 10
};

// Alternative stack - center stack - copied from https://github.com/sciactive/pnotify/issues/46
var stack_center = {
    'dir1': 'down',
    'dir2': 'right',
    'firstpos1': 4,
    'firstpos2': ($(window).width() / 2) - (Number(PNotify.prototype.options.width.replace(/\D/g, '')) / 2)
};

// Handle the center stack when resizing the browser
$(window).on('resize', function () {
    stack_center.firstpos2 = ($(window).width() / 2) - (Number(PNotify.prototype.options.width.replace(/\D/g, '')) / 2);
});

// Alternative stack - context stack
var stack_context = {
    'dir1': 'down',
    'dir2': 'right',
    'context': $('#stack-context')
};

// PNotify default options
PNotify.prototype.options.stack = stack_bottomright;
PNotify.prototype.options.addclass = 'stack-bottomright';
PNotify.prototype.options.styling = 'bootstrap3';
PNotify.prototype.options.delay = 5000;
PNotify.prototype.options.desktop.desktop = true; // Use desktop notifications
PNotify.desktop.permission(); // Check for permission for desktop notifications

/* ==========
 * Websockets
 * ========== */

// Set the websocket_message_url variable
var websocket_message_url = 'ws://' + window.location.host + webroot + '/system/message';

// Function to get a message through websocket
function get_message_through_websocket(message) {
    data = message.data;
    // console.log('Received websocket message: ' + data);
    if (!jQuery.isEmptyObject(data)) {
        data_json = JSON.parse(data);
        _handle_message_data(data_json);
    }
}

// Function to handle the message data
function _handle_message_data(message) {
    if (message['message_type'] == 'notification') {
        var notification = message['notification'];
        _show_notification(notification['notification_message'], notification['notification_type'], notification['sticky']);
    } else if (message['message_type'] == 'event') {
        var event = data_json['event'];
        _handle_event(event['event_type']);
    } else {
        console.error('Unsupported message: ' + message)
    }
}

// Function to show a notification message
function _show_notification(message, type, sticky) {
    // Sticky location - use stack_context
    if (sticky) {
        new PNotify({
            title: false, // Remove title
            text: message,
            type: type,
            hide: false, // Disable fading
            width: 'auto',
            addclass: 'container stack-context',
            stack: stack_context,
            desktop: {
                desktop: false // Disable desktop
            }
        });
    }
    // Default location
    else {
        new PNotify({
            title: 'Auto-Subliminal',
            text: message,
            type: type
        });
    }
}

// Function to handle an event
function _handle_event(event_type) {
    if (event_type == 'HOME_PAGE_RELOAD') {
        // only reload when we are actually on the home page
        if (window.location.pathname.indexOf('/home') >= 0) {
            // Add delay of 1s to be sure it's not triggered immediately after a page redirect (or load)
            // When redirecting and loading really fast after each other, it's possible that your websocket is not initialized in time and your websocket message is lost
            setTimeout(function () {
                window.location.reload();
            }, 1000);
        }
    } else {
        console.error('Unsupported event: ' + event_type);
    }
}

// Setup the websocket message system
var ws = new WebSocket(websocket_message_url);
ws.onmessage = get_message_through_websocket;
// console.log('Websocket ready to receive messages');
