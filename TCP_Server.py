import contextlib
import copy
import gzip
import os
import pickle
import socketserver
import struct
import sys
import threading
import random
import bisect


class Car:
	"""
		Класс-контейнер информации о кол-ве мест, пробеге
		и владельце в виде свойств.
		Класс не хранит информацию о номерном знаке, потому
		что он хранится в словаре в кач-ве ключа.
	"""
	def __init__(self, seats, mileage, owner):
		self.__seats = seats  # read-only
		self.mileage = mileage
		self.owner = owner

	@property
	def seats(self):
		return self.__seats

	@property
	def mileage(self):
		return self.__mileage

	@mileage.setter
	def mileage(self, mileage):
		self.__mileage = mileage

	@property
	def owner(self):
		return self.__owner

	@owner.setter
	def owner(self, owner):
		self.__owner = owner


class Finish(Exception):
	pass


class CarRegistrationServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
	""" Определение класса сервера. """
	pass


class RequestHandler(socketserver.StreamRequestHandler):
	""" Класс-обработчик событий сервера CarRegistrationServer. """
	Cars = None
	CarsLock = threading.Lock()  # блокировка доступа к словарю Cars
	CallLock = threading.Lock()
	Call = dict(  # словарь операций, выполняемых сервером
		GET_CARS_LIST=lambda self, *args: self.get_cars_list(*args),
		GET_CAR_DETAILS=lambda self, *args: self.get_car_details(*args),
		GET_LICENCE_STARTING_WITH=lambda self, *args: self.get_licence_starting_with(*args),
		CHANGE_MILEAGE=lambda self, *args: self.change_mileage(*args),
		CHANGE_OWNER=lambda self, *args: self.change_owner(*args),
		NEW_REGISTRATION=lambda self, *args: self.new_registration(*args),
		SHUTDOWN=lambda self, *args: self.shutdown(*args))
	''' Лямбды используются как обертки, т.к. методы не могут
		использоваться непосредственно из-за отсутствия ссылки
		на self на уровне класса.
		Решаемо размещением словаря после определения всех ф-й.
	'''
	def handle(self):
		"""
			Функция потока-экземпляра класса. Читает полученные
			от клиента данные, отправляет собственные данные.

		Протокол: первое сообщение о размере, второе -- данные.
			Передаваемые клиентом данные: кортеж (команда, *параметры).
			Ответ сервера: True/False/данные, сообщение при ошибке.
		"""
		InfoVersion = 1  # версия протокола
		InfoStruct = struct.Struct('!IB')  # беззнаковое целое -- байты размера сообщения

		info = self.rfile.read(InfoStruct.size)  # получить данные информации:
		size, version = InfoStruct.unpack(info)  # извлечь значение размера и версию
		if version > InfoVersion:
			reply = False, 'client is compatible'
		else:
			# распаковать заданный размер данных:
			data = pickle.loads(self.rfile.read(size))
			try:
				with RequestHandler.CallLock:
					function = self.Call[data[0]]  # отыскать функцию действия
				reply = function(self, *data[1:])  # сформировать ответ из ф-и (отдельно для укорочения блокировки)
			except Finish:  # при function=SHUTDOWN
				return
		data = pickle.dumps(reply, 3)  # законсервировать данные
		self.wfile.write(InfoStruct.pack(len(data), InfoVersion))  # передать размер
		self.wfile.write(data)  # передать данные

	def get_cars_list(self, *ignore):
		with RequestHandler.CarsLock:
			keys = list(self.Cars.keys())
		if keys is None:
			return False, 'No have cars in base'
		return True, sorted(keys[:])

	def get_licence_starting_with(self, start):
		with RequestHandler.CarsLock:
			keys = list(self.Cars.keys())  # получить список ключей словаря
		# бинарный поиск по ключам:
		keys.sort()
		right = left = bisect.bisect_left(keys, start)
		while right < len(keys) and keys[right].startswith(start):
			right += 1
		return True, keys[left:right]

	def get_car_details(self, licence):
		with RequestHandler.CarsLock:
			# получ. сведения об указанном по номеру автомобиле или None:
			car = copy.copy(self.Cars.get(licence, None))  # dict.get(), Cars=dict
		if car is not None:
			return True, car.seats, car.mileage, car.owner
		return False, 'This licence is not registered'

	def change_mileage(self, licence, mileage):
		if mileage < 0:
			return False, 'Cannot set a negative mileage'
		with RequestHandler.CarsLock:
			car = self.Cars.get(licence, None)
			if car is not None:
				if car.mileage < mileage:
					car.mileage = mileage
					return True, None
				return False, 'Cannot wind the odometer back'
		return False, 'This licence is not registered'

	def change_owner(self, licence, owner):
		if not owner:
			return False, 'Cannot set an empty owner'
		with RequestHandler.CarsLock:
			car = self.Cars.get(licence, None)
			if car is not None:
				car.owner = owner
				return True, None
		return False, 'This licence is not registered'

	def new_registration(self, licence, seats, mileage, owner):
		if not licence:
			return False, 'Cannot set an empty licence'
		if seats not in {2, 4, 5, 6, 7, 8, 9}:
			return False, 'Cannot register car with invalid seats'
		if mileage < 0:
			return False, 'Cannot set a negative mileage'
		if not owner:
			return False, 'Cannot set an empty owner'

		with RequestHandler.CarsLock:
			if licence not in self.Cars:
				self.Cars[licence] = Car(seats, mileage, owner)
				return True, None
		return False, 'Cannot register duplicate licence'

	def shutdown(self, *ignore):
		self.server.shutdown()
		raise Finish()


