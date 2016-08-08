/* jshint globals: false */
angular.module('ocperfApp', ['ngSanitize', "checklist-model"])
    .service('ocperf_rest', function($http, $sce) {
        function get_emap() {
            return $http.get('/api/v1/emap').then(function(response) {
                return response.data;
            });
        }

        return {
            get_emap: get_emap
        };
    })
    .controller('ocperfCtrl', function($scope, $http, $sce, ocperf_rest, $window) {
        var script = null;
        $scope.workload = "/home/nhardi/code/cl_forward/bin/x86_64/Release/clpixel -serial -bin -file /home/nhardi/code/cl_forward/bin/x86_64/Release/test.small.arg";
        $scope.events = ["arith.mul"];
        $scope.interval = 100;
        $scope.search_term = "";
        $scope.streaming = true;

        function getDiv() {
            return $http.get("/plot/plot.html").then(function(response) {
                $scope.plain_html = $sce.trustAsHtml(response.data);
            });
        }

        function getScript() {
            return $http.get("/plot/script.js").then(function(response) {
                script = response.data;
            });
        }

        function loadPlot() {
            /* jshint ignore: "eval" */
            eval(script);
        }

        function fetchPlot() {
            getDiv().then(getScript).then(loadPlot);
        }

        function getAutoloadScript() {
            return $http.get("/plot/autoload_script.js").then(function(response) {
                // $scope.plain_html = $sce.trustAsHtml(response.data);
                var s_tag = response.data;
                $("#some_script").append($(s_tag));
            });
        }

        function startAutoloadScript() {
            console.log("should start autoload script");
            console.log($scope.plain_html);
        }

        function fetchPlot2() {
            getAutoloadScript().then(startAutoloadScript);
            // console.log("redirecting");
            // $window.open("http://127.0.0.1:8000/index.html");
        }

        $scope.run = function() {
            var data = {
                workload: $scope.workload,
                events: $scope.events,
                interval: $scope.interval,
                streaming: $scope.streaming
            };

            console.log(data);

            $http.post("/api/v1/run", data=data).then(fetchPlot2);
        };

        ocperf_rest.get_emap().then(function(emap) {
            $scope.emap = emap;
        });
    });
