import telebot
import gspread
import sqlalchemy
import schedule
import json
from time import sleep
from threading import Thread
from datetime import datetime
from models import Users, UserHistory, ApplicationsSell, ApplicationsBuy, Base, Session
from random import randint
from telebot import types

bot = telebot.TeleBot('6250800326:AAEgBf4F8ET3UKDVvajZKI6tlRHEihMWP3Q')
gc = gspread.service_account(filename='exchange-384915-7fec015fbe08.json')
engine = sqlalchemy.create_engine('postgresql+psycopg2://jgsqklcsypqoky:091e08d9f3b9b038b1c8b1662a34b2bed42c52d2fc6baf6f6809f0a63712ca7b@ec2-3-248-141-201.eu-west-1.compute.amazonaws.com:5432/d6l089hfn0o91n')
Session = sqlalchemy.orm.sessionmaker(bind=engine)

banks_sell_calldata = {'monobank_sell': 'Монобанк', 'privatbank_sell': 'ПриватБанк',  'pumb_sell': 'ПУМБ', 'else_sell': 'Другое'}
banks_buy_calldata = {'monobank_buy': 'Монобанк', 'privatbank_buy': 'ПриватБанк',  'pumb_buy': 'ПУМБ', 'else_buy': 'Другое'}
sh = gc.open('Ресурсы для бота')

admins_chat_id = ['5518462737']
users_status_sell = []
user_confirmations_status_sell = []
users_status_buy = []
user_confirmations_status_buy = []

Base.metadata.create_all(engine)

# Старт
@bot.message_handler(commands=['start'])
def start(message):
    text = '*Привет👋* \nЭтот бот сделан нашей командой для закрытия одной простой потребности - регулярный, быстрый и выгодный обмен вашей гривны на USDT и наоборот'
    with Session() as session:
        user_list = session.query(Users).all()
        if message.from_user.id not in [user_id.id for user_id in user_list]:
            new_user = Users(id=message.from_user.id, 
                            username=message.from_user.username, 
                            first_name=message.from_user.first_name, 
                            last_name=message.from_user.last_name
                            )
            user_history = UserHistory(
                id=message.from_user.id 
            )
            session.add(new_user)
            session.add(user_history)
            session.commit()
            bot.send_message(message.chat.id, text, parse_mode='Markdown')
    select_action(message)

# Выбор действия после старта
def select_action(message):
    text_to_user = 'Выберите действие, которое вы хотите выполнить'
    markup = types.InlineKeyboardMarkup(row_width=1)
    sell_btn = types.InlineKeyboardButton('Я хочу купить USDT', callback_data='sell_btn')
    buy_btn = types.InlineKeyboardButton('Я хочу продать USDT', callback_data='buy_btn')
    markup.add(sell_btn, buy_btn)
    bot.send_message(message.chat.id, text_to_user, reply_markup=markup)

# Callbacks

