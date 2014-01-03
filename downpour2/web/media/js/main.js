var navDrawer = false;
var navWidth = 0;
var drawerIcon = 0;
var slideDuration = 150;

$(function() {

	// Use History API for navigation if supported
	usePushState();

	// Add event handlers for slide-out menu if required
	setupMenu();

	// Refresh page on orientation change for force correct styles
	$(window).on('orientationchange', function() { window.location.reload(); });

	contentHandler(standardBehaviors);

    // Hide notification if no unread messages
    console.log($('.unread-count').html());
    if ($('.unread-count').html() == '0')
        $('.unread').hide();

	// Configure initial  behaviors
	contentChanged($('body'));

});

/*
 * Navigation / pushState handlers
 */

function usePushState() {

	if (!(window.history && history.pushState))
		return;

	// Set a content-only header on all requests to let the server
	// know not to wrap the response in the page template
	$.ajaxSetup({
		beforeSend: function (xhr, settings) {
			xhr.setRequestHeader('X-Standalone-Content', 'true');
		}
	});

	window.history.replaceState({ 'content': $('#content').html() },
		document.title, document.location.href);

	$(window).on('popstate', function(e) {
		restoreState(e.originalEvent.state);
	});

	$('html').on('click', 'a', function(e) {
		e.preventDefault();
		loadContent(this.href, this.title);
	});
	
	$('#navigation').on('click', 'a', function(e) {
		e.preventDefault();
		$('#navigation').find('li').removeClass('active');
		$(this).parent().addClass('active');
		loadContent(this.href, this.title);
		if (navDrawer)
			closeDrawer(slideDuration);
		e.stopPropagation();
	});

}

function loadContent(url, title) {

	if (url != document.location) {

		if (inCurrentDomain(url)) {

			$('html').animate({ 'scrollTop': '0px' }, 100);

			// Only display loading indicator if request takes awhile
			var loadTimer = setTimeout(function() {
				var overlay = showOverlay(1, 0, 'loading', $('#content'));
				var box = $('<div class="spinbox"></div>');
				overlay.append(box);
				spin(box[0]);
			}, 100);

			// Save latest HTML before replacing
			history.replaceState({ 'content': $('#content').html() }, document.title, document.location.href);
			$.get(url, function(content) {
				clearTimeout(loadTimer);
				var state = { 'content': content };
				history.pushState(state, title ? title : document.title, url);
				restoreState(state);
			}).always(function() {
				hideOverlay();
			});

		} else {

			window.location.href = url;

		}

	}

}

function restoreState(state) {

	if (state && state['content']) {
		var content = $('#content');
		content.html(state['content']);
		contentChanged(content);
	}

	$('#navigation').find('a').each(function(idx) {
		if (document.location.href.substring(0, this.href.length) == this.href) {
			$('#navigation').find('li').removeClass('active');
			$(this).parent().addClass('active');
			var title = $(this).parent().attr('title');
			if (!title) title = $(this).html();
			$('h1').html(title);
		}
	});

}

function inCurrentDomain(url) {

	var current = document.location;
	var parser = document.createElement('a');
	parser.href = url;

	return parser.protocol == current.protocol
		&& parser.hostname == current.hostname
		&& parser.port == current.port;

}

function showOverlay(opacity, duration, className, container) {

	if (opacity == undefined) opacity = 0.6;
	if (!className) className = 'fade';
	if (!container) container = $('body');

	var overlay = $('#overlay');

	if (!overlay.size()) {
		overlay = $('<div id="overlay" class="' + className + '"></div>'); 
		container.append(overlay);
	}

	if (duration)
		overlay.animate({ 'opacity': opacity }, duration);
	else
		overlay.css({ 'opacity': opacity });
	
	return overlay;

}

function hideOverlay(duration) {

	var overlay = $('#overlay');

	if (overlay.size()) {
		if (duration)
			overlay.animate({ 'opacity': '.0' }, duration, function() { overlay.remove(); });
		else
			overlay.remove();
	}

}

/*
 * Javascript content handlers / behavior attachment
 */

var contentHandlers = [];

function contentHandler(handler) {
	contentHandlers.push(handler);
}

function contentChanged(content) {
	$.each(contentHandlers, function() { this(content); });
}

function standardBehaviors(content) {

	// "Remove" buttons
	content.find('.remove').on('click', function() {
		var p = $(this).parent();
		p.fadeOut(400, function() { p.remove(); });
	});

}

/*
 * Slide-out menu handler
 */

