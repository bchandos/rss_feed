$(function () {
    $('p.body').on('click', function () {
        $.getJSON($SCRIPT_ROOT + '/_mark_read', {
            id: $(this).attr('id')
        }, function (data) {
            $('#span' + data.id).text(data.read);
        });
        return false;
    });
});