@bot.callback_query_handler(func=lambda call: True)
def action(call):
    markup = types.InlineKeyboardMarkup(row_width=1)
        
    # Продажа USDT    
    if call.data == 'sell_btn':
        ok_btn = types.InlineKeyboardButton('OK', callback_data='ok_sell')
        back_btn = types.InlineKeyboardButton('⬅️Назад', callback_data='back')
        markup.add(ok_btn, back_btn)
        text = f'Курс на данный момент {sh.sheet1.get("B2")[0][0]} за 1 USDT'
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

    elif call.data == 'ok_sell':
        banks = {
            'Монобанк': 'monobank_sell',
            'ПриватБанк': 'privatbank_sell', 
            'ПУМБ': 'pumb_sell', 
            'Другое': 'else_sell', 
                  }
        
        for bank_key, bank_value in banks.items():
                user_bank = types.InlineKeyboardButton(bank_key, callback_data=bank_value)
                markup.add(user_bank)

        back = types.InlineKeyboardButton('⬅️Назад', callback_data='sell_btn')
        markup.add(back)
        text = 'Выберите банк, которым вы хотите воспользоваться'
        bot.edit_message_text(text=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

    elif call.data in ['monobank_sell', 'privatbank_sell', 'pumb_sell', 'else_sell']:
        with Session() as session:
            last_choice = session.query(UserHistory).filter(UserHistory.id==call.message.chat.id).first()
            last_choice.last_bank = call.data
            session.commit()
            markup = types.InlineKeyboardMarkup(row_width=1)
            usdt_btn_choice = types.InlineKeyboardButton('Указать в USDT', callback_data='usdt_choice_sell')
            uah_btn_choice = types.InlineKeyboardButton('Указать в UAH', callback_data='uah_choice_sell')
            markup.add(usdt_btn_choice, uah_btn_choice)
            text = 'Сколько вы хотите купить?'
            bot.edit_message_text(text=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    
    elif call.data == 'usdt_choice_sell':
        with Session() as session:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            last_choice = session.query(UserHistory).filter(UserHistory.id==call.message.chat.id).first()
            if last_choice.last_request_usdt_sell:
                markup.add(types.KeyboardButton(last_choice.last_request_usdt_sell))
            text = 'Укажите сколько USDT вы хотите купить'
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.send_message(call.message.chat.id, text, reply_markup=markup)
            bot.register_next_step_handler(call.message, enter_usdt_sell)

    elif call.data == 'uah_choice_sell':
        with Session() as session:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            last_choice = session.query(UserHistory).filter(UserHistory.id==call.message.chat.id).first()
            if last_choice.last_request_uah_sell:
                markup.add(types.KeyboardButton(last_choice.last_request_uah_sell))
            text = 'Укажите сумму в UAH, на которую хотите купить'
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.send_message(call.message.chat.id, text, reply_markup=markup)
            bot.register_next_step_handler(call.message, enter_uah_sell)
    
    elif call.data == 'confirm_sell':
        markup = types.ReplyKeyboardRemove()
        text = 'Оплатите на реквизиты, что я отправлю ниже и подтвердите после отправки👇'
        bot.delete_message(chat_id=call.message.chat.id,  message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, text, reply_markup=markup)
        requisites_uah(call.message)

    elif call.data == 'confirmed_uah_transfer':
        for user_status in users_status_sell:
            if str(call.message.from_user.id) in user_status:
                user_status_index = users_status_sell.index(user_status)
                users_status_sell.pop(user_status_index)
                break
        with Session() as session:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Отправьте, пожалуйста, квитанцию об оплате')
            id_application = randint(1000000, 9999999)
            applications = session.query(ApplicationsSell).all()
            application_sell_list = [application.id for application in applications]
            if id_application in application_sell_list:
                while id_application not in application_sell_list:
                    id_application = randint(1000000, 9999999)
            user_history = session.query(UserHistory).filter(UserHistory.id==call.message.chat.id).first()
            last_request_uah = user_history.last_request_uah_sell.replace(',', '.')
            exchange_rate = sh.sheet1.get('B2')[0][0].replace(',', '.')
            text = f'''
*Заявка на продажу USDT #{id_application}*
Банк: *{banks_sell_calldata.get(user_history.last_bank)}*
Кошелёк: `{user_history.last_trc20_wallet}`
Курс: *{sh.sheet1.get('B2')[0][0]}*
Сумма в UAH для получения: *{user_history.last_request_uah_sell}*.
Количевство USDT для отправки: *{round(float(last_request_uah) / float(exchange_rate), 2)}*
        '''
            for admin_chat_id in admins_chat_id:
                bot.send_message(admin_chat_id, text, parse_mode='Markdown')
            bot.register_next_step_handler(call.message, handle_uah, id_application=id_application)

    elif call.data[:23] == 'agree_transactions_sell':
        with Session() as session:
            db_id = session.query(ApplicationsSell).filter(ApplicationsSell.id==call.data[23:]).first()
            text = 'Средства были отправлены вам на кошелёк. Обычно они поступают в течении 2-5 минут. Спасибо за выбор нашего сервиса🤙.\nНажмите на /start, чтобы создать новую заявку'
            new_caption = f'''
*Заявка на продажу USDT #{db_id.id}*
Банк: *{db_id.bank}*
Кошелёк: `{db_id.wallet}`
Курс: *{db_id.usdt_rate}*
Сумма в UAH для получения: *{db_id.uah_amount}*
Количевство USDT для отправки: *{db_id.usdt_amount}*
\n\n*ЗАЯВКА ПОДТВЕРЖДЕНА* 
        '''
            with open('order_sell_chat_id.json', 'r') as f:
                data = json.load(f)
                chat_id = data[str(db_id.id)].split()
            for i in range(len(admins_chat_id)):
                bot.edit_message_caption(chat_id=admins_chat_id[i], message_id=chat_id[i], caption=new_caption, parse_mode='Markdown')
            data.pop(str(db_id.id))
            with open('order_sell_chat_id.json', 'w') as delete_id:
                json.dump(data, delete_id)
            bot.send_message(db_id.user_id, text)
            db_id.status = 'approved'
            session.commit()

    elif call.data[:24] == 'reject_transactions_sell':   
        with Session() as session:
            db_id = session.query(ApplicationsSell).filter(ApplicationsSell.id==call.data[24:]).first()
            text = f'Опишите причину отказа заявки №{call.data[24:]}'
            bot.send_message(call.message.chat.id, text)
            new_caption = f'''
*Заявка на продажу USDT #{db_id.id}*
Банк: *{db_id.bank}*
Кошелёк: `{db_id.wallet}`
Курс: *{db_id.usdt_rate}*
Сумма в UAH для получения: *{db_id.uah_amount}*
Количевство USDT для отправки: *{db_id.usdt_amount}*
\n\n*ЗАЯВКА ОТКЛОНЕНА* 
        '''
            with open('order_sell_chat_id.json', 'r') as f:
                data = json.load(f)
                chat_id = data[str(db_id.id)].split()
            for i in range(len(admins_chat_id)):
                bot.edit_message_caption(chat_id=admins_chat_id[i], message_id=chat_id[i], caption=new_caption, parse_mode='Markdown')
            data.pop(str(db_id.id))
            with open('order_sell_chat_id.json', 'w') as delete_id:
                json.dump(data, delete_id)
            bot.register_next_step_handler(call.message, reject_reason_sell, reason=call.data[24:])

    # Покупка USDT

    elif call.data == 'buy_btn':
        ok_btn = types.InlineKeyboardButton('OK', callback_data='ok_buy')
        back_btn = types.InlineKeyboardButton('⬅️Назад', callback_data='back')
        markup.add(ok_btn, back_btn)
        text = f'Курс на данный момент {sh.sheet1.get("A2")[0][0]} за 1 USDT'
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

    elif call.data == 'ok_buy':
        banks = {
            'Монобанк': 'monobank_buy',
            'ПриватБанк': 'privatbank_buy', 
            'ПУМБ': 'pumb_buy', 
            'Другое': 'else_buy', 
                  }

        for bank_key, bank_value in banks.items():
            user_bank = types.InlineKeyboardButton(bank_key, callback_data=bank_value)
            markup.add(user_bank)

        back = types.InlineKeyboardButton('⬅️Назад', callback_data='buy_btn')
        markup.add(back)
        text = 'Выберите банк, на который вы хотите получить UAH'
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)    

    elif call.data in ['monobank_buy', 'privatbank_buy', 'pumb_buy', 'else_buy']:
        with Session() as session:
            last_choice = session.query(UserHistory).filter(UserHistory.id==call.message.chat.id).first()
            last_choice.last_bank = call.data
            session.commit()
            markup = types.InlineKeyboardMarkup(row_width=1)
            usdt_btn_choice = types.InlineKeyboardButton('Указать в USDT', callback_data='usdt_choice_buy')
            uah_btn_choice = types.InlineKeyboardButton('Указать в UAH', callback_data='uah_choice_buy')
            markup.add(usdt_btn_choice, uah_btn_choice)
            text = 'Сколько вы хотите продать USDT?'
            bot.edit_message_text(text=text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    
    elif call.data == 'usdt_choice_buy':
        with Session() as session:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            last_choice = session.query(UserHistory).filter(UserHistory.id==call.message.chat.id).first()
            if last_choice.last_request_usdt_buy:
                markup.add(types.KeyboardButton(last_choice.last_request_usdt_buy))
            text = 'Укажите сколько USDT вы хотите продать'
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.send_message(call.message.chat.id, text, reply_markup=markup)
            bot.register_next_step_handler(call.message, enter_usdt_buy)

    elif call.data == 'uah_choice_buy':
        with Session() as session:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            last_choice = session.query(UserHistory).filter(UserHistory.id==call.message.chat.id).first()
            if last_choice.last_request_uah_buy:
                markup.add(types.KeyboardButton(last_choice.last_request_uah_buy))
            text = 'Укажите на какую сумму UAH вы хотите продать USDT'
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.send_message(call.message.chat.id, text, reply_markup=markup)
            bot.register_next_step_handler(call.message, enter_uah_buy)

    elif call.data == 'confirm_buy':
        markup = types.ReplyKeyboardRemove()
        text = 'Оплатите пожалуйста USDT TRC20 на адрес, что я отправлю ниже и подтвердите после отправки👇'
        bot.delete_message(chat_id=call.message.chat.id,  message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, text, reply_markup=markup)
        requisites_usdt(call.message)

    elif call.data == 'confirmed_usdt_transfer':
        for user_status in users_status_buy:
            if str(call.message.from_user.id) in user_status:
                user_status_index = users_status_buy.index(user_status)
                users_status_buy.pop(user_status_index)
                break
        with Session() as session:
            text = 'Отправьте TXid сделки'
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text)
            id_application = randint(1000000, 9999999)
            applications = session.query(ApplicationsBuy).all()
            application_buy_list = [application.id for application in applications]
            if id_application in application_buy_list:
                while id_application not in application_buy_list:
                    id_application = randint(1000000, 9999999)
            user_history = session.query(UserHistory).filter(UserHistory.id==call.message.chat.id).first()
            last_request_usdt = user_history.last_request_usdt_buy.replace(',', '.')
            exchange_rate = sh.sheet1.get('A2')[0][0].replace(',', '.')
            text = f'''
*Заявка на покупку USDT #{id_application}*
Банк: *{banks_buy_calldata.get(user_history.last_bank)}*
Счёт получателя: `{user_history.last_card}`
Курс: *{sh.sheet1.get('A2')[0][0]}*
Количевство для получения в USDT: *{last_request_usdt}*
Итоговая сумма для отправки в UAH: *{round(float(exchange_rate) * float(last_request_usdt), 2)}*
        '''
            for admin_chat_id in admins_chat_id:
                bot.send_message(admin_chat_id,  text, parse_mode='Markdown')
            bot.register_next_step_handler(call.message, handle_txid, id_application=id_application)

    elif call.data[:22] == 'agree_transactions_buy':
        with Session() as session:
            db_id = session.query(ApplicationsBuy).filter(ApplicationsBuy.id==call.data[22:]).first()
            text = 'Средства были отправлены вам на кошелёк. Обычно они поступают в течении 2-5 минут. Спасибо за выбор нашего сервиса🤙.\nНажмите на /start, чтобы создать новую заявку'
            new_text = f'''
*Заявка на покупку USDT #{db_id.id}*
Банк: *{db_id.bank}*
Кошелёк: `{db_id.credit_card}`
Курс: *{db_id.usdt_rate}*
Сумма в UAH для получения: *{db_id.usdt_amount}*
Количевство USDT для отправки: *{db_id.uah_summa}*
TXid сделки: *{db_id.txid}*
\n\n*ЗАЯВКА ПОДТВЕРЖДЕНА* 
        '''
            with open('order_buy_chat_id.json', 'r') as f:
                data = json.load(f)
                chat_id = data[str(db_id.id)].split()
            for i in range(len(admins_chat_id)):
                bot.edit_message_text(chat_id=admins_chat_id[i], message_id=chat_id[i], text=new_text, parse_mode='Markdown')
            data.pop(str(db_id.id))
            with open('order_buy_chat_id.json', 'w') as delete_id:
                json.dump(data, delete_id)
            bot.send_message(db_id.user_id, text)
            db_id.status = 'approved'
            session.commit()

    elif call.data[:23] == 'reject_transactions_buy':
        with Session() as session:
            db_id = session.query(ApplicationsBuy).filter(ApplicationsBuy.id==call.data[23:]).first()
            text = f'Опишите причину отказа заявки №{call.data[23:]}'
            new_text = f'''
*Заявка на покупку USDT #{db_id.id}*
Банк: *{db_id.bank}*
Кошелёк: `{db_id.credit_card}`
Курс: *{db_id.usdt_rate}*
Сумма в UAH для получения: *{db_id.usdt_amount}*
Количевство USDT для отправки: *{db_id.uah_summa}*
TXid сделки: *{db_id.txid}*
\n\n*ЗАЯВКА ОТКЛОНЕНА* 
        '''
            with open('order_buy_chat_id.json', 'r') as f:
                data = json.load(f)
                chat_id = data[str(db_id.id)].split()
            for i in range(len(admins_chat_id)):
                bot.edit_message_text(chat_id=admins_chat_id[i], message_id=chat_id[i], text=new_text, parse_mode='Markdown')
            data.pop(str(db_id.id))
            with open('order_buy_chat_id.json', 'w') as delete_id:
                json.dump(data, delete_id)
            bot.send_message(call.message.chat.id, text)
            bot.register_next_step_handler(call.message, reject_reason_buy, reason=call.data[23:])

    # Callback возвращающий в старт
    elif call.data == 'back':
        bot.delete_message(call.message.chat.id, call.message.message_id)
        select_action(call.message)

# Админка

@bot.message_handler(commands=['admin'])
def auth_admin(message):
    if str(message.chat.id) not in [message_chat_id for message_chat_id in admins_chat_id]:
        text = 'Введите, пожалуйста, пароль от админ панели'
        bot.send_message(message.chat.id, text)
        bot.register_next_step_handler(message, admin_panel)
    else:
        bot.send_message(message.chat.id, 'Вы уже авторизованы')


def admin_panel(message):
    if message.text.replace(' ', '') == '123':
        admins_chat_id.append(str(message.chat.id))
        bot.send_message(message.chat.id, 'Вы успешно ввели пароль')
    else:
        text = 'Пароль является неправильным, введите команду /admin ещё раз, если хотите повторить попытку'
        bot.send_message(message.chat.id, text)


def reject_reason_sell(message, reason):
    with Session() as session:
        applications = session.query(ApplicationsSell).filter(ApplicationsSell.id==reason).first()
        text = f'К сожалению что-то пошло не так. Комментарий от админа👉: <b>{message.text}</b>. Свяжитесь с @manager_ex4 если у вас возникли дополнительные вопросы. Спасибо за выбор нашего сервиса🤙\nНажмите на /start, чтобы создать новую заявку'
        bot.send_message(applications.user_id, text, parse_mode='html')
        session.delete(applications)
        session.commit()


def reject_reason_buy(message, reason):
    with Session() as session:
        applications = session.query(ApplicationsBuy).filter(ApplicationsBuy.id==reason).first()
        text = f'К сожалению что-то пошло не так. Комментарий от админа👉: <b>{message.text}</b>. Свяжитесь с @manager_ex4 если у вас возникли дополнительные вопросы. Спасибо за выбор нашего сервиса🤙\nНажмите на /start, чтобы создать новую заявку'
        bot.send_message(applications.user_id, text, parse_mode='html')
        session.delete(applications)
        session.commit()

# Покупка USDT

def enter_usdt_sell(message):
    with Session() as session:
        if ' ' not in message.text:
            edited_text = message.text.replace(',', '.')
            text = message.text.replace(',', '.')
            if message.text.isdigit() or edited_text.count('.') == 1 and all(c.isdigit() for c in edited_text.replace('.', '', 1)):
                min_usdt = 100
                if float(edited_text) >= min_usdt:
                    user_history = session.query(UserHistory).filter(UserHistory.id==message.chat.id).first()
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                    exchange_rate = sh.sheet1.get('B2')[0][0].replace(',', '.')
                    if user_history.last_trc20_wallet:
                        markup.add(types.KeyboardButton(user_history.last_trc20_wallet))
                    text = 'Укажите, пожалуйста, адрес USDT TRC20, на который мы должны будем отправить средства.'
                    bot.send_message(message.chat.id, text, reply_markup=markup)
                    bot.register_next_step_handler(message, send_request_confirmation_sell)
                    user_history.last_request_uah_sell = round(float(exchange_rate) * float(edited_text), 2)
                    user_history.last_request_usdt_sell = edited_text
                    session.commit()
                else:
                    text =  'Минимальная сумма для покупки 100 USDT'
                    bot.send_message(message.chat.id, text)
                    bot.register_next_step_handler(message, enter_usdt_sell)
            elif message.text == '/start':
                markup = types.ReplyKeyboardRemove()
                bot.send_message(message.chat.id, 'Возвращаем...', reply_markup=markup)
                start(message)
                return
            else:
                bot.send_message(message.chat.id, 'Напишите сумму ещё раз')
                bot.register_next_step_handler(message, enter_usdt_sell)
        else:
            text = 'Введите сумму USDT корректно'
            bot.send_message(message.chat.id, text)
            bot.register_next_step_handler(message, enter_usdt_sell)


def enter_uah_sell(message):
    with Session() as session:
        if ' ' not in message.text:
            user_history = session.query(UserHistory).filter(UserHistory.id==message.chat.id).first()
            edited_text = message.text.replace(',', '.')
            exchange_rate = sh.sheet1.get('B2')[0][0].replace(',', '.')
            if message.text.isdigit() or edited_text.count('.') == 1 and all(c.isdigit() for c in edited_text.replace('.', '', 1)):
                min_request = 100
                min_summa = round(min_request * float(exchange_rate), 2)
                if float(edited_text) >= min_summa:
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                    if user_history.last_trc20_wallet:
                        markup.add(types.KeyboardButton(user_history.last_trc20_wallet))
                    text = 'Укажите, пожалуйста, адрес USDT TRC20, на который мы должны будем отправить средства.'
                    bot.send_message(message.chat.id, text, reply_markup=markup)
                    bot.register_next_step_handler(message, send_request_confirmation_sell)
                    user_history.last_request_usdt_sell = round(float(edited_text) / float(exchange_rate), 2)
                    user_history.last_request_uah_sell = edited_text
                    session.commit()
                else:
                    text = f'Минимум для покупки 100 USDT ({min_summa}грн)'
                    bot.send_message(message.chat.id, text)
                    bot.register_next_step_handler(message, enter_uah_sell)
            elif message.text == '/start':
                markup = types.ReplyKeyboardRemove()
                bot.send_message(message.chat.id, 'Возвращаем...', reply_markup=markup)
                start(message)
                return
            else:
                bot.send_message(message.chat.id, 'Напишите сумму ещё раз')
                bot.register_next_step_handler(message, enter_uah_sell)
        else:
            text = 'Введите сумму UAH корректно'
            bot.send_message(message.chat.id, text)
            bot.register_next_step_handler(message, enter_uah_sell)


def send_request_confirmation_sell(message):
    if message.text == '/start':
        markup = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, 'Возвращаем...', reply_markup=markup)
        start(message)
        return
    with Session() as session:
        user_history = session.query(UserHistory).filter(UserHistory.id==message.chat.id).first()
        user_history.last_trc20_wallet = message.text
        session.commit()
        exchange_rate = sh.sheet1.get('B2')[0][0].replace(',', '.')
        last_request_usdt = user_history.last_request_uah_sell
        uah_summa = user_history.last_request_usdt_sell
        markup = types.InlineKeyboardMarkup(row_width=1)
        confirm = types.InlineKeyboardButton('OK', callback_data='confirm_sell')
        cancel = types.InlineKeyboardButton('Отменить', callback_data='back')
        markup.add(confirm, cancel)
        confirmation_text = f'''
Подтвердите вашу заявку
Банк: {banks_sell_calldata.get(user_history.last_bank)}
Кошелёк: {user_history.last_trc20_wallet}
Курс: {exchange_rate}
Сумма в UAH для отправки: {last_request_usdt}
Количевство USDT для получения: {uah_summa}
Через 10 минут подтверждение заявки пропадёт и вы начнёте сначала.
'''
        f = bot.send_message(message.chat.id, confirmation_text, reply_markup=markup)
        user_confirmations_status_sell.append({str(f.from_user.id): False})

        def deleting_confirmation_status_sell(message):
            sleep(30)
            for user_status in user_confirmations_status_sell:
                if str(message.from_user.id) in user_status:
                    markup = types.ReplyKeyboardRemove()
                    text = 'Время ожидание истекло'
                    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                    bot.send_message(chat_id=message.chat.id, text=text, reply_markup=markup)
                    select_action(message)
                    user_status_index = user_confirmations_status_sell.index(user_status)
                    user_confirmations_status_sell.pop(user_status_index)
                    break

        thr = Thread(target=deleting_confirmation_status_sell, args=(f, ))
        thr.start()


