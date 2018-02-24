import os,json
os.environ["TELEGRAM_TOKEN"] = "509785164:AAF1MQSLMa1RMFJyFnFwbCc_4od26ZUGYOs"
os.environ["DYNAMODB_TABLE"] = "ask-the-potato-db"
from handleReceivedMessages import main as handleReceivedMessages
from distributeMessages import main as distributeMessages



def handleReceivedMessagesTest():

    body = json.dumps(
    {'message':{
        'text':'Why is there no Wifi in my ICE?',
        'chat':{
            'id':'282364504',
            'first_name':'Walter'
    }}})
    event = {'body':body}
    print(handleReceivedMessages(event,''))
    
def distributeMessagesTest():
    event = {
    'Records': [{
        'EventSource': 'aws:sns',
        'EventVersion': '1.0',
        'EventSubscriptionArn': 'arn:aws:sns:us-east-1:528227264112:ask-the-potato-question-asked:f2f76f99-0a16-4ce6-a411-5b181da0d493',
        'Sns': {
            'Type': 'Notification',
            'MessageId': '40b51ce7-168a-590e-8291-4fe2cec32c7d',
            'TopicArn': 'arn:aws:sns:us-east-1:528227264112:ask-the-potato-question-asked',
            'Subject': None,
            'Message': '{"question": "Walter asks: Why is there no Wifi in my ICE?", "chat_id": "282364504"}',
            'Timestamp': '2018-02-20T08:02:17.953Z',
            'SignatureVersion': '1',
            'Signature': 'bKggal6u6OOJtY8KekYQdCkOcYa54K/GJQekPsu1QXjtw39L7JTU+MLtRrNOxecjx+s3z+ax8BHyemdL86gQtkpXLHBjX8hUP8L0MoA85eKTnUvwgVE+tFmMGfTRYMs5fnKCGbDj32XKDknrt3kJIXHYQoFe26C3uYw7+jQtVzEOvDtaycWAdF48hzAh/ZW8HQ9moJX4QZvuaxP/O2z+WuPTYK7mUoveNZlFqcTLEFHEUsqomSRp23rw7joso1eTHxiKMPwdfSTHrhXK1K2u6Td5yqz1vHBRE8IEC8gseKVptzk86XeVw/8l6k1aghSKMkfN2YHq4JUfATkeMdFnjw==',
            'SigningCertUrl': 'https://sns.us-east-1.amazonaws.com/SimpleNotificationService-433026a4050d206028891664da859041.pem',
            'UnsubscribeUrl': 'https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:528227264112:ask-the-potato-question-asked:f2f76f99-0a16-4ce6-a411-5b181da0d493',
            'MessageAttributes': {}
            }
        }]
    }
    print(distributeMessages(event,''))
    
#print("\n***\ntesting handleReceivedMessages:")
#handleReceivedMessagesTest()
print("\n***\ntesting distributeMessages:")
distributeMessagesTest()