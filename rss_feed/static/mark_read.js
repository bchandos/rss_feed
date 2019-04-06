$(function () {
    $('.marker').on('click', function () {
        $.getJSON($SCRIPT_ROOT + '/_mark_read', {
            id: $(this).attr('id').slice(3)
        }, function (data) {
            $('article#' + data.id).fadeOut("200", function () {
                $('article#' + data.id).removeClass("unread").addClass("read invisible");
                /*  removes the display: none added by fadeOut
                    and allow the standard CSS to control display */
                $('article#' + data.id).css("display", "");
            });
        });
        return false;
    });
});