def requisites_uah(message):
    for user_status in user_confirmations_status_sell:
        if str(message.from_user.id) in user_status:
            user_status_index = user_confirmations_status_sell.index(user_status)
            user_confirmations_status_sell.pop(user_status_index)
            break
    with Session() as session:
        user_history = session.query(UserHistory).filter(UserHistory.id==message.chat.id).first()
        wallets = {'privatbank_sell': "B1",'monobank_sell': "B2", 'pumb_sell': "B3",'else_sell': "B4"}
        markup = types.InlineKeyboardMarkup(row_width=1)
        confirmed_transfer = types.InlineKeyboardButton('Я отправил деньги', callback_data='confirmed_uah_transfer')
        markup.add(confirmed_transfer)
        text = f'Номер карты: `{sh.get_worksheet(2).get(wallets.get(user_history.last_bank))[0][0]}`\nСумма: {user_history.last_request_uah_sell}'
        f = bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
        users_status_sell.append({str(f.from_user.id): False})

        def deleting_status_sell(message):
            sleep(30)
            for user_status in users_status_sell:
                if str(message.from_user.id) in user_status:
                    markup = types.ReplyKeyboardRemove()
                    text = 'Время ожидание истекло'
                    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                    bot.send_message(message.chat.id, text, reply_markup=markup)
                    select_action(message)
                    user_status_index = users_status_sell.index(user_status)
                    users_status_sell.pop(user_status_index)
                    break

        thr = Thread(target=deleting_status_sell, args=(f, ))
        thr.start()


