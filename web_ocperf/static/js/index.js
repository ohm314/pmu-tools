/* jshint globals: false */
angular.module('ocperfApp', ['checklist-model', 'ui.bootstrap', 'ngRoute']).
    service('ocperf_rest', function($http) {
        function get_emap() {
            return $http.get('/api/v1/emap', {cache: true}).
                then(function(response) {
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
            when('/session/:uuid', {
                templateUrl: '/templates/benchmark.html',
                controller: 'benchmarkCtrl'
            }).
            otherwise('/');
    }).
    controller('benchmarkCtrl', function($scope, $http, ocperf_rest, $routeParams, $location) {
        $scope.frontend_state = {};

        $scope.frontend_state.workload = "/home/nhardi/code/cl_forward/bin/x86_64/Release/clpixel -serial -bin -file /home/nhardi/code/cl_forward/bin/x86_64/Release/test.small.arg";
        // $scope.frontend_state.workload = "/tmp/workload.py";
        $scope.frontend_state.events = ["instructions"];
        $scope.frontend_state.interval = 100;
        $scope.frontend_state.streaming = true;
        $scope.frontend_state.tool = "stat";
        $scope.frontend_state.env = "";

        $scope.search_term = "";

        function clearPlot() {
            console.log("clearing the plot area");
            $("#plot_autoload_script").html("");
            $("body>link").each(function() {
                this.remove();
            });
        }

        function fetchPlot(response) {
            clearPlot();

            console.log(response.data);

            var s_tag = response.data.script;
            $scope.frontend_state = response.data.state;
            $("#plot_autoload_script").append($(s_tag));
        }

        function loadBenchmarks(response) {
            var url = "/api/v1/session/" + $routeParams.uuid;

            $http.get(url).then(function(response) {
                $scope.benchmarks_list = response.data;
            });
        }

        function loadOldPlot(uuid) {
            var url = "/api/v1/benchmark/" + uuid + ".js";

            $http.get(url).then(fetchPlot);
        }

        $scope.clearPlot = clearPlot;
        $scope.loadOldPlot = loadOldPlot;

        $scope.run = function() {
            var url = "/api/v1/session/" + $routeParams.uuid;
            $http.post(url, data=$scope.frontend_state).then(fetchPlot).then(loadBenchmarks);
        };

        ocperf_rest.get_emap().then(function(emap) {
            $scope.emap = emap;
        });
        loadBenchmarks();
    }).
    controller('homepageCtrl', function($scope, $http) {
        function fetch_sessions() {
            $http.get("/api/v1/session/").then(function(response) {
                $scope.sessions_list = response.data;
            });
        }

        $scope.new_session = function(session_title) {
            $http.post("/api/v1/session/", {session_title: session_title}).
                then(function(response) {
                    fetch_sessions();
                });
        };

        fetch_sessions();
    }).
    controller('sessionCtrl', function($scope, $http, $routeParams, $location) {
        $scope.uuid = $routeParams.uuid;

        function fetch_benchmarks(session_uuid) {
            var url = "/api/v1/session/" + session_uuid;

            $http.get(url).then(function(response) {
                $scope.benchmarks_list = response.data;
            });
        }

        $scope.fetch_benchmarks = fetch_benchmarks;

        $scope.new_benchmark = function() {
            // var url = "/api/v1/session/" + $scope.uuid;

            // $http.post(url).then(function(response) {
            //     console.log(response.data); 

            //     fetch_benchmarks($scope.uuid);
            // });

            var url = $location.path()+'/new_benchmark';
            $location.path(url);
        };

        fetch_benchmarks($scope.uuid);
    });
