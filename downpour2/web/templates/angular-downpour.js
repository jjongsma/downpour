/*
 * Core app module
 */
var downpour = angular.module('downpour', ['ngRoute', 'dpProviders', 'dpDirectives', 'dpControllers',
    'transfers', 'library'
    //{% if modules|count %}, '{{ modules|join('\', \'', attribute='namespace') }}'{% endif %}
]);

/*
 * Setup core routing rules
 */
downpour.config(['$routeProvider', '$locationProvider',
    function($routeProvider, $locationProvider) {

        $locationProvider.html5Mode(true);

        // Configure core routes
        $routeProvider.when('/transfers', {
            templateUrl: '/resources/templates/transfers/index.html',
            controller: 'TransferList'
        }).otherwise({
                redirectTo: '/'
            });

    }
]);

/*
 * Core service providers.
 */
var dpProviders = angular.module('dpProviders', []);

/*
 * Content injector service provider which allows modules to add hooks
 * into shared UI sections during config()
 */
dpProviders.provider('contentInjector',
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

/*
 * Core directives.
 */
var dpDirectives = angular.module('dpDirectives', ['ngTouch']);

dpDirectives.directive('drawerSlide', ['$swipe',
    function($swipe) {

        var link = function(scope, element, attrs) {

            var drawer = $(attrs['drawerSlide']);

            // Update nav height on scroll
            var topOffset = drawer.position().top;
            drawer.height($(window).height() - topOffset);

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
                    console.log('start');
                },
                'move': function(point) {
                    console.log(point);
                },
                'end': function(point) {
                    console.log('end');
                },
                'cancel': function() {
                    console.log('cancel');
                }
            })

        };

        return {
            'link': link
        };

    }
]);


/*
 * Core controllers.
 */
var dpControllers = angular.module('dpControllers', []);

/*
 * Main controller for header/footer/menu.
 */
dpControllers.controller('dpPage', ['$scope', '$routeParams', '$http', '$rootScope', 'contentInjector',
    function($scope, $routeParams, $http, $rootScope, contentInjector) {

        $scope.title = 'Downpour';
        $scope.menu = contentInjector.menu;
        $rootScope.section = 'overview';
        $rootScope.setSection = function(s) {
            $rootScope.section = s;
        }

        // Load core app settings on init
        $http.get('/app/config').success(function(data) {
            angular.extend($scope, data);
        });

    }
]);
