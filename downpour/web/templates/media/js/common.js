function AJAX() {
	this.http = AJAX.CreateNewHTTPObject();
}

AJAX.prototype.get = function(url, callback) {
	req = this.http;
	req.open('GET', url, true); 
	req.setRequestHeader('Content-Type', 'text/plain');
	req.onreadystatechange = function(transport) {
		if ((req.readyState == 4) && (req.status == 200))
			callback(req.responseText);
	}
	req.send(null);
}

AJAX.prototype.getJSON = function(url, callback) {
	this.get(url, function(response) {
		callback(eval('(' + response + ')'));
	});
}

AJAX.CreateNewHTTPObject = function() {
	var xmlhttp;
	/*@cc_on
	@if (@_jscript_version >= 5)
		try {
			xmlhttp = new ActiveXObject("Msxml2.XMLHTTP");
		}
		catch (e) {
			try {
				xmlhttp = new ActiveXObject("Microsoft.XMLHTTP");
			}
			catch (E) {
				xmlhttp = false;
			}
		}
	@else
		xmlhttp = false;
	@end @*/
	if (!xmlhttp && typeof XMLHttpRequest != 'undefined') {
		try {
			xmlhttp = new XMLHttpRequest();
		} 
		catch (e) {
			xmlhttp = false;
		}
	}
	return xmlhttp;
}

function findElementsByClassName(classname, root) {
	var res = [];
	var elts = (root||document).getElementsByTagName('*')
	var re = new RegExp('\\b'+classname+'\\b');
	for (var i = 0; i < elts.length; ++i)
		if (elts[i].className.match(re))
			res[res.length] = elts[i];
	return res;
}

function addClass(el, c) {
	cl = el.className ? el.className.split(/ /) : [];
	for (var i = 0; i < cl.length; ++i)
		if (cl[i] == c)
			return;
	cl[cl.length] = c;
	el.className = cl.join(' ');
}

function removeClass(el, c) {
	if (!el.className) return;
	cl = el.className.split(/ /);
	var nc = [];
	for (var i = 0; i < cl.length; ++i)
		if (cl[i] != c)
			nc[nc.length] = cl[i];
	el.className = nc.join(' ');
}

function stopEvent(e) {
	var ev = window.event||e;
	if (ev.stopPropagation)
		ev.stopPropagation();
	else
		ev.cancelBubble = true;
}

function addEvent(el, name, handler) {
	if (el.addEventListener) {
		el.addEventListener(name, handler, false);
	} else {
		el.attachEvent('on'+name, handler);
	}
}

function removeEvent(el, name, handler) {
	if (el.removeEventListener) {
		el.removeEventListener(name, handler, false);
	} else {
		el.detachEvent('on'+name, handler);
	}
}
