import "./scss/tag.scss";
import "./css/font.css";

import "./card";

$('#tag-tab a').on('click', (event) => {
    event.preventDefault()
    let $this = $(event.currentTarget);
    let url = $this.data('url');
    window.location.replace(url);
})
