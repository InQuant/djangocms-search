var cmssearch = angular.module('cms.search', []);

function cngSearchInputFormCtrl($scope, $element, $attrs) {
    console.log('cngSearchInputFormCtrl');
    var ctrl = this;

    ctrl.$onInit = function () {
        console.log(ctrl.resolve);
        ctrl.searchStr = ctrl.resolve.searchStr;
    };

    ctrl.execSearch = function () {
        ctrl.close({$value: ctrl.searchStr});
    };

    ctrl.onInputKey = function(ev) {
        if (ev.which === 13) ctrl.execSearch();
    }

    ctrl.cancel = function () {
        ctrl.dismiss({$value: 'cancel'});
    };
}
cmssearch.component('cngSearchInputForm', {
    template:
      '<div class="p-3 d-flex">' +
      '  <input id="cms-search-input" class="border-0" placeholder="Suchwort" type="text" ng-model="$ctrl.searchStr"' +
      '    ng-keypress="$ctrl.onInputKey($event)">' +
      '  <a class="ml-2" href ng-click="$ctrl.execSearch()"><i class="fas fa-search"></i></a>' +
      '</div>',
    controller: cngSearchInputFormCtrl,
    bindings: {
        resolve: '<',
        close: '&',
        dismiss: '&'
    },
});


function cngSearchResultCtrl($scope, $element, $attrs, $http, $httpParamSerializer, $location) {
    console.log('cngSearchResultCtrl');
    var ctrl = this;
    ctrl.pager = {};
    ctrl.items = [];

    ctrl.fetchPage = function(page=1) {
        page = parseInt(page);
        var params = {page:page, search:ctrl.searchStr};
        var url = ctrl.searchApi + '?' + $httpParamSerializer(params);

        $http.get(url).then(function(response) {
            ctrl.pager.previous = response.data.previous;
            ctrl.pager.next = response.data.next;
            ctrl.pager.currentPage = page;
            ctrl.pager.totalHits = response.data.count;
            // FIXME: instead of 10 -> hitsPerPage from api
            ctrl.pager.totalPages = Math.ceil(response.data.count / 10);
            ctrl.items = response.data.results;

            // update url params
            $location.search(params);
        }, function(response) {
            console.log(response);
        });
    }

    ctrl.nextPage = function() {
        if (ctrl.pager.next)
            ctrl.fetchPage(ctrl.pager.currentPage + 1);
    }

    ctrl.previousPage = function() {
        if (ctrl.pager.previous)
            ctrl.fetchPage(ctrl.pager.currentPage - 1);
    }

    ctrl.inputKeyPressed = function(ev) {
        if (ev.which === 13) ctrl.fetchPage();
    }

    ctrl.$onInit = function () {
        console.log('search str: ' + ctrl.searchStr);
        ctrl.fetchPage();
    };
}
cmssearch.component('cngSearchResult', {
    templateUrl:  'cms_search/search-result.html',
    controller: cngSearchResultCtrl,
    bindings: {
        searchStr: '@',
        searchApi: '@'
    },
});
