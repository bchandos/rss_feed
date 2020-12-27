let _state = {
    showRead: false,
};


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
            if (!_state.showRead && data.read == 'Read') {
                $(`article#${data.id}`).fadeOut("200", function () {
                    $(`article#${data.id}`).removeClass("unread").addClass("read w3-hide w3-border-pale-blue");
                    /*  removes the display: none added by fadeOut
                        and allow the standard CSS to control display */
                    $(`article#${data.id}`).css("display", "");
                });
                label = "Mark Unread";
            } else if (data.read == 'Read') {
                $(`article#${data.id}`).removeClass("unread w3-border-light-blue").addClass("read w3-border-pale-blue");
                label = "Mark Unread";
            }
            else {
                $(`article#${data.id}`).removeClass("read w3-border-pale-blue").addClass("unread w3-border-light-blue");
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
$(function () {
    $("#show_read").on("click", function () {
        _state.showRead = !_state.showRead;
        let btn = $('#more-articles-btn');
        if (_state.showRead) {
            $("article.read").removeClass("w3-hide");
            $(this).text("Hide Read");
            if (btn.attr('more-unread') === 'True') {
                btn.addClass('w3-show');
                btn.removeClass('w3-hide');
            }
        }
        else {
            $("article.read").addClass("w3-hide");
            $(this).text("Show Read");
            if (btn.attr('more-unread') === 'True' && btn.attr('more-read') === 'False') {
                btn.addClass('w3-hide');
                btn.removeClass('w3-show');
            }
        }
    });
});


// Show more button...

$(function() {
    let btn = $('#more-articles-btn');
    if (btn.attr('more-read') === 'True') {
        btn.addClass('w3-show');
        btn.removeClass('w3-hide')
    } else if (btn.attr('more-unread') === 'True' && _state.showRead) {
        btn.addClass('w3-show');
        btn.removeClass('w3-hide')
    } else {
        btn.addClass('w3-hide');
        btn.removeClass('w3-show');
    }

})

$(function () {
    $('#more-articles-btn').on('click', function() {
        let startAt = $(this).attr('article-count');
        let feedId = $(this).attr('feed-id');
        $.get($SCRIPT_ROOT + '/_more_articles', {
            feed_id: feedId || '',
            start_at: startAt
        }, function (response) {
            $('#more-articles-target').replaceWith(response);
            // New articles will be hidden by default; set visibility 
            // based on current showRead state
            if (_state.showRead) {
                $("article.read").removeClass("w3-hide");
            }
            else {
                $("article.read").addClass("w3-hide");
                $(this).text("Show Read");
            }
        });
    });
})

// Article preview modal
$(function () {
    $('.article-preview').on('click', function() {
        let articleId = $(this).attr('data-id');
            $.get($SCRIPT_ROOT + '/_article_contents', {
            id: articleId
        }, function(response) {
            $('#article-content-target').html(response.article_contents);
            $('#article-content-modal').removeClass('w3-hide').addClass('w3-show');
        })
    })
})