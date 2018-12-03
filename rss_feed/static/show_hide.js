$("#show_read").on("click", function () {
    if ($(this).text() == "Show Read") {
        $("article.read").removeClass("invisible");
        $(this).text("Hide Read");
    }
    else {
        $("article.read").addClass("invisible");
        $(this).text("Show Read");
    }
});