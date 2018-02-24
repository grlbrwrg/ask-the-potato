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
BASE_URL = "https://api.telegram.org/bot{}".format(TOKEN)

SIGN_UP_STRINGS = {"I only speak English.":'ask',"Ich spreche Deutsch und kann helfen!":'answer'}

QUESTION_ASKED_ARN = "arn:aws:sns:us-east-1:528227264112:ask-the-potato-question-asked"
TIMESTAMP = int(time.time() * 1000)

def main(event, context):
    try:
        print(event)
        telegramMessage = parseTelegramMessage(json.loads(event["body"]))
        chat_id = telegramMessage['chat_id']
        first_name = telegramMessage['first_name']
        message = telegramMessage['message']
        user = getUserFromDb(chat_id)
        
        if user == {}:
            if message in SIGN_UP_STRINGS:
                job = SIGN_UP_STRINGS[message]
                addUserToDb(chat_id,job)
                if job == 'answer':
                    addAnswererToQueue(chat_id)
                signUpMessage = "You have signed up to %s questions." % (job)
                sendTelegramMessage(signUpMessage,chat_id)
            else:
                sendSignUpMessage(chat_id)
            return {"statusCode": 200}
        elif user['job'] == 'ask':
            question = "%s asks: %s" % (first_name,message)         
            publishQuestionToSns(chat_id,question)
            response = "I've sent your question to a few people speaking German. Wait a bit until they answer"
            sendTelegramMessage(response,chat_id)
        elif user['job'] == 'answer':
            if telegramMessage['reply_to_message_text'] == "":
                response = "To answer a question, tap it and select 'Reply'."
                sendTelegramMessage(response,chat_id)
            else:
                for conversation in user['conversations']:
                    if conversation['question'] == telegramMessage['reply_to_message_text']:
                        answerText = "%s answered: %s" % (first_name,message)
                        sendTelegramMessage(answerText,conversation['asker'])
                        conversation['answer'] = message
                        updateConversations(chat_id,user['conversations'])
                        return {"statusCode": 200}
                    
        else:
            sendSignUpMessage(chat_id)
        return {"statusCode": 200}
    except Exception as e:
        print(e)
        traceback.print_exc()

def parseTelegramMessage(body):
    message = str(body["message"]["text"])
    chat_id = body["message"]["chat"]["id"]
    first_name = body["message"]["chat"]["first_name"]
    if 'reply_to_message' in body["message"]:
        reply_to_message_text = body['message']['reply_to_message']['text']
    else:
        reply_to_message_text = ""

    return({
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

def sendSignUpMessage(chat_id):
    text = "Hi!\nI haven't seen you before. Are you looking for help or do you want to help?"      
    keyboard = []
    for message in SIGN_UP_STRINGS:
        keyboard.append([{"text":message}])
    reply_markup = {"keyboard":keyboard,"one_time_keyboard":True}
    payload = {"text": text.encode("utf8"), "chat_id": chat_id, "reply_markup": json.dumps(reply_markup)}
    url = BASE_URL + "/sendMessage"
    requests.post(url, payload)

def publishQuestionToSns(chat_id,question):
    message = json.dumps({'question':question,'chat_id':chat_id})
    sns.publish(TopicArn=QUESTION_ASKED_ARN, Message=message)

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