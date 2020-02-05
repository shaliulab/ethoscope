(function(){
    var experimentsController = function($scope, $http, $timeout, $routeParams, $window, $interval){

        $http.get('/browse/null').success(function(data){
            $scope.backup_files = data.files;
        });

        $http.get('/devices').success(function(data){
            $scope.devices = data;
        });
        
        $http.get('/runs_list').success(function(data){
            $scope.runs = data;
            for (ix in $scope.runs) {
                
                // reformat start and end times in a js compatible format
                if ( $scope.runs[ix].end_time != '' ) { $scope.runs[ix].end_time = $scope.runs[ix].end_time.split(".")[0].replace(/-/g,'/') };
                $scope.runs[ix].start_time = $scope.runs[ix]['start_time'].split(".")[0].replace(/-/g,'/') ;

                // check the mtime of the associated db file and records whether a backup file is on the node
                var db_name = $scope.runs[ix].experimental_data.split('\\').pop().split('/').pop();
                if ( $scope.backup_files[db_name] != undefined ) 
                    { $scope.runs[ix].last_backup = $scope.backup_files[db_name]['mtime'];
                      $scope.runs[ix].has_backup = true;
                    }
                else
                    { $scope.runs[ix].has_backup = false };
            }

        });

        $scope.compare_time = function (t1, t2) {
            //compare two dates
            //t1 must be a valid date either in unix timestamp or stringformat
            //t2 can also be undefined and in that case the current time is used
            
            t1 = new Date (isNaN(t1) ? t1 : t1 * 1000 );
            
            if ( t2 == undefined ) 
                { t2 = new Date() }
            else
                { t2 = new Date (isNaN(t2) ? t2 : t2 * 1000) };

            return Math.floor ( (t2 - t1) / (60 * 1000) );
            
            }


       refresh_data = $interval(function () {
              console.log("refresh");
          }, 10000);
          
        //clear interval when scope is destroyed
        $scope.$on("$destroy", function(){
            $interval.cancel(refresh_data);
            //clearInterval(refresh_data);
        });

}

 angular.module('flyApp').controller('experimentsController', experimentsController);

})()
