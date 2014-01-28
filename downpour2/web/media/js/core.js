var transfers = angular.module('transfers', []);

transfers.controller('TransferList', ['$scope', '$http', 'authenticator',
    function($scope, $http, authenticator) {

        $scope.downloads = [];
        $scope.queued = [];
        $scope.uploads = [];

        $http.get('/transfers/status/demo').then(
            function(response) {
                angular.forEach(response.data, function(transfer) {
                    if (transfer.state.state == 'seeding')
                        $scope.uploads.push(transfer);
                    else if (transfer.state.state == 'queued')
                        $scope.queued.push(transfer);
                    else
                        $scope.downloads.push(transfer);
                });
            }
        );

    }
]);

transfers.controller('TransferDetail', ['$scope', '$routeParams',
    function($scope, $routeParams) {

    }
]);

var account = angular.module('account', []);

account.controller('AccountLogin', ['$scope', '$location', 'authenticator',
    function($scope, $location, authenticator) {

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
