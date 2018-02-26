import os
os.environ["TELEGRAM_TOKEN"] = "509785164:AAF1MQSLMa1RMFJyFnFwbCc_4od26ZUGYOs"
os.environ["SNS_QUESTION_ASKED_ARN"] = ""
from handleReceivedMessages import parseTelegramMessage
from distributeMessages import getChatIdsfromQueue
from moto import mock_sns
import boto3
def test_parseTelegramMessage():
    body = {'message':{'text':'Test','chat':{'id':1,'first_name':'Testbert'},'reply_to_message':{'text':'ReplyToTest'}}}
    result = {'isTextMessage':True,'message':'Test','chat_id':1,'first_name':'Testbert','reply_to_message_text':'ReplyToTest'}
    assert parseTelegramMessage(body) == result

def test_getChatIdsfromQueue():
    amount,queue_in = 1,[11,22,33]
    queue_out,chat_ids = [22,33,11],[11]
    assert getChatIdsfromQueue(amount,queue_in) == (queue_out,chat_ids)
@mock_sns
def test_publishQuestionToSns():
    conn = boto3.client('sns', region_name='us-east-1')
    created = conn.create_topic(Name="test-topic")
    topic_arn = created.get('TopicArn')    
    from handleReceivedMessages import publishQuestionToSns
    response = publishQuestionToSns(282364504,"test",topic_arn)
    assert ('MessageId' in response)