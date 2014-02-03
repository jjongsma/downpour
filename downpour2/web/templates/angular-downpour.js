/*
 * Core app module
 */
var downpour = angular.module('downpour', ['ngRoute', 'ngAnimate',
    'dpServices', 'dpDirectives', 'dpFilters', 'dpControllers',
    'account', 'transfers', 'library'
    //{% if modules|count %}, '{{ modules|join('\', \'', attribute='namespace') }}'{% endif %}
]);

/*
 * Setup core routing rules
 */
downpour.config(['$routeProvider', '$locationProvider', '$httpProvider',
    function($routeProvider, $locationProvider, $httpProvider) {

        $locationProvider.html5Mode(true);

        // Configure core routes
        $routeProvider.when('/transfers', {
            templateUrl: '/resources/templates/transfers/index.html',
            controller: 'TransferList'
        }).when('/transfers/:id', {
            templateUrl: '/resources/templates/transfers/detail.html',
            controller: 'TransferDetail'
        }).when('/account/login', {
            templateUrl: '/resources/templates/account/login.html',
            controller: 'AccountLogin'
        }).when('/', {
            templateUrl: '/resources/templates/index.html',
            controller: 'dpOverview'
        }).when('/live', {
            templateUrl: '/resources/templates/index.html',
            controller: 'dpLiveMode'
        }).when('/demo', {
            templateUrl: '/resources/templates/index.html',
            controller: 'dpDemoMode'
        }).otherwise({
            redirectTo: '/'
        });

    }
]);

/*
 * Core service providers.
 */
var dpServices = angular.module('dpServices', []);

/*
 * Content injector service provider which allows modules to add hooks
 * into shared UI sections during config()
 */
dpServices.provider('contentInjector',
    function() {

        this.DEFAULT = {};
        this.SETTINGS = {};
        this.ADMIN = {};

        var navLinks = [];
        var settingLinks = [];
        var adminLinks = [];
        var navGroups = [];
        var blocks = {};

        var navLink = function(name, url, section) {
            return { 'name': name, 'url': url, 'section': section };
        };

        var addNavLink = function(group, name, url, section) {
            if (group === this.DEFAULT)
                navLinks.push(navLink(name, url, section));
            else if (group === this.SETTINGS)
                settingLinks.push(navLink(name, url, section));
            else if (group === this.ADMIN)
                adminLinks.push(navLink(name, url, section));
        };

        var navGroup = function(name, links, url) {
            return { 'name': name, 'url': url, 'links': links };
        };

        var addBlock = function(name, template, controller) {
            if (!(name in blocks))
                blocks[name] = [];
            blocks[name].push({'template': template, 'controller': controller });
        }

        var addNavGroup = function(name, links, url) {
            navGroups.push(navGroup(name, links, url));
        };

        this.navLink = navLink;
        this.addNavLink = addNavLink;
        this.navGroup = navGroup;
        this.addNavGroup = addNavGroup;
        this.addBlock = addBlock;

        this.$get = ['$rootScope', function($rootScope) {

            return {
                'navLink': navLink,
                'addNavLink': addNavLink,
                'navGroup': navGroup,
                'addNavGroup': addNavGroup,
                'menu': {
                    'navLinks': navLinks,
                    'settingLinks': settingLinks,
                    'adminLinks': adminLinks,
                    'navGroups': navGroups,
                    'open': false, // State for mobile slide out menu
                    'toggling': false // State for mobile slide out menu
                },
                'addBlock': addBlock,
                'block': function(name) {
                    if (name in blocks)
                        return blocks[name];
                    return [];
                }
            };

        }];

    }
);

dpServices.service('state', ['$rootScope', '$http', '$q',
    function($rootScope, $http, $q) {

        var update = function() {
            return $http.get('/app/state').success(function(data) {
                angular.extend($rootScope.state, data);
            }).then(
                function(response) {
                    return response.data;
                },
                function(response) {
                    return $q.reject("Could not refresh state");
                }
            );
        };

        $rootScope.state = {
            'update': update
        };

        update();

        return {
            'update': update,
            'state': $rootScope.state
        };

    }
]);

