// TODO: use data-args
$("#show_read").on("click", function () {
    if ($(this).text() == "Show Read") {
        $("article.read").removeClass("w3-hide");
        $(this).text("Hide Read");
    }
    else {
        $("article.read").addClass("w3-hide");
        $(this).text("Show Read");
    }
});