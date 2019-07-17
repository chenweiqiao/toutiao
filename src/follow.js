var $followBtn = $('.follow-button');
var $isFollowed = $followBtn.hasClass('followed');

$followBtn.on('click', (event)  => {
    let $this = $(event.currentTarget);
    let url = $this.data('url');

    $.ajax({
        url: `/api/${url}`,
        type: $isFollowed ? 'DELETE' : 'POST',
        data: {},
        success: function(rs) {
            if (!rs.r) {
                let isFollowed = rs.data.is_followed;
                if ($isFollowed != isFollowed) {
                    $isFollowed = isFollowed;
                    $this.toggleClass('followed');
                    if ($isFollowed) {
                        $this.text('已关注TA');
                    } else {
                        $this.text('关注TA');
                    }
                }
            } else {
                alert('关注失败, 请稍后再试');
            }
        }
    });
});