dpServices.service('authenticator', ['$rootScope', '$http', '$location', '$q', '$route',
    function($rootScope, $http, $location, $q, $route) {

        var set = function(user) {
            $rootScope.user = user;
            $rootScope.$broadcast('$userChanged', user);
            return user;
        };

        /*
         * Login as the specified user.
         */
        var login = function(username, password) {

            return $http({
                method: 'POST',
                url: '/account/login',
                data: $.param({
                    'username': username,
                    'password': password
                }),
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            }).then(
                function(response) {
                    return set(response.data);
                },
                function(response) {
                    set(null);
                    return $q.reject("Login failed");
                }
            );

        };

        /*
         * Log the current user out.
         */
        var logout = function() {

            return $http.post('/account/logout').then(
                function(response) {
                    set(null);
                    $route.reload();
                    return true;
                },
                function(response) {
                    set(null);
                    // Refresh to verify whether it actually succeeded despite error
                    return refresh().then(
                        function() {
                            return $q.reject("Logout failed");
                        },
                        function () {
                            $route.reload();
                            return true;
                        }
                    );
                }
            );

        };

        /*
         * Refresh credentials from the server.
         */
        var refresh = function() {

            var auth = 'user' in $rootScope && $rootScope.user;

            return $http.get('/account/detail').then(
                function(response) {
                    set(response.data);
                    if (!auth)
                        $route.reload();
                    return response.data;
                },
                function(response) {
                    set(null);
                    if (auth)
                        $route.reload();
                    return $q.reject("Not authenticated")
                }
            );

        }

        /*
         * Check if the user is authenticated, checking local cache then falling back to refresh().
         */
        var authenticated = function() {

            if ('user' in $rootScope) {
                if (!!$rootScope.user)
                    return $q.when($rootScope.user);
                else {
                    $location.path("/account/login");
                    return $q.reject("Not authenticated");
                }
            } else {
                return refresh();
            }

        };

        /*
         * Require that the user be logged in, or redirect to login page.
         */
        var require = function() {

            return authenticated().then(
                function(user) {
                    return user;
                },
                function(error) {
                    $location.path("/account/login");
                    return $q.reject(error);
                }
            );

        };

        return {
            'login': login,
            'logout': logout,
            'refresh': refresh,
            'authenticated': authenticated,
            'require': require
        };

    }
]);

/*
 * Core directives.
 */
var dpDirectives = angular.module('dpDirectives', ['ngTouch']);

dpDirectives.directive('drawerSlide', ['$swipe',
    function($swipe) {

        var link = function(scope, element, attrs) {

            var drawer = $(attrs['drawerSlide']);

            drawer.niceScroll({ hidecursordelay: 100 });
            $(window).on('scroll', function(e) {
                drawer.height($(window).height() - topOffset);
                drawer.getNiceScroll().resize();
            });

            drawer.on('selectstart', function(e) {
                return false;
            });

            $swipe.bind(element, {
                'start': function(point) {
                    // console.log('start');
                },
                'move': function(point) {
                    // console.log(point);
                },
                'end': function(point) {
                    // console.log('end');
                },
                'cancel': function() {
                    // console.log('cancel');
                }
            })

        };

        return {
            'link': link
        };

    }
]);

/*
 * Core filters.
 */
var dpFilters = angular.module('dpFilters', []);

dpFilters.filter('bytes', function() {
    return function(bytes, precision) {
		if (isNaN(parseFloat(bytes)) || !isFinite(bytes)) return '-';
		if (typeof precision === 'undefined') precision = 1;
        if (!bytes) return '0b';
		var units = ['b', 'kB', 'MB', 'GB', 'TB', 'PB'];
        var number = Math.floor(Math.log(bytes) / Math.log(1024));
		return (bytes / Math.pow(1024, Math.floor(number))).toFixed(precision) +  ' ' + units[number];
	}
});

/*
 * Core controllers.
 */
var dpControllers = angular.module('dpControllers', []);

/*
 * Demo mode
 */
dpControllers.controller('dpDemoMode', ['$rootScope', '$location',
    function($rootScope, $location) {
        $rootScope.demoMode = true;
        $location.path('/');
    }
])
dpControllers.controller('dpLiveMode', ['$rootScope', '$location',
    function($rootScope, $location) {
        $rootScope.demoMode = false;
        $location.path('/');
    }
])

/*
 * Main controller for header/footer/menu.
 */
dpControllers.controller('dpPage', ['$scope', '$routeParams', '$http', '$rootScope', '$interval',
    'state', 'contentInjector', 'authenticator',
    function($scope, $routeParams, $http, $rootScope, $interval, state, contentInjector, authenticator) {

        // Menu / etc
        $scope.title = 'Downpour';
        $scope.menu = contentInjector.menu;
        $rootScope.section = 'overview';
        $rootScope.setSection = function(s) {
            $scope.menu.open = false;
            $rootScope.section = s;
        }

        $scope.$watch('menu.open', function() {
            if ($scope.menu.open) {
                // Update nav height on open
                var drawer = $('#navigation');
                var topOffset = drawer.position().top;
                drawer.scrollTop(0);
                drawer.height($(window).height() - topOffset);
            }
        });

        // Authentication state
        $scope.logout = authenticator.logout;

        $scope.host = {};
        $scope.notifications = [];

        // Host/bandwidth stats and notifications
        var update = function() {
            $http.get('/app/host' + ($scope.demoMode ? '/demo' : '')).success(function(data) {
                angular.extend($scope.host, data);
            });
            $http.get('/app/notifications' + ($scope.demoMode ? '/demo' : '')).success(function(data) {
                $scope.notifications = data;
            });
        };

        update();

        $scope.interval = $interval(update, 5000)
        $scope.$on('$destroy', function() {
            $interval.cancel($scope.interval);
        })

    }
]);

dpControllers.controller('dpOverview', ['$scope', '$http', 'authenticator', 'contentInjector',
    function($scope, $http, authenticator, contentInjector) {

        $scope.mainblocks = contentInjector.block('homecolumn');
        $scope.sideblocks = contentInjector.block('homeblock');

        authenticator.require().then(
            function(user) {
                // Setup page here
            }
        );

    }
])

