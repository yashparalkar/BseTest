from pushbullet import PushBullet

access_token = os.environ.get('pbKey')
pb = PushBullet(access_token)

pb.push('Greeting', "Hello there")