def handle_uah(message, id_application):
    if message.photo:
        with Session() as session:
            user_history = session.query(UserHistory).filter(UserHistory.id==message.chat.id).first()
            exchange_rate = sh.sheet1.get('B2')[0][0].replace(',', '.')
            last_request_uah = user_history.last_request_uah_sell.replace(',', '.')
            create_application = ApplicationsSell(
                id=id_application,
                user_id=message.chat.id,
                bank=banks_sell_calldata.get(user_history.last_bank),
                usdt_rate=exchange_rate,
                wallet=user_history.last_trc20_wallet,
                uah_amount=last_request_uah,
                usdt_amount=round(float(last_request_uah) / float(exchange_rate), 2),
                data_created=datetime.now().strftime('%d.%m.%Y'),
                time_created = datetime.now().strftime('%H:%M:%S'),
                status='in process'
            )
            session.add(create_application)
            session.commit()
            text = f'''
*Заявка на продажу USDT #{create_application.id}*
Банк: *{create_application.bank}*
Кошелёк: `{create_application.wallet}`
Курс: *{create_application.usdt_rate}*
Количевство для получения USDT: *{create_application.uah_amount}*
Итоговая сумма для отправки в UAH: *{create_application.usdt_amount}*
        '''
        markup = types.InlineKeyboardMarkup(row_width=1)
        agree_transactions = types.InlineKeyboardButton('Подтверждаю обмен', callback_data=f'agree_transactions_sell{create_application.id}')
        reject_transactions = types.InlineKeyboardButton('Отклоняю обмен', callback_data=f'reject_transactions_sell{create_application.id}')
        markup.add(agree_transactions, reject_transactions)
        admins_id = ''
        for admin_chat_id in admins_chat_id:
            admin_message = bot.send_photo(admin_chat_id, message.photo[-1].file_id, caption=text, reply_markup=markup, parse_mode='Markdown')
            admins_id += f'{admin_message.message_id} '
        order_chat_ids = {str(create_application.id): admins_id}
        with open('order_sell_chat_id.json', 'r') as f:
            parse_file = json.loads(f.read())
            parse_file.update(order_chat_ids)
            with open('order_sell_chat_id.json', 'w') as f:
                json.dump(parse_file, f)
        text = f'Пожалуйста, ожидайте подтверждения транзакции. ID этой сделки: #{create_application.id}.\nОбычно подтверждение заявки происходит в течении 15 минут.'
        bot.send_message(message.chat.id, text)
    elif message.text == '/start':
        markup = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, 'Возваращаем...', reply_markup=markup)
        select_action(message)
        return
    else:
        bot.send_message(message.chat.id, 'Пожалуйста, отправьте скриншот квитанции об переводе средств', parse_mode='Markdown')
        bot.register_next_step_handler(message, handle_uah, id_application=id_application)

