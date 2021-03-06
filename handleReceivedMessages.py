import json
import os
import sys
import traceback
import time
here = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(here, "./vendored"))

import requests
import boto3
from boto3.dynamodb.conditions import Key
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

TOKEN = os.environ['TELEGRAM_TOKEN']
QUESTION_ASKED_ARN = os.environ['SNS_QUESTION_ASKED_ARN']

BASE_URL = "https://api.telegram.org/bot{}".format(TOKEN)

SIGN_UP_STRINGS = {"ASK - I speak english!.":'ask',"ANTWORTEN - Ich spreche Deutsch!":'answer'}
RATING_SYMBOLS = {"grin":u'\U0001F600',"boom":u'\U0001F92F',"laugh":u'\U0001F602',"cry":u'\U0001F622',"celebrate":u'\U0001F64C',"beer":u'\U0001F37A'}
TIMESTAMP = int(time.time() * 1000)

def main(event, context):
    try:
        eventBody = json.loads(event["body"])
        if "callback_query" in eventBody:
            print(eventBody)
            callback_query_id = eventBody["callback_query"]["id"]
            answerTelegramCallbackQuery(callback_query_id)

            chat_id = eventBody["callback_query"]["message"]["chat"]["id"]
            message_id = eventBody["callback_query"]["message"]["message_id"] 
            removeInlineKeyboard(chat_id,message_id)

            message_text = eventBody["callback_query"]["message"]["text"]
            rating = eventBody["callback_query"]["data"]
            updateRatingOfAskerAndSendMessageToAnswerer(message_text,rating,chat_id)
            return {"statusCode": 200}
        telegramMessage = parseTelegramMessage(eventBody)
        chat_id = telegramMessage['chat_id']
        if not telegramMessage['isTextMessage']:
            sendTelegramMessage("Sorry, I can only handle text messages for now :(",chat_id)
            return {"statusCode": 200}
        first_name = telegramMessage['first_name']
        message = telegramMessage['message']
        user = getUserFromDb(chat_id)
        
        if message[:8].upper() == "FEEDBACK":
            feedback = "%s (%s) gave feedback: %s" % (first_name,chat_id,message)
            sendTelegramMessage(feedback,"282364504")
            sendTelegramMessage("Thanks for your feedback!",chat_id)
        elif user == {}:
            if message in SIGN_UP_STRINGS:
                job = SIGN_UP_STRINGS[message]
                addUserToDb(chat_id,job)
                if job == 'answer':
                    addAnswererToQueue(chat_id)
                    signUpMessage = "Du beantwortest jetzt Fragen."
                else:
                    signUpMessage = "You have signed up to ask questions."
                sendTelegramMessage(signUpMessage,chat_id)
            else:
                sendSignUpMessage(chat_id)
            return {"statusCode": 200}
        elif user['job'] == 'ask':
            question = "%s asks: %s" % (first_name,message)         
            publishQuestionToSns(chat_id,question,QUESTION_ASKED_ARN)
            response = "I've sent your question to a few people speaking German. Wait a bit until they answer"
            sendTelegramMessage(response,chat_id)
        elif user['job'] == 'answer':
            if telegramMessage['reply_to_message_text'] == "":
                response = "Um zu antworten, tappe auf die Nachricht und wähle 'Antworten'."
                sendTelegramMessage(response,chat_id)
            else:
                for conversation in user['conversations']:
                    if conversation['question'] == telegramMessage['reply_to_message_text']:
                        answerText = "%s answered: %s" % (first_name,message)
                        sendTelegramMessageWithRating(answerText,conversation['asker'])
                        conversation['answer'] = message
                        updateConversations(chat_id,user['conversations'])
                        addEmptyRatingToAsker(answerText,chat_id,conversation['asker'])
                        sendTelegramMessage("Antwort wurde weitergeleitet!",chat_id)
                        return {"statusCode": 200}
                response = "Sorry, ich konnte die Frage auf deine Antwort nicht finden :(."
                sendTelegramMessage(response,chat_id)
            return {"statusCode": 200}
                    
        else:
            sendSignUpMessage(chat_id)
        return {"statusCode": 200}
    except Exception as e:
        print(e)
        traceback.print_exc()

def addEmptyRatingToAsker(answerText,answererChatId,askerChatId):
    asker = getUserFromDb(askerChatId)
    if "ratings" not in asker:
        ratings = {}
    else:
        ratings = asker["ratings"]
    ratings[answerText] = {"answerer":answererChatId}
    #TODO: Extract updating a user
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    response = table.update_item(
        Key={
            'id': int(askerChatId)
        },
        UpdateExpression="set ratings = :r, updated_at = :u",
        ExpressionAttributeValues={
            ':r': ratings,
            ':u': TIMESTAMP
        },
        ReturnValues="UPDATED_NEW"
    )
    return response

