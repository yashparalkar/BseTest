from pushbullet import PushBullet
import os

access_token = os.environ.get('pbKey')
pb = PushBullet(access_token)

pb.push('Greeting', "Hello there")

