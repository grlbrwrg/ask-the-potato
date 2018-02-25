import os
os.environ["TELEGRAM_TOKEN"] = "509785164:AAF1MQSLMa1RMFJyFnFwbCc_4od26ZUGYOs"
from handleReceivedMessages import parseTelegramMessage
from distributeMessages import getChatIdsfromQueue
def test_parseTelegramMessage():
    body = {'message':{'text':'Test','chat':{'id':1,'first_name':'Testbert'},'reply_to_message':{'text':'ReplyToTest'}}}
    result = {'isTextMessage':True,'message':'Test','chat_id':1,'first_name':'Testbert','reply_to_message_text':'ReplyToTest'}
    assert parseTelegramMessage(body) == result

def test_getChatIdsfromQueue():
    amount,queue_in = 1,[11,22,33]
    queue_out,chat_ids = [22,33,11],[11]
    assert getChatIdsfromQueue(amount,queue_in) == (queue_out,chat_ids)