def load(filename):
	""" Получение данных из законсервированного файла. """
	if not os.path.exists(filename):  # Fake data:
		cars = {}
		owners = []

		for forename, surname in zip(("Warisha", "Elysha", "Liona",
                "Kassandra", "Simone", "Halima", "Liona", "Zack",
                "Josiah", "Sam", "Braedon", "Eleni"),
                ("Chandler", "Drennan", "Stead", "Doole", "Reneau",
                 "Dent", "Sheckles", "Dent", "Reddihough", "Dodwell",
                 "Conner", "Abson")):
			owners.append(forename + ' ' + surname)

		for licenсe in ("1H1890C", "FHV449", "ABK3035", "215 MZN",
                "6DQX521", "174-WWA", "999991", "DA 4020", "303 LNM",
                "BEQ 0549", "1A US923", "A37 4791", "393 TUT", "458 ARW",
                "024 HYR", "SKM 648", "1253 QA", "4EB S80", "BYC 6654",
                "SRK-423", "3DB 09J", "3C-5772F", "PYJ 996", "768-VHN",
                "262 2636", "WYZ-94L", "326-PKF", "EJB-3105", "XXN-5911",
                "HVP 283", "EKW 6345", "069 DSM", "GZB-6052", "HGD-498",
                "833-132", "1XG 831", "831-THB", "HMR-299", "A04 4HE",
                "ERG 827", "XVT-2416", "306-XXL", "530-NBE", "2-4JHJ"):

			mileage = random.randint(0, 100000)
			seats = random.choice((2, 4, 5, 6, 7))
			owner = random.choice(owners)
			cars[licenсe] = Car(seats, mileage, owner)
		return cars
	try:
		with contextlib.closing(gzip.open(filename, 'rb')) as fh:
			return pickle.load(fh)  # распаковать данные
	except (EnvironmentError, pickle.UnpicklingError) as err:
		print('server cannot load data: {}'.format(err))
		sys.exit(1)


def save(filename, cars):
	""" Консервирование данных в файл. """
	try:
		with contextlib.closing(gzip.open(filename, 'wb')) as fh:
			pickle.dump(cars, fh, 3)
	except (EnvironmentError, pickle.PicklingError) as err:
		print('server cannot to save data: {}'.format(err))
		sys.exit(1)


def main():
	# Формирование базы автомобилей из файла:
	filename = os.path.join(os.path.dirname(__file__), 'car-registrations.dat')
	cars = load(filename)

	print('Loaded {} car registrations'.format(len(cars)))
	RequestHandler.Cars = cars  # добавление атрибута в клас

	# Запуск сервера:
	server = None
	try:
		server = CarRegistrationServer(('', 9653), RequestHandler)
		server.serve_forever()
	except Exception as err:
		print('ERROR', err)
	finally:
		if server is not None:
			server.shutdown()
			save(filename, cars)
			print('Saved {} car registrations'.format(len(cars)))


main()
