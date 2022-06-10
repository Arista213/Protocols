import requests
from settings import Settings


class RequestHandler:
    def __init__(self):
        pass

    @staticmethod
    def get_friends_response():
        return requests.get((f'https://api.vk.com/method/friends.get?'
                             f'&access_token={Settings.token}&v=5.131'))

    @staticmethod
    def get_wall_post_response():
        return requests.get(f'https://api.vk.com/method/wall.get?'
                            f'access_token={Settings.token}&v=5.131')

    @staticmethod
    def get_wall_post_likes_response(post_id):
        return requests.get(
            f'https://api.vk.com/method/likes.getList?type=post&item_id={post_id}&friends_only=1&extended=1&'
            f'access_token={Settings.token}&v=5.131')

    @staticmethod
    def get_wall_post_comments_response(post_id):
        return requests.get(f'https://api.vk.com/method/wall.getComments?post_id={post_id}&extended=1&'
                            f'access_token={Settings.token}&v=5.131')
