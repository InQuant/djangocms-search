Vue.component('cms-search-input-group', {
  props: ['placeholder', 'searchResultUrl' ],
  data: function () {
    return {
      searchStr: '',
    }
  },
  methods: {
    execSearch: function () {
      if (!this.searchStr)
        return;
      window.location = this.searchResultUrl + '?' + new URLSearchParams({search:this.searchStr}).toString();
    },
  },
  template:
      '<b-input-group id="cms-search-input-group" class="input-group-sm">' +
      ' <b-form-input id="cms-search-input" :placeholder="placeholder" v-model="searchStr" ' +
      '  v-on:keyup.enter="execSearch()"></b-form-input>' +
      ' <b-input-group-append>' +
      '   <b-button @click="execSearch()" variant="light"><b-icon icon="search"></b-icon></b-button>' +
      ' </b-input-group-append>' +
      '</b-input-group>'
})
