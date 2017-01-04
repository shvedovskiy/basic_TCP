"""
	Пример сеанса взаимодействия:

	(C)ar (M)ileage (O)wner (N)ew car (S)top server (Q)uit [c]:
	License: 024 hyr
	License: 024 HYR
	Seats: 2
	Mileage: 97543
	Owner: Jack Lemon
	(C)ar (M)ileage (O)wner (N)ew car (S)top server (Q)uit [c]: m
	License [024 HYR]:
	Mileage [97543]: 103491
	Mileage successfully changed

	В данном случае пользователь запросил информацию о
	конкретном автомобиле и затем обновил величину пробега.
"""
import sys
import socket
import collections
import pickle
import struct
import Console


Address = ['localhost', 9653]  # IP-адрес, номер порта
# кол-во посадочных мест, пробег и владелец:
CarTuple = collections.namedtuple('CarTuple', 'seats mileage owner')


class SocketManager:
	"""
		Сокет-менеджер контекста, готовый к использованию.
	"""
	def __init__(self, address: tuple):
		self.address = address

	def __enter__(self):
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.connect(self.address)
		return self.sock

	def __exit__(self, *ignore):
		self.sock.close()
		# любые исключения не заботят, они продолжат распространение


def handle_request(*items, wait_for_reply=True):
	"""	Реализация сетевых взаимодействий с сервером.

		Запаковка данных->передача размера и версии->передача законвервированных данных.
		Получение размера и версии->получение данных->распаковка ответа.

		socket.socket.sendall() -- отправка всех переданных сокету данных,
		выполняя требуемое кол-во send().
	"""
	# беззнаковое целое с сетевым порядком следования байтов:
	InfoVersion = 1  # версия протокола обмена
	InfoStruct = struct.Struct('!IB')  # байты размера

	# консервация объекта с полученными данными:
	data = pickle.dumps(items, 3)  # версия протокола 3

	try:
		with SocketManager(tuple(Address)) as sock:
			# передача серверу:
			sock.sendall(InfoStruct.pack(len(data), InfoVersion))  # запакованной длины объекта и версии
			sock.sendall(data)  # самого законсервированного объекта
			if not wait_for_reply:
				return

			info = sock.recv(InfoStruct.size)  # блокирующее принятие ответа 6 байтов
			size, version = InfoStruct.unpack(info)  # распаковывание байтов в длину сообщения и версию
			if version > InfoVersion:
				raise ValueError('server is incompatible')

			result = bytearray()
			while True:
				# получение законсерв. объекта блоками до 4000 байтов:
				data = sock.recv(4000)
				if not data:
					break
				result.extend(data)
				if len(result) >= size:  # до передачи заданного кол-ва данных
					break
		return pickle.loads(result)  # распаковка данных и их возврат
	except ValueError as err:
		print(err)
		sys.exit(1)
	except socket.error as err:
		print('{}: is the server running?'.format(err))
		sys.exit(1)


def retrieve_car_details(previous_licence):
	""" Возвращает котреж номера автомобиля и CarTuple -- информацию об автомобиле.

		Данные запрашиваются у сервера на основе полученного номера.
		Если номера нет, то используется предуыдущий как значение
		по умолчанию.
	"""
	# получить желаемый номер от пользователя:
	licence = Console.get_string('License', name='license', default=previous_licence)

	if not licence:  # либо использовать старый
		return previous_licence, None  # (licence, car)

	licence = licence.upper()
	ok, *data = handle_request('GET_CAR_DETAILS', licence)  # запросить данные с сервера
	if not ok:  # дается возможность получить от пользователя первую букву номера
		print(data[0])
		while True:
			start = Console.get_string('Start of licence', name='licence')
			if not start:
				return previous_licence, None

			start = start.upper()
			ok, *data = handle_request('GET_LICENCE_STARTING_WITH', start)  # запрос по первой букве
			if not data[0]:
				print('No licence starts with' + start)
				continue
			for i, licence in enumerate(data[0]):  # вывод нескольких результатов
				print('({0}) {1}'.format(i+1, licence))

			# выбор из этих нескольких от пользователя:
			answer = Console.get_integer('Enter choice (0 to cancel)', min=0, max=len(data[0]))
			if answer == 0:
				return previous_licence, None
			licence = data[0][answer-1]
			ok, *data = handle_request('GET_CAR_DETAILS', licence)
			if not ok:
				print(data[0])
				return previous_licence, None
			break
	return licence, CarTuple(*data)


