$(function () {
    $('.bookmark').on('click', function () {
        $.getJSON($SCRIPT_ROOT + '/_bookmark', {
            id: $(this).attr('id').slice(3),
            marked: $(this).hasClass('marked')
        }, function (data) {
            if (data.bookmark == 'true') {
                // must find a way to have flask provide these img src urls
                $('#bm-' + data.id).attr('src', data.u);
                $('#bm-' + data.id).removeClass('unmarked').addClass('marked');
            }
            else {
                $('#bm-' + data.id).attr('src', data.u);
                $('#bm-' + data.id).removeClass('marked').addClass('unmarked');
            }
        });
    });
    return false;
});
