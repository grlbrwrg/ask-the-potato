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


def main(event, context):
    try:
        data = json.loads(event["body"])
        message = str(data["message"]["text"])
        chat_id = data["message"]["chat"]["id"]
        first_name = data["message"]["chat"]["first_name"]
        table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
        timestamp = int(time.time() * 1000)
            
        # fetch chat_id from the database
        result = table.get_item(Key={'id':int(chat_id)})
        print(result)
        
        # if no Item in table, respond with sign-up message
        if not 'Item' in result:
            
            # create user if response matches sign up strings
            if message in SIGN_UP_STRINGS:
                
                item = {
                    'id': int(chat_id),
                    'updated_at': timestamp,
                    'job':SIGN_UP_STRINGS[message],
                    'created_at': timestamp,
                    }
                table.put_item(Item=item)
                
                response = "You have signed up to %s questions." % (SIGN_UP_STRINGS[message])
                
                if SIGN_UP_STRINGS[message] == 'answer':
                    dynamoQueue = table.get_item(Key={'id':0})
                    if not 'queue' in dynamoQueue['Item']:
                        queue = []
                    else:
                        queue = dynamoQueue['Item']['queue']
                        
                    queue.append(int(chat_id))
                    dynamoResponse = table.update_item(
                    Key={
                        'id': 0
                    },
                    UpdateExpression="set queue = :q",
                    ExpressionAttributeValues={
                        ':q': queue
                    },
                    ReturnValues="UPDATED_NEW"
                    )
                
                telegramData = {"text": response.encode("utf8"), "chat_id": chat_id}
                
                url = BASE_URL + "/sendMessage"
                r = requests.post(url, telegramData)
                
                return {"statusCode": 200}
            
            response = "Hi!\nI haven't seen you before. Are you looking for help or do you want to help?"
            
            keyboard = []
            for message in SIGN_UP_STRINGS:
                keyboard.append([{"text":message}])
            
            reply_markup = {"keyboard":keyboard,"one_time_keyboard":True}
            
            telegramData = {"text": response.encode("utf8"), "chat_id": chat_id, "reply_markup": json.dumps(reply_markup)}
        #process message when user is already signed up
        else:
            if result['Item']['job'] == 'ask':
                #Add open question to chat_id in DB
                if not 'questions' in result['Item']:
                    questions = []
                else:
                    questions = result['Item']['questions']
                
                question = "%s asks: %s" % (first_name,message)
                questions.append({'question':question})
                
                dynamoResponse = table.update_item(
                    Key={
                        'id': int(chat_id)
                    },
                    UpdateExpression="set questions = :q, updated_at = :u",
                    ExpressionAttributeValues={
                        ':q': questions,
                        ':u': timestamp
                    },
                    ReturnValues="UPDATED_NEW"
                    )
                print(dynamoResponse)
                
                snsMessage = json.dumps({'question':question,'chat_id':chat_id})
                
                snsResponse = sns.publish(TopicArn=QUESTION_ASKED_ARN, Message=snsMessage)
                
                telegramResponse = "I've sent your question to a few people speaking German. Wait a bit until they answer"
                
                telegramData = {"text": telegramResponse.encode("utf8"), "chat_id": chat_id}

            elif result['Item']['job'] == 'answer':
                pass
                #check if reply_to_message is in message object, if no educate user
                # if yes, get original chat id from db and forward message, return success to sender
                telegramResponse = "I can't handle answers yet..."
                telegramData = {"text": telegramResponse.encode("utf8"), "chat_id": chat_id}
            
            

        
        url = BASE_URL + "/sendMessage"
        r = requests.post(url, telegramData)
        print(r.text)

    except Exception as e:
        print(e)
        traceback.print_exc()

    return {"statusCode": 200}