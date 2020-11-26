Vue.component('cms-search-result', {
    props: ['searchStr', 'searchApi'],
    data: function () {
        return {
            pager: {},
            items: [],
        }
    },
    created: function() {
        this.fetchPage();
    },
    methods: {
        fetchPage: function(page=1) {
            page = parseInt(page);
            var params = {page:page, search:this.searchStr};

            axios.get(this.searchApi, params).then(function(response) {
                this.pager.previous = response.data.previous;
                this.pager.next = response.data.next;
                this.pager.currentPage = page;
                this.pager.totalHits = response.data.count;
                // FIXME: instead of 10 -> hitsPerPage from api
                this.pager.totalPages = Math.ceil(response.data.count / 10);
                this.items = response.data.results;

                // update url params
                location.search = new URLSearchParams(params).toString();
            }).catch(function(error) {
                console.log(error);
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
