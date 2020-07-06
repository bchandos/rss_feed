// Delete feed
function deleteFeed(elem) {
    let id = $(elem).attr('data-feedID');
    $('#delete-warning-modal').css('display', 'block');
    $('#bigScaryDeleteButton').on('click', function () {
        $('#delete-warning-modal').css('display', '');
        window.location.href = $SCRIPT_ROOT + '/' + id + '/delete';
        })
}

// Mark Read
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
                    $('article#' + data.id).css("display", "");
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

// Bookmarks
$(function () {
    $('.bookmark').on('click', function () {
        let target = $(this);
        $.getJSON($SCRIPT_ROOT + '/_bookmark', {
            id: $(this).attr('data-id'),
            marked: $(this).attr('data-marked')
        }, function (data) {
            if (data.bookmark == 'true') {
                target.children('i').text('bookmark');
                target.attr('data-marked', 'true');
            }
            else {
                target.children('i').text('bookmark_border')
                target.attr('data-marked', 'false');
            }
        });
    });
    return false;
});

// Show / hide
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