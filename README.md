### 1. 确认需求

1. Post页面
2. 登录注册(不包含手机号码登录)
3. 标签分类
4. 搜索
5. 点赞
6. 收藏
7. 评论
8. 用户(关注，个人设置)
9. 热门分享/最新分享Tab
10. 首页Feed

### 2. 技术选型

1. Flask Web框架 相关扩展
2. SQLALchemy
3. Bootstrap(CSS)
4. jQuery(Javascript交互)
5. Redis(键值对数据库，缓存)
6. MySQL(数据)
7. Elasticsearch(搜索)

### 3. 设计表结构(Model)

1. User
2. Contact
3. Post
4. Comment
5. Like
6. Collect
7. Tag

### 4. 搭建Flask应用

### 5. 表结构的管理(Flask-migrate)

### 6. 准备数据(写爬虫)

### 7. 使用Jinja2模板

### 8. 使用Bootstrap

### 9. 前端开发环境

### 10. 完成Post页面样式

### 11. 注册和登录

### 12. 用户个人设置页面

### 13. 标签功能

### 14. 搜索(Elasticsearch)

### 15. 使用消息队列/Celery处理事件

### 16. 点赞/收藏

### 17. 评论

### 18. Header里面的用户下拉菜单

### 19. 我的点赞/我的收藏页面

### 20. 热门分享/最新分享Tab

### 21. 关注关系

### 22. 分享

### 23. 首页Feed

### 24. 完整测试一遍
  - 测试环境：
    - Ubuntu18 + Python3.6 + Mysql5.7 + Redis4.0 + Elasticsearch7.6 + Npm6.9
    - pip install -r requirements.txt

1. 设置虚拟环境
   ```
   pipenv shell
   ```

2. 开启Flask和Celery
    ```
    FLASK_APP=app.py FLASK_ENV=development flask run

    celery -A handler worker -l info
    ```

3. 重置数据库及Redis缓存，重新生成用户和爬取文章
    ```
    FLASK_APP=manage.py flask initdb
    ```

4. 运行前端工程，生成js文件，管理前端css
    ```
    npm install
    npm run build
    ```
