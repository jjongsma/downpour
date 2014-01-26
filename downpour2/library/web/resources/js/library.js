// 'sidelink': web.link_renderer('/library/', 'Media Library'),
// 'settinglink': web.link_renderer('/library/types', 'Media Types'),
// 'homecolumn': lambda req: self.render_template('library/home-blocks.html', req, {})

var library = angular.module('library', ['ngRoute', 'dpProviders']);

library.config(['$routeProvider', '$locationProvider', 'contentInjectorProvider',
    function($routeProvider, $locationProvider, contentInjectorProvider) {

        // Configure core routes
        $routeProvider.when('/library', {
            templateUrl: '/library/resources/templates/index.html',
            controller: 'LibraryView'
        }).when('/library/types', {
            templateUrl: '/library/resources/templates/index.html',
            controller: 'LibraryView'
        });

        contentInjectorProvider.addNavLink(
            contentInjectorProvider.DEFAULT, "Library", "/library", "library");
        contentInjectorProvider.addNavLink(
            contentInjectorProvider.SETTINGS, "Media Types", "/library/types", "librarytypes");

    }
]);

transfers.controller('LibraryView', ['$scope', '$routeParams',
    function($scope, $routeParams) {

    }
]);