def get_cars_list(previous_licence):
	ok, *data = handle_request('GET_CARS_LIST')
	if not ok:
		print(data[0])
		return previous_licence, None

	for i in data:
		print(i, end='\n')
	return previous_licence, None


def get_car_details(previous_licence):
	""" Получение информации о конкретном автомобиле.

		Если информация не получена, то используется предыдущий
		номер как значение по умолчанию.
	"""
	licence, car = retrieve_car_details(previous_licence)  # получить данные об автомобиле
	if car is not None:
		print('Licence: {0}\nSeats: {1[0]}\nMileage: {1[1]}\nOwner: {1[2]}'.format(licence, car))
	return licence


def change_mileage(previous_licence):
	""" Получает и обновляет элемент пробега. """
	licence, car = retrieve_car_details(previous_licence)  # запрос данных по номеру
	if car is None:  # данных нет
		return previous_licence

	# запрос пробега от пользователя:
	mileage = Console.get_integer('Mileage', name='mileage', default=car.mileage, min=0)
	if mileage == 0:
		return licence

	# обновить данные:
	ok, *data = handle_request('CHANGE_MILEAGE', licence, mileage)
	if not ok:
		print(data[0])
	else:
		print('Mileage successfully changed')
	return licence


def change_owner(previous_licence):
	licence, car = retrieve_car_details(previous_licence)  # запрос данных по номеру
	if car is None:  # данных нет
		return previous_licence

	# запрос пробега от пользователя:
	owner = Console.get_string('Owner', name='owner', default=car.owner)
	if not owner:
		return licence

	# обновить данные:
	ok, *data = handle_request('CHANGE_OWNER', licence, owner)
	if not ok:
		print(data[0])
	else:
		print('Owner successfully changed')
	return licence


def new_registration(previous_licence):
	licence = Console.get_string('Licence', name='licence')
	if not licence:
		return previous_licence
	licence = licence.upper()

	seats = Console.get_integer('Seats', name='seats', default=4, min=0)
	if not(1 < seats < 10):
		return previous_licence

	mileage = Console.get_integer('Mileage', name='mileage', default=0, min=0)
	owner = Console.get_string('Owner', name='owner')
	if not owner:
		return previous_licence

	ok, *data = handle_request('NEW_REGISTRATION', licence, seats, mileage, owner)
	if not ok:
		print(data[0])
	else:
		print('Car {} successfully registered'.format(licence))

	return licence


def quit(*ignore):
	sys.exit()


def stop_server(*ignore):
	handle_request('SHUTDOWN', wait_for_reply=False)
	sys.exit()


def main():
	if len(sys.argv) > 1:  # если переопределяем ip-адрес
		Address[0] = sys.argv[1]
	# пункты меню:
	call = dict(g=get_cars_list, c=get_car_details, m=change_mileage,
				o=change_owner, n=new_registration, s=stop_server, q=quit)
	menu = '(G)et cars list (C)ar Edit (M)ileage Edit (O)wner (N)ew car (S)top server (Q)uit'
	valid = frozenset('gcmonsq')
	# для запоминания последнего введенного номера, чтобы исп. как значение по умолч.:
	previous_licence = None

	while True:
		# получить валидный пользовательский ввод:
		action = Console.get_menu_choice(menu, valid, 'c', True)  # (msg, valid, default, force_lower)
		previous_licence = call[action](previous_licence)  # перезаписать номер на новый по умолчанию


main()