# Продажа USDT

def enter_usdt_buy(message):
    with Session() as session:
        if ' ' not in message.text:
            edited_text = message.text.replace(',', '.')
            if message.text.isdigit() or edited_text.count('.') == 1 and all(c.isdigit() for c in edited_text.replace('.', '', 1)):
                min_usdt = 30
                if float(edited_text) >= min_usdt:
                    user_history = session.query(UserHistory).filter(UserHistory.id==message.chat.id).first()
                    exchange_rate = sh.sheet1.get('A2')[0][0].replace(',', '.')
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                    if user_history.last_card:
                        markup.add(types.KeyboardButton(user_history.last_card))
                    text = 'Введите пожалуйста номер карты, на который мы отправим UAH.'
                    bot.send_message(message.chat.id, text, reply_markup=markup)
                    bot.register_next_step_handler(message, send_request_confirmation_buy)
                    user_history.last_request_uah_buy = round(float(exchange_rate) * float(edited_text), 2)
                    user_history.last_request_usdt_buy = edited_text
                    session.commit()
                else:
                    text =  'Минимальная сумма продажи 30 USDT'
                    bot.send_message(message.chat.id, text)
                    bot.register_next_step_handler(message, enter_usdt_buy)
            elif message.text == '/start':
                markup = types.ReplyKeyboardRemove()
                bot.send_message(message.chat.id, 'Возвращаем...', reply_markup=markup)
                start(message)
                return
            else:
                bot.send_message(message.chat.id, 'Напишите сумму ещё раз')
                bot.register_next_step_handler(message, enter_usdt_buy)
        else:
            text = 'Введите сумму USDT корректно'
            bot.send_message(message.chat.id, text)
            bot.register_next_step_handler(message, enter_usdt_buy)


