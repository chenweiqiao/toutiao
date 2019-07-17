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

### 22. 第三方登录

### 23. 分享

### 24. 首页Feed

### 25. 完整测试一遍
  - 测试环境：
    - Ubuntu18 + Python3.6 + Mysql5.7 + Redis4.0 + Elasticsearch7.0 + Npm3.5
    - pip install -r requirements.txt
      - `安装Github依赖包时可能会引用错误，需要把对应依赖包卸载后重新安装`
      - pip install -e git+https://github.com/chenweiqiao/flask-security.git@develop#egg=flask_security
      - pip install -e git+https://github.com/chenweiqiao/social-core.git@master#egg=social_core
      - pip install -e git+https://github.com/chenweiqiao/social-app-flask-sqlalchemy.git@master#egg=social_flask_sqlalchemy
      - pip install -e git+https://github.com/chenweiqiao/social-storage-sqlalchemy.git@master#egg=social_sqlalchemy
      - pip install -e git+https://github.com/chenweiqiao/social-app-flask.git@master#egg=social_flask 
    - Github登录验证
      - 首先得有Github帐户
      - 登录后，在Settings创建[OAuth Apps](https://github.com/settings/applications/new)
        - Application name
          - Toutiao
        - Homepage URL
          - http://toutiao.ie
        - Authorization callback URL
          - http://toutiao.ie/complete/github
      - 打开[OAuth Apps](https://github.com/settings/developers)刚才新建的App，复制`Client ID`和`Client Secret`到local_settings.py中

1. Initdb and flush redis
    ```
    FLASK_APP=manage.py flask initdb
    ```

3. 重启Flask和Celery
    ```
    FLASK_APP=app.py FLASK_ENV=development  flask run --port=8080

    celery -A handler worker -l infov
    ```

4. 运行前端工程，生成js文件，管理前端css
    ```
    cnpm install
    npm run build
    ```

5. 爬虫抓取coolshell的`文章RSS`作数据填充
    ```
    python crawling.py
    ```

6. 创建2个用户
    ```
    分别通过邮箱和Github注册1个用户
    ```
