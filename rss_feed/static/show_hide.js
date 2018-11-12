$("#show_hide :checkbox").change(function () {
    if (this.checked) {
        $("article.read").removeClass("invisible");
        $("label[for='show_read']").text("Hide Read");
    } else {
        $("article.read").addClass("invisible");
        $("label[for='show_read']").text("Show Read");
    }
});