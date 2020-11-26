Vue.component('cms-search-result', {
    props: ['searchStr', 'searchApi'],
    data: function () {
        return {
            pager: {},
            items: [],
        }
    },
    mounted: function() {
        this.fetchPage();
    },
    methods: {
        fetchPage: function(page=1) {
            page = parseInt(page);
            var params = {page:page, search:this.searchStr};
            var ctrl = this;

            axios.get(ctrl.searchApi, params).then(function(response) {
                ctrl.pager.previous = response.data.previous;
                ctrl.pager.next = response.data.next;
                ctrl.pager.currentPage = page;
                ctrl.pager.totalHits = response.data.count;
                if (response.data.next)
                    ctrl.pager.totalPages = Math.ceil(response.data.count / response.data.results.length);
                else
                    ctrl.pager.totalPages = page
                ctrl.items = response.data.results;

                // update url query params
                if (history.pushState) {
                    var newurl = window.location.pathname + '?' + new URLSearchParams(params).toString();
                    window.history.pushState({ path:newurl }, '', newurl);
                }

            }).catch(function(error) {
                console.error(error);
                console.log(params);
            })
        },

        nextPage: function() {
            if (this.pager.next)
                this.fetchPage(this.pager.currentPage + 1);
        },

        previousPage: function() {
            if (this.pager.previous)
                this.fetchPage(this.pager.currentPage - 1);
        },
    },
    template: '#search-result',
})
