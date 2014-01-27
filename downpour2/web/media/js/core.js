var transfers = angular.module('transfers', []);

transfers.controller('TransferList', ['$scope', '$routeParams',
    function($scope, $routeParams) {

    }
]);

transfers.controller('TransferDetail', ['$scope', '$routeParams',
    function($scope, $routeParams) {

    }
]);

var account = angular.module('account', []);

account.controller('AccountLogin', ['$scope', '$routeParams', '$location', 'authenticator',
    function($scope, $routeParams, $location, authenticator) {

        $scope.submit = function() {
            authenticator.login(
                $scope.username, $scope.password
            ).then(
                function(user) {
                    $scope.error = null;
                    $location.path('/');
                },
                function(error) {
                    $scope.error = error;
                }
            );
        };

    }
]);
