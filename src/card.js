import "./css/font.css";
import "./follow";

var $likeBtn = $('.like-button');
var $collectBtn = $('.collect-button');

/* Fix multi-cards for `like` and `collect` */
$likeBtn.on('click', (event)  => {
    let $this = $(event.currentTarget);
    let url = $this.data('url');
    let $isLiked = $this.hasClass('liked')
    
    $.ajax({
        url: `/api/${url}`,
        type: $isLiked ? 'DELETE' : 'POST',
        data: {},
        success: function(rs) {
            if (!rs.r) {
                let isLiked = rs.data.is_liked;
                if ($isLiked != isLiked) {
                    $isLiked = isLiked;
                    $this.toggleClass('liked');
                    $this.find('span').text(rs.data.n_likes);
                    if (isLiked) {
                        $this.find('i').addClass('toutiao-thumbsup').removeClass('toutiao-thumbsoup');
                    } else {
                        $this.find('i').addClass('toutiao-thumbsoup').removeClass('toutiao-thumbsup');
                    }
                }
            } else {
                alert('点赞失败, 请稍后再试');
            }
        }
    });
});


$collectBtn.on('click', (event)  => {
    let $this = $(event.currentTarget);
    let url = $this.data('url');
    let $isCollected = $this.hasClass('collected');

    $.ajax({
        url: `/api/${url}`,
        type: $isCollected ? 'DELETE' : 'POST',
        data: {},
        success: function(rs) {
            if (!rs.r) {
                let isCollected = rs.data.is_collected;
                if ($isCollected != isCollected) {
                    $isCollected = isCollected;
                    $this.toggleClass('collected');
                    if (isCollected) {
                        $this.find('i').addClass('toutiao-bookmark').removeClass('toutiao-bookmarko');
                    } else {
                        $this.find('i').removeClass('toutiao-bookmark').addClass('toutiao-bookmarko');
                    }
                }
            } else {
                alert('关注失败, 请稍后再试');
            }
        }
    });
});
