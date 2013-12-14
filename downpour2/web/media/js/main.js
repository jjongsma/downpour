$(function() {

	$('#menutoggle').bind('touchstart', function(e) {
		e.stopPropagation();
	});
	$('#navigation, #menutoggle').bind('click', function(e) {
		e.stopPropagation();
	});

	$('#menutoggle').bind('touchstart mousedown', function(e) {
		$(this).addClass('active');
	});
	$('#menutoggle').bind('mouseup mouseout touchend', function(e) {
		$(this).removeClass('active');
	});
	$('#menutoggle').bind('selectstart', function(e) {
		return false;
	});
	
	var navswipe = false;
	var start = 0;

	$('html').bind('touchstart', function(e) {
		var t1 = e.originalEvent.changedTouches[0];
		x = parseInt(t1.clientX);
		if (!drawerOpen()) {
			if (x < 20) {
				navswipe = x;
				start = 0;
			}
		} else {
			navswipe = x;
			start = 226;
		}
	});
	$('html').bind('touchmove', function(e) {
		if (navswipe !== false) {
			e.preventDefault();
			var t1 = e.originalEvent.changedTouches[0];
			x = parseInt(t1.clientX);
			slideDrawer(x - navswipe + start);
		}
	});
	$('html').bind('touchend', function(e) {
		if (navswipe !== false) {
			var t1 = e.originalEvent.changedTouches[0];
			x = parseInt(t1.clientX);
			if (x > 226 * .5) {
				openDrawer();
			} else {
				closeDrawer();
			}
			navswipe = false;
		}
	});

	$('#menutoggle').bind('touchend', function() {
		if (drawerOpen()) {
			closeDrawer();
		} else {
			openDrawer();
		}
	});

	$('html').click(function(e) {
		if (drawerOpen())
			closeDrawer();
	});
	
});

function drawerOpen() {
	return $('#navigation').offset().left > -200;
}

function slideDrawer(pixels) {

	// Stay one pixel behind the drag, some browers have issues
	var drawer = pixels - 226 + 1;

	if (drawer > 0)
		drawer = 0;
	else if (drawer < -226)
		drawer = -226;

	var percent = 1 - (drawer / -226);
	var icon = (percent * -4) - 8;

	var overlay = $('#loadingOverlay');
	if (!overlay.size()) {
		overlay = $('<div id="loadingOverlay"></div>'); 
		$('body').append(overlay);
	}
	var opacity = .6 * percent;

	overlay.css({ 'opacity': opacity });
	$('#menu span').css({ 'left': icon + 'px' });
	$('#navigation').css({ 'left': drawer + 'px' });

}

function openDrawer() {
	var overlay = $('#loadingOverlay');
	if (!overlay.size()) {
		overlay = $('<div id="loadingOverlay"></div>'); 
		$('body').append(overlay);
	}
	overlay.animate({ 'opacity': '.6' }, 100);
	$('#menu span').animate({ 'left': '-12px' }, 100);
	$('#navigation').animate({ 'left': '0px' }, 100);
}

function closeDrawer() {
	var overlay = $('#loadingOverlay');
	if (!overlay.size()) {
		overlay = $('<div id="loadingOverlay"></div>'); 
		$('body').append(overlay);
	}
	overlay.animate({ 'opacity': '.0' }, 100, function() { overlay.remove(); });
	$('#menu span').animate({ 'left': '-8px' }, 100);
	$('#navigation').animate({ 'left': '-226px' }, 100);
}

function spin(target) {
	return new Spinner({
		lines: 13, // The number of lines to draw
		length: 20, // The length of each line
		width: 10, // The line thickness
		radius: 30, // The radius of the inner circle
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
