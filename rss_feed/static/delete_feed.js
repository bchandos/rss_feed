function deleteFeed(elem) {
    let id = $(elem).attr('data-feedID');
    $('#delete-warning-modal').css('display', 'block');
    $('#bigScaryDeleteButton').on('click', function () {
        $('#delete-warning-modal').css('display', '');
        window.location.href = $SCRIPT_ROOT + '/' + id + '/delete';
        })
}