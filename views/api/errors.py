# coding=utf-8
""" Format: ``return code`` ``message`` ``status``"""
unknown_error = (1000, 'unknown error', 400)
access_forbidden = (1001, 'access forbidden', 403)
unimplemented_error = (1002, 'unimplemented error', 400)
not_found = (1003, 'not found', 404)
illegal_state = (1004, 'illegal state', 400)
not_supported = (1005, '暂时不支持此操作', 400)
post_not_found = (1006, 'Post不存在', 400)