def enter_uah_buy(message):
    with Session() as session:
        if ' ' not in message.text:
            user_history = session.query(UserHistory).filter(UserHistory.id==message.chat.id).first()
            edited_text = message.text.replace(',', '.')
            exchange_rate = sh.sheet1.get('A2')[0][0].replace(',', '.')
            if message.text.isdigit() or edited_text.count('.') == 1 and all(c.isdigit() for c in edited_text.replace('.', '', 1)):
                min_request = 30
                min_summa = round(min_request * float(exchange_rate), 2)
                if float(edited_text) >= min_summa:
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                    if user_history.last_card:
                        markup.add(types.KeyboardButton(user_history.last_card))
                    text = 'Введите пожалуйста номер карты, на который мы отправим UAH.'
                    bot.send_message(message.chat.id, text, reply_markup=markup)
                    bot.register_next_step_handler(message, send_request_confirmation_buy)
                    user_history.last_request_usdt_buy = round(float(edited_text) / float(exchange_rate), 2)
                    user_history.last_request_uah_buy = edited_text
                    session.commit()
                else:
                    text = f'Минимум для продажи 30 USDT ({min_summa}грн)'
                    bot.send_message(message.chat.id, text)
                    bot.register_next_step_handler(message, enter_uah_buy)
            elif message.text == '/start':
                markup = types.ReplyKeyboardRemove()
                bot.send_message(message.chat.id, 'Возвращаем...', reply_markup=markup)
                start(message)
                return
            else:
                bot.send_message(message.chat.id, 'Напишите сумму ещё раз')
                bot.register_next_step_handler(message, enter_uah_buy)
        else:
            text = 'Введите сумму UAH корректно'
            bot.send_message(message.chat.id, text)
            bot.register_next_step_handler(message, enter_uah_buy)


