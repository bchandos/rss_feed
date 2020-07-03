// TODO: use data-args for much of this
$(function () {
    $('.marker').on('click', function () {
        let label;
        let target = $(this);
        $.getJSON($SCRIPT_ROOT + '/_mark_read', {
            id: $(this).attr('data-id')
        }, function (data) {
            if ($("#show_read").text() == 'Show Read' && data.read == 'Read') {
                $('article#' + data.id).fadeOut("200", function () {
                    $('article#' + data.id).removeClass("unread").addClass("read w3-hide");
                    /*  removes the display: none added by fadeOut
                        and allow the standard CSS to control display */
                    // $('article#' + data.id).css("display", "");
                });
                label = "Mark Unread";
            } else if (data.read == 'Read') {
                $('article#' + data.id).removeClass("unread").addClass("read");
                label = "Mark Unread";
            }
            else {
                $('article#' + data.id).removeClass("read").addClass("unread");
                label = "Mark Read";
            }
            target.text(label)
        });

        return false;
    });
});