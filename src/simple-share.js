/*
 * simple-share
 * From: @yujiangshui
 *     https://github.com/yujiangshui/simple-share.js
 *
 * Licensed under the MIT license.
 */

let SimpleShare = function (options) {

  // get share content
  options = options || {};
  var url = options.url || window.location.href;
  var title = options.title || document.title;
  var content = options.content || '';
  var pic = options.pic || '';

  // fix content format
  url = encodeURIComponent(url);
  title = encodeURIComponent(title);
  content = encodeURIComponent(content);
  pic = encodeURIComponent(pic);

  // share target url
  var weibo = 'http://service.weibo.com/share/share.php?url={url}&title={title}&pic={pic}&searchPic=false';
  var facebook = 'https://www.facebook.com/sharer/sharer.php?u={url}&t={title}&pic={pic}';
  var twitter = 'https://twitter.com/intent/tweet?text={title}&url={url}';
  var linkedin = 'https://www.linkedin.com/shareArticle?title={title}&summary={content}&mini=true&url={url}&ro=true';
  var weixin = 'http://qr.liantu.com/api.php?text={url}';

  // replace content functions
  function replaceAPI (api) {
    api = api.replace('{url}', url);
    api = api.replace('{title}', title);
    api = api.replace('{content}', content);
    api = api.replace('{pic}', pic);

    return api;
  }

  // share target
  this.weibo = function() {
    window.open(replaceAPI(weibo));
  };
  this.facebook = function() {
    window.open(replaceAPI(facebook));
  };
  this.twitter = function() {
    window.open(replaceAPI(twitter));
  };
  this.linkedin = function() {
    window.open(replaceAPI(linkedin));
  };

  this.weixin = function() {
    let qrcode = new QRCode("weixin-qrcode", {
        text: title || '分享链接',
        width: 132,
        height: 132,
        colorDark : "#000000",
        colorLight : "#ffffff",
        correctLevel : QRCode.CorrectLevel.H
    });
    qrcode.makeCode(decodeURIComponent(url));
  };

};

export {SimpleShare}