def send_request_confirmation_buy(message):
    message_text = message.text.replace(' ', '')
    with Session() as session:
        if len(message_text) == 16:
            if message_text.isdigit():
                user_history = session.query(UserHistory).filter(UserHistory.id==message.chat.id).first()
                user_history.last_card = message.text
                session.commit()
                exchange_rate = sh.sheet1.get('A2')[0][0].replace(',', '.')
                last_request_usdt = user_history.last_request_usdt_buy
                uah_summa = user_history.last_request_uah_buy
                markup = types.InlineKeyboardMarkup(row_width=1)
                confirm = types.InlineKeyboardButton('OK', callback_data='confirm_buy')
                cancel = types.InlineKeyboardButton('Отменить', callback_data='back')
                markup.add(confirm, cancel)
                confirmation_text = f'''
Подтвердите вашу заявку
Банк: {banks_buy_calldata.get(user_history.last_bank)}
Реквезиты получателя: {user_history.last_card}
Курс: {exchange_rate}
Количевство USDT для отправки: {last_request_usdt}
Сумма в UAH для получения: {uah_summa}
Через 10 минут подтверждение заявки пропадёт и вы начнёте сначала.'''
                f = bot.send_message(message.chat.id, confirmation_text, reply_markup=markup)
                user_confirmations_status_buy.append({str(f.from_user.id): False})

                def deleting_confirmation_status_buy(message):
                    sleep(30)
                    for user_status in user_confirmations_status_buy:
                        if str(message.from_user.id) in user_status:
                            markup = types.ReplyKeyboardRemove()
                            text = 'Время ожидание истекло'
                            bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                            bot.send_message(message.chat.id, text, reply_markup=markup)
                            select_action(message)
                            user_status_index = user_confirmations_status_buy.index(user_status)
                            user_confirmations_status_buy.pop(user_status_index)
                            break

                thr = Thread(target=deleting_confirmation_status_buy, args=(f, ))
                thr.start()
            else:
                bot.send_message(message.chat.id, 'Уберите буквы')
                bot.register_next_step_handler(message, send_request_confirmation_buy)
        elif message.text == '/start':
                markup = types.ReplyKeyboardRemove()
                bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                bot.send_message(message.chat.id, 'Возвращаем...', reply_markup=markup)
                start(message)
                return
        else:
            bot.send_message(message.chat.id, 'Вы неправильно ввели свою карту, пожалуйста, введите свою карту ещё раз')
            bot.register_next_step_handler(message, send_request_confirmation_buy)


def requisites_usdt(message):
    for user_status in user_confirmations_status_buy:
        if str(message.from_user.id) in user_status:
            user_status_index = user_confirmations_status_buy.index(user_status)
            user_confirmations_status_buy.pop(user_status_index)
            break
    with Session() as session:
        user_history = session.query(UserHistory).filter(UserHistory.id==message.chat.id).first()
        markup = types.InlineKeyboardMarkup(row_width=1)
        confirmed_transfer = types.InlineKeyboardButton('Я отправил деньги', callback_data='confirmed_usdt_transfer')
        markup.add(confirmed_transfer)
        text = f'Адресс USDT кошелька: `{sh.get_worksheet(1).get("B1")[0][0]}`\nСумма: {user_history.last_request_usdt_buy}'
        f = bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
        users_status_buy.append({str(f.from_user.id): False})

        def deleting_status_buy(message):
            sleep(30)
            for user_status in users_status_buy:
                if str(message.from_user.id) in user_status:
                    markup = types.ReplyKeyboardRemove()
                    text = 'Время ожидание истекло'
                    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                    bot.send_message(message.chat.id, text, reply_markup=markup)
                    select_action(message)
                    user_status_index = users_status_buy.index(user_status)
                    users_status_buy.pop(user_status_index)
                    break
            
        thr = Thread(target=deleting_status_buy, args=(f, ))
        thr.start()


