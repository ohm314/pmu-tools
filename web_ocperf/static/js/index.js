/* jshint globals: false */
angular.module('ocperfApp', ['checklist-model', 'ui.bootstrap', 'ngRoute']).
    service('ocperf_rest', function($http) {
        function get_emap() {
            return $http.get('/api/v1/emap').then(function(response) {
                return response.data;
            });
        }

        return {
            get_emap: get_emap
        };
    }).
    config(function($locationProvider, $routeProvider) {
        $routeProvider.
            when('/', {
                templateUrl: '/templates/homepage.html',
                controller: 'homepageCtrl'
            }).
            when('/session', {
                templateUrl: '/templates/session.html'
            }).
            when('/benchmark', {
                templateUrl: '/templates/benchmark.html',
                controller: 'benchmarkCtrl'
            }).
            otherwise('/');
    }).
    controller('benchmarkCtrl', function($scope, $http, ocperf_rest) {
        $scope.workload = "/home/nhardi/code/cl_forward/bin/x86_64/Release/clpixel -serial -bin -file /home/nhardi/code/cl_forward/bin/x86_64/Release/test.small.arg";
        $scope.events = ["arith.mul"];
        $scope.interval = 100;
        $scope.search_term = "";
        $scope.streaming = true;
        $scope.tool = "stat";

        function fetchPlot(response) {
            var s_tag = response.data;
            $("#plot_autoload_script").append($(s_tag));
        }

        $scope.run = function() {
            var data = {
                tool: $scope.tool,
                workload: $scope.workload,
                events: $scope.events,
                interval: $scope.interval,
                streaming: $scope.streaming
            };

            $http.post("/api/v1/run", data=data).then(fetchPlot);
        };

        ocperf_rest.get_emap().then(function(emap) {
            $scope.emap = emap;
        });
    }).
    controller('homepageCtrl', function($scope, $http) {
        function fetch_sessions() {
            $http.get("/api/v1/session/").then(function(response) {
                $scope.sessions_list = response.data;
            });
        }

        $scope.new_session = function(session_title) {
            console.log("Creating new session with title: " + session_title);
            // post request
            // get uuid for the new sessions
            // redirect user to this new session
        };

        fetch_sessions();
    });
