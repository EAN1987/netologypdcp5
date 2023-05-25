from vk_api.longpoll import VkEventType, VkLongPoll
from vk_api.bot_longpoll import VkBotEventType, VkBotLongPoll

from bot import *
from db import *
from config import *

import configparser
import time
import logging
from threading import Thread
from datetime import datetime
from time import sleep


logging.basicConfig(level=logging.INFO)

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8-sig')

parameters_sql = config['POSTGRESQL']
db = Database(parameters_sql)

def main_start():
    for event in bot.longpoll.listen():
        
        if event.type == VkBotEventType.MESSAGE_NEW:
            user_id = event.message.from_id
            request = event.message.text.lower()

            if request == 'начать':
                user_info = bot.get_user_info(user_id)
    
                if not user_info:   
                    bot.send_msg(message = "Похоже ваши данные недоступны для нас, вы можете вручную ввести информацию в формате: пол:возраст:город. Пример: мужчина:36:Москва", user_id = user_id)
                    continue

                missing_info = bot.get_missing_info(user_info)
                if missing_info:
                    bot.send_msg(message = f"Следующие поля отсутствуют в вашей странице: {', '.join(missing_info)}. Вы можете вручную ввести информацию в формате: пол:возраст:город. Пример: мужчина:36:Москва", user_id = event.message.from_id)
                    continue

                user = User(user_info)
                if not db.add_user(user):
                    bot.send_msg(message = "Вы уже зарегистрированы", user_id = user.id)

                else:
                    bot.send_msg(message = "Вы зарегистрировались", user_id = user.id)
                
                bot.send_main(user.id)
            
            elif request == 'поиск' or request == 'f':
                user = User(db.get_user(user_id))

                new_offset = bot.looking_for_persons(user, db)
                user.set_offset(new_offset)
                db.update_offset(user)

            elif request == 'просмотренные':
                user = User(db.get_user(event.message.from_id))
                bot.create_seen_list(user, db)

            elif request == 'избранные':
                user = User(db.get_user(event.message.from_id))
                bot.create_fav_list(user, db)

            elif request == 'удалить' or request == 'd':
                db.delete_table_seen_person()  
                db.create_table_seen_person()  
                bot.send_msg(user_id, f' База данных очищена! Введите "Поиск" или F ')

            elif request == 'смотреть' or request == 's':
                user = User(db.get_user(event.message.from_id))
                bot.create_seen_list(user, db)

            else:
                bot.send_msg(user_id, f'Бот готов к поиску, наберите: \n '
                                        f' "Начать или B" - Регистрация \n'
                                        f' "Поиск или F" - Поиск людей. \n'
                                        f' "Удалить или D" - удаляет старую БД и создает новую. \n'
                                        f' "Смотреть или S" - просмотр следующей записи в БД.')
                time.sleep(10)
        
        elif event.type == VkBotEventType.MESSAGE_EVENT:
            user = User(db.get_user(event.obj.peer_id))
            
            if event.object.payload.get('type') in ["RIGHT", "LEFT"] :
                id_search = event.object.payload.get('id_search')
                number = event.object.payload.get('number')
                len = event.object.payload.get('len')
                bot.next_person(user, id_search, number, event.obj.conversation_message_id, len, db)

            elif event.object.payload.get('type') in ["RIGHT_SEEN", "LEFT_SEEN"]:
                number = event.object.payload.get('number')
                bot.next_seen(user, number, event.obj.conversation_message_id, db)

            elif event.object.payload.get('type') in ["RIGHT_FAV", "LEFT_FAV"]:
                number = event.object.payload.get('number')
                bot.next_fav(user, number, event.obj.conversation_message_id, db)

            elif event.object.payload.get('type') in ["IN_FAV"]:
                id_fav = event.object.payload.get('id_fav')
                print(event)
                db.add_fav(user.id, id_fav, event.object.payload.get('description'))
                bot.send_msg(user.id, "Пользователь внесен в список избранных.")

            # elif eve
        
        if event.type in [VkBotEventType.MESSAGE_EVENT, VkBotEventType.MESSAGE_NEW]:
            try:
                db.update_status_and_date(user, datetime.now().hour * 60 + datetime.now().minute)
            except UnboundLocalError:
                continue


def check():
    while True:
        users = db.users_for_check()
        print(users)
        for user in users:
            if datetime.now().hour * 60 + datetime.now().minute - int(user[1]) > 2:
                bot.send_msg(user_id=user[0], message='До свидания!!!')
                db.reset_status(user[0])

        sleep(30)


thread_main = Thread(target=main_start)
thread_checker = Thread(target=check)

thread_main.start()
thread_checker.start()

thread_main.join()
thread_checker.join()