def handle_txid(message, id_application):
    with Session() as session:
        if message.text == '/start':
            markup = types.ReplyKeyboardRemove()
            bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            select_action(message)
            return
        user_history = session.query(UserHistory).filter(UserHistory.id==message.chat.id).first()
        exchange_rate = sh.sheet1.get('A2')[0][0].replace(',', '.')
        last_request_usdt = user_history.last_request_usdt_buy.replace(',', '.')
        create_application = ApplicationsBuy(
            id=id_application,
            user_id=message.chat.id,
            txid=message.text,
            bank=banks_buy_calldata.get(user_history.last_bank),
            usdt_rate=exchange_rate,
            credit_card=user_history.last_card,
            usdt_amount=last_request_usdt,
            uah_summa=round(float(exchange_rate) * float(last_request_usdt), 2),
            data_created=datetime.now().strftime('%d.%m.%Y'),
            time_created = datetime.now().strftime('%H:%M:%S'),
            status='in process'
        )
        session.add(create_application)
        session.commit()
        text = f'''
*Заявка на покупку USDT #{create_application.id}*
Банк: *{create_application.bank}*
Счёт получателя: `{create_application.credit_card}`
Курс: *{create_application.usdt_rate}*
Количевство для получения в USDT: *{create_application.usdt_amount}*
Итоговая сумма для отправки в UAH: *{create_application.uah_summa}*
TXid сделки: *{create_application.txid}*
    '''
        markup = types.InlineKeyboardMarkup(row_width=1)
        agree_transactions = types.InlineKeyboardButton('Подтверждаю обмен', callback_data=f'agree_transactions_buy{create_application.id}')
        reject_transactions = types.InlineKeyboardButton('Отклоняю обмен', callback_data=f'reject_transactions_buy{create_application.id}')
        markup.add(agree_transactions, reject_transactions)
        admins_id = ''
        for admin_chat_id in admins_chat_id:
            a = bot.send_message(admin_chat_id, text, reply_markup=markup, parse_mode='Markdown')
            admins_id += f'{a.message_id} '
        order_chat_ids = {str(create_application.id): admins_id}
        with open('order_buy_chat_id.json', 'r') as f:
            parse_file = json.loads(f.read())
            parse_file.update(order_chat_ids)
            with open('order_buy_chat_id.json', 'w') as f:
                json.dump(parse_file, f)
        text = f'Пожалуйста, ожидайте подтверждения транзакции. Обычно подтверждение заявки происходит в течении 15 минут. ID этой сделки: #{create_application.id}'
        bot.send_message(message.chat.id, text)

#Функция собирающая данные за день в гугл таблицу
def data_upload():
    # Фильтрация всех заявок на продажу
    with Session() as session:
        todays_sell_applications = session.query(ApplicationsSell).filter(
            ApplicationsSell.data_created==datetime.now().strftime('%d.%m.%Y'),
            ApplicationsSell.status=='approved').all()

        worksheet = sh.get_worksheet(3)
        column_a = worksheet.col_values(1)
        clear_sheet = len(column_a) + 1

        # Выгрузка в таблицу всех заявок на покупку USDT
        data = []
        for application in todays_sell_applications:
            row_data = [f'{application.id}', f'{application.bank}', f'{application.wallet}',
                        f'{application.data_created}', f'{application.time_created}',
                        f'{application.usdt_rate}', 'продажа']
            data.append(row_data)

        num_rows = len(data)
        cell_range = f'A{clear_sheet}:G{clear_sheet + num_rows - 1}'

        worksheet.update(cell_range, data)

        # Фильтрация всех заявок на покупку
        todays_buy_applications = session.query(ApplicationsBuy).filter(
            ApplicationsBuy.data_created==datetime.now().strftime('%d.%m.%Y'),
            ApplicationsBuy.status=='approved').all()

        # Выгрузка в таблицу всех заявок на продажу USDT
        column_a = worksheet.col_values(1)
        clear_sheet = len(column_a) + 1
        data = []
        for application in todays_buy_applications:
            row_data = [f'{application.id}', f'{application.bank}', f'{application.credit_card}',
                        f'{application.data_created}', f'{application.time_created}',
                        f'{application.usdt_rate}', 'покупка']
            data.append(row_data)

        num_rows = len(data)
        cell_range = f'A{clear_sheet}:G{clear_sheet + num_rows - 1}'

        worksheet.update(cell_range, data)
        
# Эта функция активирует data_upload в 23:59 каждый день
schedule.every().day.at("23:59:00").do(data_upload)

# Эта функция запускает цикл запускающий отправки данных по расписанию каждый день
def run_schedule():
    while True:
        schedule.run_pending()
        sleep(1)

# Запуск второго потока
second_flow = Thread(target=run_schedule)
second_flow.start()

# Запуск бота
if __name__ == '__main__':
    bot.polling(none_stop=True)