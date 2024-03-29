import logging
import sys
import time
from http import HTTPStatus

import requests
import telegram

from exceptions import OtherHTTPError, HTTPError, MessageError
from config import (
    PRACTICUM_TOKEN,
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID,
    RETRY_PERIOD,
    ENDPOINT,
    HEADERS,
    HOMEWORK_VERDICTS
)


logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    encoding='UTF-8'
)


def check_tokens():
    """Проверяем наличие переменных."""
    if not all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        logging.critical('Отсутствуют обязательные переменные.')
        sys.exit(1)


def send_message(bot, message):
    """Отправляем сообщение о статусе в телеграм."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug('Сообщение отправлено.')
    except telegram.error.TelegramError as e:
        logging.error(
            f'Не удалось отправить сообщение: {str(e)}'
        )
        raise MessageError('Ошибка отправки сообщения в Telegram') from e


def get_api_answer(timestamp):
    """Получаем API с информацией о домашних работах."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            logging.error(f'Bad response: {response.status_code}')
            raise HTTPError('Bad response:', response.status_code)
    except requests.exceptions.HTTPError:
        raise OtherHTTPError(f'Bad response: {response.status_code}')
    except requests.RequestException:
        raise OtherHTTPError('Ошибка связанная с запросом')
    return response.json()


def check_response(response):
    """Проверяем API на соответствие документации."""
    if not isinstance(response, dict):
        logging.error('API response is not a dictionary')
        raise TypeError('API response is not a dictionary')
    if 'current_date' not in response:
        logging.error('current_date is not in a response')
        raise KeyError('current_date is not in a response')
    if not isinstance(response['current_date'], int):
        logging.error('current_date is not an integer')
        raise TypeError('current_date is not a dictionary')
    if 'homeworks' not in response:
        logging.error('homeworks is not in a response')
        raise KeyError('homeworks is not in a response')
    if not isinstance(response['homeworks'], list):
        logging.error('homeworks is not a list')
        raise TypeError('homeworks is not a list')


def parse_status(homework):
    """Обрабатываем API и создаем ответ о статусе."""
    if 'homework_name' not in homework:
        logging.error('Значение ключа homework_name не найдено')
        raise KeyError('Значение ключа homework_name не найдено')
    homework_name = homework['homework_name']
    if 'status' not in homework:
        logging.error('Ключ status не найден')
        raise KeyError('Ключ status не найден')
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        logging.error(f'Неизвестный статус домашней работы: {status}')
        raise ValueError(f'Неизвестный статус домашней работы: {status}')
    verdict = HOMEWORK_VERDICTS.get(status)
    logging.info('Статус работы обновлен')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logging.info('Программа запущена')
    check_tokens()
    timestamp = int(time.time()) - RETRY_PERIOD
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    last_error_message = ''
    while True:
        try:
            response_json = get_api_answer(timestamp)
            check_response(response_json)
            if response_json['homeworks']:
                message = parse_status(response_json['homeworks'][0])
                send_message(bot, message)
                timestamp = response_json['current_date']
            else:
                logging.info('Обновлений статуса не найдено')
        except Exception as error:
            logging.error(f'Ошибка в работе программы: {error}')
            error_message = f'Ошибка в работе программы: {error}'
            if error_message != last_error_message:
                send_message(bot, error_message)
            last_error_message = error_message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.info('Программа остановлена пользователем вручную')