function setupMenu() {

	var nav = $('#navigation');

	if (nav.offset().left < 0) {

		navDrawer = true;
		navWidth = -nav.offset().left;

		drawerIcon = $('#menu').find('span').offset().left;

		// Update nav height on scroll
		var topOffset = $('#header').outerHeight() + 1;
		nav.css({ 'top': topOffset + 'px' });
		nav.height($(window).height() - topOffset);
		nav.niceScroll({ hidecursordelay: 100 });

		$(window).on('scroll', function(e) {
			nav.height($(window).height() - topOffset);
			nav.getNiceScroll().resize();
		});

        nav.on('selectstart', function(e) {
            return false;
        });

        var menutoggle = $('#menutoggle');
		menutoggle.on('touchstart', function(e) {
			$(this).addClass('active');
			e.stopPropagation();
		});
        menutoggle.on('selectstart', function(e) {
            return false;
        });
        menutoggle.on('touchend', function() {
            $(this).removeClass('active');
            if (drawerOpen()) {
                closeDrawer(slideDuration);
            } else {
                openDrawer(slideDuration);
            }
        });

		var swipeState = {
			started: false,
			direction: null,
			drawerX: 0,
			startX: 0,
			startY: 0
		};

        var html = $('html');
		html.on('touchstart', function(e) {

			// Check if vertical or horizontal
			var t1 = e.originalEvent.changedTouches[0];
			swipeState.startX = parseInt(t1.clientX);
			swipeState.startY = parseInt(t1.clientY);
			swipeState.direction = null;

			if (!drawerOpen()) {
				if (swipeState.startX < 20) {
					swipeState.started = new Date().getTime();
					swipeState.drawerX = 0;
				}
			} else {
				swipeState.started = new Date().getTime();
				swipeState.drawerX = navWidth;
			}

		});

		html.on('touchmove', function(e) {

			if (swipeState.started !== false) {

				// Required for Android Chrome for some reason
				e.preventDefault();
				var t1 = e.originalEvent.changedTouches[0];
				var xMove = parseInt(t1.clientX) - swipeState.startX;
				var yMove = parseInt(t1.clientY) - swipeState.startY;

				if (swipeState.direction == null) {
					var absX = Math.abs(xMove);
					var absY = Math.abs(yMove);
					if (absX > 5 || absY > 5) {
						swipeState.direction = absX > absY ? 'horizontal' : 'vertical';
					}
				}

				if (swipeState.direction == 'horizontal')
					slideDrawer(xMove + swipeState.drawerX);
				else if (swipeState.direction == 'vertical')
					swipeState.started = false;

			}

		});

		html.on('touchend', function(e) {

			if (swipeState.started !== false) {

				var t1 = e.originalEvent.changedTouches[0];
				x = parseInt(t1.clientX);
				var elapsed = new Date().getTime() - swipeState.started;
				swipeState.started = false;

				// Fast swipe, finish open/close automatically
				if (elapsed < 150 && Math.abs(x - swipeState.startX) > 50) {
					if (swipeState.drawerX && x < swipeState.startX)
						return closeDrawer(slideDuration);
					else if (!swipeState.drawerX && x > swipeState.startX)
						return openDrawer(slideDuration);
				}

				if (x > navWidth * .5)
					openDrawer(slideDuration);
				else
					closeDrawer(slideDuration);

			}

		});

	}

}

function drawerOpen() {
	return $('#navigation').offset().left == 0;
}

function slideDrawer(pixels) {

	if (!navDrawer) return;

	var drawer = pixels - navWidth;

	if (drawer > 0)
		drawer = 0;
	else if (drawer < -navWidth)
		drawer = -navWidth;

	var percent = 1 - (drawer / -navWidth);
	var icon = (percent * -4) + drawerIcon;
	var opacity = .6 * percent;

	showOverlay(opacity);
	$('#menu').find('span').css({ 'left': icon + 'px' });
	$('#navigation').css({ 'left': drawer + 'px' });

}

function openDrawer(duration) {

	if (!navDrawer) return;

	showOverlay(0.6, duration);
	$('#menu').find('span').animate({ 'left': (drawerIcon - 4) + 'px' }, duration);
	$('#navigation').animate({ 'left': '0px' }, duration);

	// Close menu on page click
	$('html').on('click.drawer', function(e) {
		if (drawerOpen())
			closeDrawer(duration);
	});

	// Block clicks from nav drawer / menu header from closing menu
	$('#navigation, #menutoggle').on('click.drawer', function(e) {
		e.stopPropagation();
	});
	
}

function closeDrawer(duration, callback) {

	if (!navDrawer) {
		if (callback) callback();
		return;
	}

	hideOverlay(duration);
	$('#menu').find('span').animate({ 'left': drawerIcon + 'px' }, duration);
	$('#navigation').animate({ 'left': '-' + navWidth + 'px' }, duration, function() {
		// Reset drawer menu to top
		$('#navigation').scrollTop(0);
		if (callback) callback();
	});

	// Remove close listeners
	$('html').off('.drawer');

}

/* Utility functions */

function spin(target) {
	return new Spinner({
		lines: 13, // The number of lines to draw
		length: 20, // The length of each line
		width: 7, // The line thickness
		radius: 20, // The radius of the inner circle
		corners: 1, // Corner roundness (0..1)
		rotate: 0, // The rotation offset
		direction: 1, // 1: clockwise, -1: counterclockwise
		color: '#000', // #rgb or #rrggbb or array of colors
		speed: 1, // Rounds per second
		trail: 60, // Afterglow percentage
		shadow: false, // Whether to render a shadow
		hwaccel: false, // Whether to use hardware acceleration
		className: 'spinner', // The CSS class to assign to the spinner
		zIndex: 2e9, // The z-index (defaults to 2000000000)
		top: 'auto', // Top position relative to parent in px
		left: 'auto' // Left position relative to parent in px
	}).spin(target);
}

function setUnreadCount(count) {
	$('.unread-count').html(count);
	if (!$('.unread').is(':visible'))
		$('.unread').fadeIn();
	if (!count)
		setTimeout(function() {
			$('.unread').fadeOut();
		}, 1000);
}
