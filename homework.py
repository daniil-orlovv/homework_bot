import os
import requests
import time
import logging

from typing import Dict, List

import telegram
from telegram import ReplyKeyboardMarkup
from telegram.ext import CommandHandler, Updater, Filters, MessageHandler

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    encoding='UTF-8'
)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    try:
        PRACTICUM_TOKEN = os.environ['PRACTICUM_TOKEN']
        TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
        TELEGRAM_CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
    except KeyError as e:
        logging.critical(f'Переменная {e.args[0]} не найдена.')
        raise SystemExit(1)


def send_message(bot, message):
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    logging.debug('Сообщение о статусе отправлено.')


def get_api_answer(timestamp):
    payload = {'from_date': 0}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f'API request failed: {e}')
        return None
    return response.json()


def check_response(response):
    try:
        assert isinstance(response, dict)
        assert isinstance(response['current_date'], int)
        assert isinstance(response['homeworks'], list)

        for homework in response['homeworks']:
            assert isinstance(homework, dict)
            assert isinstance(homework['date_updated'], str)
            assert isinstance(homework['homework_name'], str)
            assert isinstance(homework['id'], int)
            assert isinstance(homework['lesson_name'], str)
            assert isinstance(homework['reviewer_comment'], str)
            assert isinstance(homework['status'], str)

        logging.info('API response is valid')
    except AssertionError:
        logging.error('API response is not valid')


def parse_status(homework):
    try:
        if 'homeworks' in homework:
            homework_name = homework['homeworks'][0]['homework_name']
            status = homework['homeworks'][0]['status']
            verdict = HOMEWORK_VERDICTS.get(status)
            if status not in HOMEWORK_VERDICTS:
                logging.error(f'Неизвестный статус домашней работы: {verdict}')
            logging.info('Статус работы изменен.')
            return f'Изменился статус проверки работы "{homework_name}". {verdict}'
        else:
            logging.info('Статус работы не изменен.')
    except KeyError as e:
        logging.error(f'Отсутствует ожидаемый ключ в ответе API: {e}')
        return None
    except IndexError:
        logging.error('Пустой список homeworks в ответе API')
        return None


def main():
    """Основная логика работы бота."""
    check_tokens()
    timestamp = int(time.time()) - RETRY_PERIOD

    while True:
        try:
            response_json = get_api_answer(timestamp)
            check_response(response_json)
            bot = telegram.Bot(token=TELEGRAM_TOKEN)
            message = parse_status(response_json)
            send_message(bot, message)
            timestamp = response_json['current_date']
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            print(f'Сбой в работе программы: {error}')


if __name__ == '__main__':
    main()
