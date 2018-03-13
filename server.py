import asyncio
import logging
import server_utils as utils
from server_utils import Client
from aiohttp import ClientSession
import sys
import time
import propogate_client


# Client dictionary will need to be global, because protocol is per client
clients_d = dict()

#https://docs.python.org/3/library/asyncio-protocol.html
class EchoServerClientProtocol(asyncio.Protocol):

	def __init__(self, name, loop):
		super().__init__()
		self.loop = loop
		self.name = name


	def connection_made(self, transport):
		peername = transport.get_extra_info('peername')
		logging.info('Connection from {}'.format(peername))
		self.transport = transport


	# data_received will call the parse message function, which will basically do all the work.
	# This is because in order for WHATSAT to run a asyncio future, this function cannot merely
	# transport the return value of parse_message
	def data_received(self, data):
		message = data.decode()
		# TODO: change print to log
		logging.info('Data received: {!r}'.format(message))

		# We need to parse the data first to see what kind of message was sent from the client
		# this method also returns the response
		response_message = self.parse_message(message)



	# FOR INVALID MESSAGES:
	def error_message_and_close(self, message):
		# Servers should respond to invalid commands with a line that contains a question mark (?), 
		# a space, and then a copy of the invalid command.
		response = '? ' + message
	
		response_message_formatted = '{}'.format(response)

		# Send the encoded version of the message aka data
		self.transport.write(response_message_formatted.encode())

		logging.info('Close the client socket\n\n')
		self.transport.close()


	# FOR VALID MESSAGES:
	def transport_message_and_close(self, message):
		response_message_formatted = '{}'.format(message)

		# Send the encoded version of the message aka data
		self.transport.write(response_message_formatted.encode())

		logging.info('Close the client socket\n\n')
		self.transport.close()



	# parse_message will parse the message, see if there is an error, and return a response string
	def parse_message(self, message):
		message_split = message.split(' ')

		# Keep track of when we received the message from the client.
		# This isnt exact, but its probably good enough
		time_rcv = time.time()

		# Three types of messages: IAMAT, AT, WHATSAT
		##### IAMAT #####
		if message_split[0] == 'IAMAT':
			# Check if its a valid IAMAT
			if utils.isWellFormed(message, 'IAMAT') == False:
				logging.info('Invalid IAMAT')
				self.error_message_and_close(message)

			else:
				# Extract info
				# [1]: client ID (eg; kiwi.cs.ucla.edu)
				# [2]: latitude and longitude in decimal degrees
				# [3]: client's idea of when it sent the message
				client_ID = message_split[1]
				client_lat_long = message_split[2]
				client_time_sent = message_split[3]

				# Respond ex: AT Goloman +0.263873386 kiwi.cs.ucla.edu +34.068930-118.445127 1520023934.918963997
				# time_elapsed is the difference between the server's idea of when it got the message from the client and the client's time stamp
				time_elapsed = time_rcv - float(client_time_sent)
				if time_elapsed >= 0:
					time_elapsed_s = '+' + str(time_elapsed)
				else:
					time_elapsed_s = time_elapsed

				# form the response
				response = 'AT '+ self.name +' '+ time_elapsed_s +' '+ client_ID +' '+ client_lat_long +' '+ client_time_sent

				# add client to dictionary
				logging.info('Updating client dictionary with: {}'.format(client_ID))
				clients_d[client_ID] = Client(client_ID, client_lat_long, client_time_sent)

				# When a server gets new info, it propagates it to the other servers it talks to
				self.update_neighbors(response)

				self.transport_message_and_close(response)
				

		##### WHATSAT #####
		elif message_split[0] == 'WHATSAT':
			# target client ID that client wants info about
			target_client_ID = message_split[1]

			# Check if its a valid WHATSAT
			if utils.isWellFormed(message, 'WHATSAT') == False:
				logging.info('Invalid WHATSAT: not well formed')
				self.error_message_and_close(message)
			elif clients_d.get(target_client_ID) is None:
				logging.info('Invalid WHATSAT: target client not found')
				self.error_message_and_close(message)

			else:
				# Extract info
				# [1]: client ID (eg; kiwi.cs.ucla.edu)
				# [2]: client_radius - a radius (in kilometers) from the client (e.g., 10)
				# [3]: client_upper_bound - an upper bound on the amount of information to receive from Places data within that radius of the client (e.g., 5 items).
				client_radius = message_split[2]
				client_upper_bound = message_split[3]

				# We need to query the Google Places API 
				target_client = clients_d[target_client_ID]
				target_loc = target_client.location.replace('+', ',').replace('-', ',-')
				# Will strip off initial "positive sign"
				if target_loc[0] == ',':
					target_loc = target_loc[1:]

				# Respond ex: AT Goloman +0.263873386 kiwi.cs.ucla.edu +34.068930-118.445127 1520023934.918963997
				# time_elapsed is the difference between the server's idea of when it got the message from the client and the client's time stamp
				time_elapsed = time_rcv - float(target_client.time)
				if time_elapsed >= 0:
					time_elapsed_s = '+' + str(time_elapsed)
				else:
					time_elapsed_s = time_elapsed
				# form the response
				response = 'AT '+ self.name +' '+ time_elapsed_s +' '+ target_client.ID +' '+ target_client.location +' '+ target_client.time

				#first send aT, then google response
				response_message_formatted = '{}'.format(response)
				self.transport.write(response_message_formatted.encode())
				google_places_response = self.google_places_request(target_loc, client_radius)

				


		##### AT #####
		elif message_split[0] == 'AT':
			# Extract info: AT Goloman +0.263873386 kiwi.cs.ucla.edu +34.068930-118.445127 1520023934.918963997
			server_ID = message_split[1] 
			clock_skew = message_split[2]
			client_ID = message_split[3]
			client_lat_long = message_split[4]
			client_time_sent = message_split[5]
			server_from = message_split[-1]
			#update dictionary
			clients_d[client_ID] = Client(client_ID, client_lat_long, client_time_sent)
			#update neighbors
			self.update_neighbors(message)



		else:
			logging.info('Received badly formatted msg')
			self.error_message_and_close(message)



	# This is the function we wil luse to make an http request from google places
	def google_places_request(self, target_loc, client_radius):
		# Setup request
		query = 'key={}&location={}&radius={}'.format(utils.GOOGLE_PLACES_API_KEY, target_loc, client_radius)
		url = f'https://maps.googleapis.com/maps/api/place/nearbysearch/json?{query}'
		#request = (f'GET {uri} HTTP/1.1\r\nHost: {host}\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n')

		# Send Google Places our formatted request
		async def google_it(uri):
			async with ClientSession() as session:
				async with session.get(uri) as response:
					response_read = await response.read()
					response_decoded = response_read.decode('utf-8')
					response_fixed = '\n'.join(response_decoded.split('\n\n'))
					response_fixed_again = response_fixed.rstrip('\n')
					response_fixed_again_again = response_fixed_again + '\n\n'
					logging.info('Sending WHATSAT: response received')
					self.transport_message_and_close(response_fixed_again_again)

		asyncio.ensure_future(google_it(url))




    # When a server gets new info, it propagates it to the other servers it talks to
	def update_neighbors(self, message):
		message_split = message.split(' ')
		# we wanna run an ensure_future for each neighbor that isnt the source of the AT
		message_signed = message + ' ' + self.name
		for neighbor in utils.getNeighbors(self.name):
			# We dont want to resend to either the source node, or the neighbors of the source node
			if neighbor in message_split:
				continue
			if self.name != message_split[1]:
				if neighbor in utils.getNeighbors(message_split[1]):
					continue
			asyncio.ensure_future(propogate_client.main(message_signed, neighbor))
			logging.info('Propogating message to: {}'.format(neighbor))




def main():
	# first check arguments to make sure server was initialized correctly
	if len(sys.argv) != 2:
		sys.stdout.write('Invalid number of args')
		exit(1)

	# get server name and port 
	server_name = sys.argv[1]
	server_port = utils.getPort(server_name)

	sys.stdout.write('Name: %s.\n' % (server_name))
	sys.stdout.write('Port: %d.\n' % (server_port))

	if server_port == -1: 
		sys.stdout.write('Invalid server name')
		exit(1)

	logFileName = server_name + '.log'
	logging.basicConfig(filename=logFileName,level=logging.INFO)

	# start the server
	loop = asyncio.get_event_loop()
	# Each client connection will create a new protocol instance
	coro = loop.create_server(lambda: EchoServerClientProtocol(server_name, loop), '127.0.0.1', server_port)
	server = loop.run_until_complete(coro)

	# Serve requests until Ctrl+C is pressed
	logging.info('Serving on {} %s'.format(server.sockets[0].getsockname()) % server_name)
	try:
		loop.run_forever()
	except KeyboardInterrupt:
		pass

	# Close the server
	server.close()
	loop.run_until_complete(server.wait_closed())
	loop.close()
	loop.close()

if __name__ == "__main__":
	main()