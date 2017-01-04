import sys
import datetime
"""
	Содержит некоторые полезные функции получения значений,
	вводимых пользователем в консоли.
"""


class _RangeError(Exception):
	pass


def get_string(msg, name='string', default=None,
			   min_len=0, max_len=80, force_lower=False):
	msg += ': ' if default is None else ' [{}]: '.format(default)
	while True:
		try:
			line = input(msg)
			if not line:
				if default is not None:
					return default
				if min_len == 0:
					return ''
				else:
					raise ValueError('{} may not be empty'.format(name))

			if not (min_len <= len(line) <= max_len):
				raise ValueError('{0} must have at least {1} and at most {2} '
								 'characters'.format(name, min_len, max_len))

			return line if not force_lower else line.lower()
		except ValueError as err:
			print('ERROR', err)


def get_integer(msg, name='integer', default=None, min=None,
				max=None, allow_zero=True):
	msg += ': ' if default is None else ' [{}]: '.format(default)
	while True:
		try:
			line = input(msg)
			if not line and default is not None:
					return default
			x = int(line)
			if x == 0:
				if allow_zero:
					return x
				else:
					raise _RangeError('{} may not be 0'.format(name))

			if (min is not None and min > x) or (max is not None and max < x):
				raise _RangeError('{0} must be between {1} and {2} inclusive{3}'
								 .format(name, min, max, ' (or 0)' if allow_zero else ''))

			return x
		except _RangeError as err:
			print('ERROR', err)
		except ValueError:
			print('ERROR {} must be an integer'.format(name))


def get_float(msg, name='float', default=None, min=None,
				max=None, allow_zero=True):
	msg += ': ' if default is None else ' [{}]: '.format(default)
	while True:
		try:
			line = input(msg)
			if not line and default is not None:
					return default
			x = float(line)
			if abs(x) < sys.float_info.epsilon:
				if allow_zero:
					return x
				else:
					raise _RangeError('{} may not be 0.0'.format(name))

			if (min is not None and min > x) or (max is not None and max < x):
				raise _RangeError('{0} must be between {1} and {2} inclusive{3}'
								 .format(name, min, max, ' (or 0.0)' if allow_zero else ''))

			return x
		except _RangeError as err:
			print('ERROR', err)
		except ValueError:
			print('ERROR {} must be an float'.format(name))


def get_bool(msg, default=None):
	yes = frozenset({'1', 'y', 'yes', 't', 'true', 'ok', 'да'})
	msg += ' (y/yes/n/no)'
	msg += ': ' if default is None else ' [{}]: '.format(default)

	line = input(msg)
	if not line and default is not None:
		return default in yes
	return line.lower() in yes


def get_date(msg, default=None, format='%y-%m-%d'):
	msg += ': ' if default is None else ' [{}]: '.format(default)
	while True:
		try:
			line = input(msg)
			if not line and default is not None:
				return default
			return datetime.datetime.strptime(line, format)
		except ValueError as err:
			print('ERROR', err)


def get_menu_choice(msg, valid, default=None, force_lower=False):
	msg += ': ' if default is None else ' [{}]: '.format(default)
	while True:
		line = input(msg)
		if not line and default is not None:
			return default
		if line not in valid:
			print('ERROR only {} are valid choices'.format(', '.join(["'{}'".format(x) for x in sorted(valid)])))
		else:
			return line if not force_lower else line.lower()