def updateRatingOfAskerAndSendMessageToAnswerer(answerText,rating,askerChatId):
    asker = getUserFromDb(askerChatId)
    if "ratings" not in asker:
        raise Exception("Asker rated answer but didn't have rating object!")
    else:
        ratings = asker["ratings"]
    answererChatId = ratings[answerText]["answerer"]
    ratings[answerText] = {"answerer":answererChatId,"rating":rating}

    #TODO: Extract notifying answerer for stats tracking
    message = "Du hast ein %s für deine Antwort bekommen!" % (RATING_SYMBOLS[rating])
    sendTelegramMessage(message,answererChatId)

    #TODO: Extract updating a user
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    response = table.update_item(
        Key={
            'id': int(askerChatId)
        },
        UpdateExpression="set ratings = :r, updated_at = :u",
        ExpressionAttributeValues={
            ':r': ratings,
            ':u': TIMESTAMP
        },
        ReturnValues="UPDATED_NEW"
    )
    return response    


def parseTelegramMessage(body):
    isTextMessage = False
    message = ""
    if "text" in body["message"]:
        isTextMessage = True
        message = str(body["message"]["text"])
    chat_id = body["message"]["chat"]["id"]
    first_name = body["message"]["chat"]["first_name"]
    reply_to_message_text = ""
    if 'reply_to_message' in body["message"]:
        reply_to_message_text = body['message']['reply_to_message']['text']
    return({
        'isTextMessage' : isTextMessage,
        'message': message,
        'chat_id': chat_id,
        'first_name': first_name,
        'reply_to_message_text': reply_to_message_text}
        )

def getUserFromDb(chat_id):
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    request = table.get_item(Key={'id':int(chat_id)})
    if not 'Item' in request:
        return {}
    return request['Item']

def addUserToDb(chat_id,job):
    user = {
    'id': int(chat_id),
    'updated_at': TIMESTAMP,
    'job':job,
    'created_at': TIMESTAMP,
    'conversations': [],
    }
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    table.put_item(Item=user)

def addAnswererToQueue(chat_id):
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    dynamoQueue = table.get_item(Key={'id':0})
    if not 'queue' in dynamoQueue['Item']:
        raise Exception("Couldn't find queue in payload!")
    queue = dynamoQueue['Item']['queue']
    queue.append(int(chat_id))
    table.update_item(
        Key={'id': 0},
        UpdateExpression="set queue = :q",
        ExpressionAttributeValues={':q': queue},
        ReturnValues="UPDATED_NEW"
    )

def sendTelegramMessage(text,chat_id):
    reply_markup = {'hide_keyboard':True}
    payload = {"text": str(text).encode("utf8"), "chat_id": chat_id, "reply_markup": json.dumps(reply_markup)}
    url = BASE_URL + "/sendMessage"    
    requests.post(url, payload)

def sendTelegramMessageWithRating(text,chat_id):
    inline_keyboard = [[]]
    for rating in RATING_SYMBOLS:
        inline_keyboard[0].append({'text':RATING_SYMBOLS[rating],'callback_data':rating})
    print(inline_keyboard)
    payload = {"text": str(text).encode("utf8"), "chat_id": chat_id, "reply_markup":json.dumps({"inline_keyboard":inline_keyboard})}
    url = BASE_URL + "/sendMessage"    
    requests.post(url, payload)

def sendSignUpMessage(chat_id):
    text = "Hi!\nI haven't seen you before. Check out https://git.io/vxEeb for more information. What do you want to do?"      
    keyboard = []
    for message in SIGN_UP_STRINGS:
        keyboard.append([{"text":message}])
    reply_markup = {"keyboard":keyboard,"one_time_keyboard":True}
    payload = {"text": text.encode("utf8"), "chat_id": chat_id, "reply_markup": json.dumps(reply_markup)}
    url = BASE_URL + "/sendMessage"
    requests.post(url, payload)

def publishQuestionToSns(chat_id,question,arn):
    message = json.dumps({'question':question,'chat_id':chat_id})
    response = sns.publish(TopicArn=arn, Message=message)
    return response

def updateConversations(chat_id,conversations):
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    table.update_item(
        Key={
            'id': int(chat_id)
        },
        UpdateExpression="set conversations = :c, updated_at = :u",
        ExpressionAttributeValues={
            ':c': conversations,
            ':u': TIMESTAMP
        },
        ReturnValues="UPDATED_NEW"
    )

def answerTelegramCallbackQuery(callback_query_id):
    payload = {
        "text":"Rating received!",
        "callback_query_id": callback_query_id}
    url = BASE_URL + "/answerCallbackQuery"
    requests.post(url, payload)

def removeInlineKeyboard(chat_id,message_id):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "reply_markup":json.dumps({"inline_keyboard":[[]]})}
    url = BASE_URL + "/editMessageReplyMarkup"
    requests.post(url, payload)

