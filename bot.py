from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.bot_longpoll import VkBotLongPoll
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
import vk_api

import datetime
from config import user_token, group_token
from random import randrange
from pprint import pprint
from db import Database

class User():
    def __init__(self, user_info) -> None:
        self.sex = user_info['sex']
        self.city = user_info['city']
        try:
            self.age = User.bday_to_age(user_info['bdate'])
        
        except:
            self.age = user_info['age']
        
        self.id = user_info['id']
        self.offset = user_info['offset']

    def set_offset(self, new_offset):
        self.offset = new_offset

    def bday_to_age(bday: str) -> int:
        born = datetime.datetime.strptime(bday, "%d.%m.%Y").date()
        today = datetime.date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

class Bot:

    def __init__(self):
        print('Bot was created')
        self.vk_user = vk_api.VkApi(
            token=user_token)  
        self.vk_user_got_api = self.vk_user.get_api()  
        self.vk_group = vk_api.VkApi(token=group_token)  
        self.vk_group_got_api = self.vk_group.get_api() 
        self.longpoll = VkBotLongPoll(
            self.vk_group, 220352108)  

    def send_main(self, user_id):
        settings_start = dict(one_time=False, inline=False)

        keyboard_start = VkKeyboard(**settings_start)
        keyboard_start.add_button(label='Поиск')
        keyboard_start.add_line()
        keyboard_start.add_button(label="Просмотренные")
        keyboard_start.add_line()
        keyboard_start.add_button(label='Избранные')

        self.vk_group.method('messages.send', {'user_id': user_id, "random_id": 
            get_random_id(), 'message': "Основное меню", "keyboard": keyboard_start.get_keyboard()})
   
    def send_msg(self, user_id, message, attachment=None, sticker=None, keyboard=None):
        try:
            self.vk_group_got_api.messages.send(
            user_id=user_id,
            message=message,
            random_id=randrange(10 ** 7),
            attachment=attachment,
            sticker_id=sticker,
            keyboard=keyboard,)

        except Exception as e:
            print(f"Error sending message to user {user_id}: {e}")

    def get_search_info(self, user, offset):
        return self.vk_user.method('users.search',
                                {'count': 10,
                                 'offset': offset,
                                 'age_from': user.age - 5,
                                 'age_to': user.age + 5,
                                 'sex': 1 if user.sex == 2 else 2,
                                 'city': int(user.city),
                                 'status': 6,
                                 'is_closed': False,
                                 'fields': 'bdate, city'
                                }
                            )
    

    def get_user_info(self, user_id):
        info, = self.vk_user.method('users.get',
                            {'user_id': user_id,
                            'fields': 'bdate,sex,city' 
                            })

        try:
            user_info = {'id': user_id, 
                'bdate': info['bdate'],
                'sex': info['sex'],
                'city': info['city']['id'],
                'first_name': info['first_name'],
                'offset': 0}
            
        except KeyError:
            return False
            
        return user_info
    
    def get_missing_info(self, user_info: dict):
        missing_info = []

        if user_info['sex'] == 0:
            missing_info.append('пол')
        if user_info['city'] == '':
            missing_info.append('город')

        return missing_info

    def looking_for_persons(self, user: User, db: Database):
        number = 0

        data = self.get_search_info(user, user.offset)

        if not data['items']:
            user.offset = 0
            data = self.get_search_info(user, user.offset)

        users = data['items']
        count = len(users)

        id_search = get_random_id()
        current_description = '' 

        for found_user in users:

            description = f"{found_user['first_name']} {found_user['last_name']}\n"
            
            try:
                description = description + f"Возраст: {User.bday_to_age(found_user['bdate'])} лет\n"
            except ValueError:
                pass

            try:
                description = description + f"Город: {found_user['city']['title']}\n"
            except KeyError:
                pass

            description = description + f"Ссылка: vk.com/id{found_user['id']}"

            if found_user == users[0]:
                current_description = current_description + description

            db.add_found(found_user['id'], id_search, description)

        current_user = users[number]
    
        settings_start = dict(one_time=False, inline=True)

        keyboard_search = VkKeyboard(**settings_start)
        keyboard_search.add_callback_button(label="Вперед", payload={"type": "RIGHT", "id_search": id_search, "number": number + 1, 'len': count})
        keyboard_search.add_line()
        keyboard_search.add_callback_button(label="Добавить в избранных ", payload={"type": "IN_FAV", "id_fav": current_user['id'], "description": current_description})

        try:
            self.vk_group.method('messages.send', {'user_id': user.id, "random_id": get_random_id(), 'message': current_description, 
            'keyboard': keyboard_search.get_keyboard(), 'attachment': self.photo_of_found_person(current_user)})
        
        except (vk_api.exceptions.ApiError, IndexError):
            self.vk_group.method('messages.send', {'user_id': user.id, "random_id":
            get_random_id(), 'message': "Нет изображения\n" + current_description, 'keyboard': keyboard_search.get_keyboard()})

        db.add_seen(user.id, current_user['id'], current_description)
        
        return user.offset + count
    
    def next_person(self, user: User, id_search, number, message_id, len, db:Database):

        settings_start = dict(one_time=False, inline=True)
        keyboard_search = VkKeyboard(**settings_start)

        if number + 1 == len:
            print('Последний запрос')
            keyboard_search.add_callback_button(label="Назад", payload={"type": "LEFT", "id_search": id_search, "number": number - 1, 'len': len})
            keyboard_search.add_callback_button(label="Новый поиск", payload={"type": "RIGHT", "id_search": id_search, "number": number + 1, 'len': len})
        
        elif number == len:
            print('Переход к след. списку')
            number = 0
            
            new_offset = bot.looking_for_persons(user, db)
            user.set_offset(new_offset)
            db.update_offset(user)
            
            self.vk_group.method('messages.delete', {'peer_id': user.id,
                                                   'cmids': f'{message_id}',
                                                   'delete_for_all': 1
                                                   })

            return

        elif number - 1 < 0:
            keyboard_search.add_callback_button(label="Вперед", payload={"type": "RIGHT", "id_search": id_search, "number": number + 1, 'len': len})

        else:
            keyboard_search.add_callback_button(label="Назад", payload={"type": "LEFT", "id_search": id_search, "number": number - 1, 'len': len})
            keyboard_search.add_callback_button(label="Вперед", payload={"type": "RIGHT", "id_search": id_search, "number": number + 1, 'len': len})

        current_user = db.get_found_user(number, id_search)

        keyboard_search.add_line()
        keyboard_search.add_callback_button(label="Добавить в избранных", payload={"type": "IN_FAV", "id_fav": current_user[1], "description": current_user[2]})

        try:
            self.vk_group.method('messages.edit', {'peer_id': user.id, 
                                                   'conversation_message_id': message_id,
                                                   'message': current_user[2], 
                                                   'keyboard': keyboard_search.get_keyboard(), 
                                                   'attachment': self.photo_of_found_person(current_user[1])})
        
        except (vk_api.exceptions.ApiError, IndexError):
            self.vk_group.method('messages.edit', {'peer_id': user.id, 
                                                   'conversation_message_id': message_id,
                                                   'message': "Нет изображения\n" + current_user[2], 
                                                   'keyboard': keyboard_search.get_keyboard()})

        db.add_seen(user.id, current_user[1], current_user[2])

    def photo_of_found_person(self, user_id, max_photos=3):
        photos = []
        res = self.vk_user_got_api.photos.get(
            owner_id=user_id,
            album_id="profile",  
            extended=1,  
            count=30
        )
        for i in res['items']:
            photo_id = str(i["id"])
            i_likes = i["likes"]
            if i_likes["count"]:
                likes = i_likes["count"]
                photos.append(('photo{}_{}'.format(user_id, photo_id), likes))
        photos = sorted(photos, key=lambda x: x[1], reverse=True)[:max_photos]
        if not photos:
            print('Нет фото')
            return []
        return ','.join([photo[0] for photo in photos])
    
    def create_seen_list(self, user, db: Database):
        number = 0
        seen_list = db.get_seen_list(user.id)

        current_seen = seen_list[number]
        description = current_seen[1]

        settings_start = dict(one_time=False, inline=True)
        keyboard_search = VkKeyboard(**settings_start)

        if number + 1 == len(seen_list):
            keyboard_search.add_callback_button(label="Назад", payload={"type": "LEFT_SEEN", "number": number - 1})

        elif number - 1 < 0:
            keyboard_search.add_callback_button(label="Вперед", payload={"type": "RIGHT_SEEN", "number": number + 1})

        else:
            keyboard_search.add_callback_button(label="Назад", payload={"type": "LEFT_SEEN", "number": number - 1})
            keyboard_search.add_callback_button(label="Вперед", payload={"type": "RIGHT_SEEN", "number": number + 1})

        keyboard_search.add_line()
        keyboard_search.add_callback_button(label="Добавить в избранных", payload={"type": "IN_FAV", "id_fav": current_seen[0], "description": description})

        try:
            self.vk_group.method('messages.send', {'user_id': user.id, 
                                                   "random_id": get_random_id(), 
                                                   'message': description, 
                                                   'keyboard': keyboard_search.get_keyboard(), 
                                                   'attachment': self.photo_of_found_person(current_seen[0])})
        
        except (vk_api.exceptions.ApiError, IndexError):
            self.vk_group.method('messages.send', {'user_id': user.id, "random_id":
            get_random_id(), 'message': "Нет изображения\n" + description, 'keyboard': keyboard_search.get_keyboard()})

    def create_fav_list(self, user: User, db: Database):
        number = 0
        fav_list = db.get_fav_list(user.id)

        current_fav = fav_list[number]
        description = current_fav[1]

        settings_start = dict(one_time=False, inline=True)
        keyboard_search = VkKeyboard(**settings_start)

        if number + 1 == len(fav_list):
            keyboard_search.add_callback_button(label="Назад", payload={"type": "LEFT_FAV", "number": number - 1})

        elif number - 1 < 0:
            keyboard_search.add_callback_button(label="Вперед", payload={"type": "RIGHT_FAV", "number": number + 1})

        else:
            keyboard_search.add_callback_button(label="Назад", payload={"type": "LEFT_FAV", "number": number - 1})
            keyboard_search.add_callback_button(label="Вперед", payload={"type": "RIGHT_FAV", "number": number + 1})

        try:
            self.vk_group.method('messages.send', {'user_id': user.id, 
                                                   "random_id": get_random_id(), 
                                                   'message': description, 
                                                   'keyboard': keyboard_search.get_keyboard(), 
                                                   'attachment': self.photo_of_found_person(current_fav[0])})
        
        except (vk_api.exceptions.ApiError, IndexError):
            self.vk_group.method('messages.send', {'user_id': user.id, "random_id":
            get_random_id(), 'message': "Нет изображения\n" + description, 'keyboard': keyboard_search.get_keyboard()})

    def next_seen(self, user: User, number: int, message_id: int, db: Database):
        seen_list = db.get_seen_list(user.id)

        current_seen = seen_list[number]
        description = current_seen[1]

        settings_start = dict(one_time=False, inline=True)
        keyboard_search = VkKeyboard(**settings_start)

        if number + 1 == len(seen_list):
            keyboard_search.add_callback_button(label="Назад", payload={"type": "LEFT_SEEN", "number": number - 1})

        elif number - 1 < 0:
            keyboard_search.add_callback_button(label="Вперед", payload={"type": "RIGHT_SEEN", "number": number + 1})

        else:
            keyboard_search.add_callback_button(label="Назад", payload={"type": "LEFT_SEEN", "number": number - 1})
            keyboard_search.add_callback_button(label="Вперед", payload={"type": "RIGHT_SEEN", "number": number + 1})

        keyboard_search.add_line()
        keyboard_search.add_callback_button(label="Добавить в избранных", payload={"type": "IN_FAV", "id_seen": current_seen[0], "description": description})

        try:
            self.vk_group.method('messages.edit', {'peer_id': user.id, 
                                                   'conversation_message_id': message_id,
                                                   'message': description, 
                                                   'keyboard': keyboard_search.get_keyboard(), 
                                                   'attachment': self.photo_of_found_person(current_seen[0])})
        
        except (vk_api.exceptions.ApiError, IndexError):
            self.vk_group.method('messages.edit', {'peer_id': user.id, 
                                                   'conversation_message_id': message_id,
                                                   'message': "Нет изображения\n" + description, 
                                                   'keyboard': keyboard_search.get_keyboard()})
            
    def next_fav(self, user: User, number: int, message_id: int, db: Database):
        fav_list = db.get_fav_list(user.id)

        current_fav = fav_list[number]
        description = current_fav[1]

        settings_start = dict(one_time=False, inline=True)
        keyboard_search = VkKeyboard(**settings_start)

        if number + 1 == len(fav_list):
            keyboard_search.add_callback_button(label="Назад", payload={"type": "LEFT_FAV", "number": number - 1})

        elif number - 1 < 0:
            keyboard_search.add_callback_button(label="Вперед", payload={"type": "RIGHT_FAV", "number": number + 1})

        else:
            keyboard_search.add_callback_button(label="Назад", payload={"type": "LEFT_FAV", "number": number - 1})
            keyboard_search.add_callback_button(label="Вперед", payload={"type": "RIGHT_FAV", "number": number + 1})

        try:
            self.vk_group.method('messages.edit', {'peer_id': user.id, 
                                                   'conversation_message_id': message_id,
                                                   'message': description, 
                                                   'keyboard': keyboard_search.get_keyboard(), 
                                                   'attachment': self.photo_of_found_person(current_fav[0])})
        
        except (vk_api.exceptions.ApiError, IndexError):
            self.vk_group.method('messages.edit', {'peer_id': user.id, 
                                                   'conversation_message_id': message_id,
                                                   'message': "Нет изображения\n" + description, 
                                                   'keyboard': keyboard_search.get_keyboard()})

bot = Bot() 
