import webbrowser
app_id = '8189951'
vk_request_url = (f'https://oauth.vk.com/authorize?client_id={app_id}&scope=8198'
                  f'&redirect_uri=https://oauth.vk.com/blank.html&display=page&response_type=token')
response = webbrowser.open(vk_request_url)
