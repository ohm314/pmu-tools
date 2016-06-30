angular.module('ocperfApp', ['ngSanitize'])
    .controller('ocperfCtrl', function($scope, $http, $sce) {
        var script = null;

        $scope.workload = "/home/nhardi/code/cl_forward/bin/x86_64/Release/clpixel -serial -bin -file /home/nhardi/code/cl_forward/bin/x86_64/Release/test.small.arg"
        $scope.events = ["arith.mul"];
        $scope.interval = 100;

        function getDiv() {
            return $http.get("/plot/plot.html").then(function(response) {
                $scope.plain_html = $sce.trustAsHtml(response.data);
            });
        };

        function getScript() {
            return $http.get("/plot/script.js").then(function(response) {
                script = response.data;
            });
        };

        function loadPlot() {
            eval(script);
        }

        function fetchPlot() {
            getDiv().then(getScript).then(loadPlot);
        }

        $scope.run = function() {
            $http.post("/api/v1/run", data={
                workload: $scope.workload,
                events: $scope.events,
                interval: $scope.interval
            }).then(fetchPlot);
        }
    });
