import json
from collections import defaultdict
from urllib.parse import urlsplit, parse_qs

from request_handler import RequestHandler
from settings import Settings


class User:
    def __init__(self, name, surname):
        self.first_name = name
        self.last_name = surname

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


def main():
    url = (input('Введите ссылку: \n')).replace('#', '?')
    queries = parse_qs(urlsplit(url).query)
    token = queries['access_token'][0]
    Settings.token = token
    posts = json.loads(RequestHandler.get_wall_post_response().content)['response']['items']
    friends = json.loads(RequestHandler.get_friends_response().content)['response']['items']
    users_by_id = {}
    stat = defaultdict(lambda: defaultdict(int))
    i = -1
    for post in posts:
        i += 1
        post_id = post['id']
        print(f'progress: {i}/{len(posts)}')
        post_likes = json.loads(RequestHandler.get_wall_post_likes_response(post_id).content)
        if 'response' in post_likes:
            likes_items = post_likes['response']['items']
        post_comments = json.loads(RequestHandler.get_wall_post_comments_response(post_id).content)
        if 'response' in post_comments and 'profiles' in post_comments['response']:
            comment_profiles = post_comments['response']['profiles']
            for comment in comment_profiles:
                if comment['id'] not in friends:
                    continue
                if comment['id'] not in users_by_id:
                    users_by_id[comment['id']] = User(comment['first_name'], comment['last_name'])
                stat[comment['id']]['comments'] += 1
        if 'response' in post_likes:
            for like in likes_items:
                if like['id'] not in users_by_id:
                    users_by_id[like['id']] = User(like['first_name'], like['last_name'])
                stat[like['id']]['likes'] += 1
    sorted_stat = dict(sorted(stat.items(), key=lambda item: item[1]['likes'] + item[1]['comments'], reverse=True))
    print('Список друзей в порядке убывания лайков + комментов')
    for key in sorted_stat:
        a = sorted_stat[key]["likes"]
        print(f'{users_by_id[key]}: Likes {sorted_stat[key]["likes"]} + Comments {sorted_stat[key]["comments"]}')


if __name__ == '__main__':
    main()
