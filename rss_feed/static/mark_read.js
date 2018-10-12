$(function () {
    $('article.item').on('click', function () {
        $.getJSON($SCRIPT_ROOT + '/_mark_read', {
            id: $(this).attr('id')
        }, function (data) {
            $('article#' + data.id).fadeOut('200', function () {
                $('article#' + data.id).removeClass("unread").addClass("read");
            });
        });
        return false;
    });
});