import "./scss/base.scss";

$(document).ready(
    function() {
        /* Fix `nav-link` display */
        let pathname = window.location.pathname
        $("a[href='/']").toggleClass('active')
        $(`a[href='${pathname}']`).toggleClass('active')
    }
)
