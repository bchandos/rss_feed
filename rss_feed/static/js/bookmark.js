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
