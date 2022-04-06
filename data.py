
class NetworkSettings:

    def __init__(self,
                 api_key,
                 api_secret,
                 ):
        self.api_key: str = api_key
        self.api_secret: str = api_secret

    def set_api_key(self, api_key):
        self.api_key = api_key

    def set_api_secret(self, api_secret):
        self.api_secret = api_secret
