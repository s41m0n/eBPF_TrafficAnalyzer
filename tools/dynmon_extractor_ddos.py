#!/usr/bin/python3
# coding: utf-8

import time, threading, argparse, requests, json, socket, os

POLYCUBED_ADDR 				= 'localhost'
POLYCUBED_PORT 				= 9000
REQUESTS_TIMEOUT 			= 10
OUTPUT_DIR 					= 'dump_ddos'
INTERVAL 					= 2   		 	# seconds to wait before retrieving again the features, to have less just insert a decimal number like 0.01
protocol_map 				= dict(			# map protocol integer value to name
	[(6, "TCP"), (17, "UDP"), (1, "ICMP")])

polycubed_endpoint = 'http://{}:{}/polycube/v1'
counter = 0

def main():
	global polycubed_endpoint

	args = parseArguments()

	addr = args['address']
	port = args['port']
	cube_name = args['cube_name']
	output_dir = args['output']
	interval = args['interval']
	is_json = args['json']

	polycubed_endpoint = polycubed_endpoint.format(addr, port)

	checkIfOutputDirExists(output_dir)

	dynmonConsume(cube_name, output_dir, interval, is_json)


def dynmonConsume(cube_name, output_dir, interval, is_json):
	global counter
	parsed_entries = []
	my_count = counter
	counter += 1
	
	start_time = time.time()
	metric =  getMetric(cube_name)
	req_time = time.time()

	threading.Timer(interval, dynmonConsume, (cube_name, output_dir, interval, is_json)).start()

	if not metric:
		print(f'Got nothing ...\n\tExecution n°: {my_count}\n\tTime to retrieve metrics: {req_time - start_time} (s)\n\tTime to parse: {time.time() - req_time} (s)')
		return

	parseAndStore(metric, output_dir, my_count) if is_json is False	else parseAndStoreJson(metric, output_dir, my_count)
	print(f'Got something!\n\tExecution n°: {my_count}\n\tTime to retrieve metrics: {req_time - start_time} (s)\n\tTime to parse: {time.time() - req_time} (s)\n\tPacket parsed: {len(metric)}')


def parseAndStoreJson(entries, output_dir, counter):
	data = []
	flows = {}
	for entry in entries:
		sid = entry['id']
		flowIdentifier = (sid['saddr'], sid['sport'], sid['daddr'], sid['dport'], sid['proto'])
		seconds = entry['timestamp'] // 1000000000
		nanoseconds = int(str(entry['timestamp'])[:9])
		features = [seconds, nanoseconds]
		for key, value in entry.items():
			if key != 'id' and key != 'timestamp': features.append(value)
		
		if flowIdentifier in flows: flows[flowIdentifier].append(features)
		else: flows[flowIdentifier] = [features]

	'''
	NOW YOU HAVE `flows` THAT IS A DICTIONARY DATA STRUCTURE:
	{
		(srcIp_big_endian,...) : [{
				"seconds": x,
				"nanoseconds": y,
				...
			},
			...
		]
		...
	}
	WHERE EVERY ELEMENT OF THE ARRAYS CORRESPOND TO A SINGLE PACKET (IF YOU READ ALL THE COLUMS AT ONCE YOU GET THE PACKET FEATURES).
	'''
	for key, value in flows.items():
		parsed_key = (
			socket.inet_ntoa(key[0].to_bytes(4, 'little')),
			socket.ntohs(key[1]),
			socket.inet_ntoa(key[2].to_bytes(4, 'little')),
			socket.ntohs(key[3]),
			protocol_map[key[4]]	
		)
		data.append({"id": key, "packets": value})

	'''
	NOW YOU HAVE `data` which is the json-like object to be printed, retrieved from `flows`:
	{
		"id": [srcIp, dstIp, srcPort, dstPort, proto],
		"packets": [...]
	}

	THE FOLLOWING CODE PRINTS THE VALUES TO FILE. REMOVE THEM AND INSERT YOUR INTERACTIONS IN THE FINAL VERSION.
	'''
	with open(f'{output_dir}/result_{counter}.json', 'w') as fp:
		json.dump(data, fp, indent=2)


def parseAndStore(entries, output_dir, counter):
	flows = {}
	for entry in entries:
		seconds = entry['timestamp'] // 1000000000
		nanoseconds = str(entry['timestamp'])[:9]
		sid = entry['id']
		flowIdentifier = (sid['saddr'], sid['sport'], sid['daddr'], sid['dport'], sid['proto'])
		
		if flowIdentifier in flows:
			flows[flowIdentifier]['seconds'].append(seconds)
			flows[flowIdentifier]['nanoseconds'].append(nanoseconds)
			flows[flowIdentifier]['length'].append(entry['length'])
			flows[flowIdentifier]['ipFlagsFrag'].append(entry['ipFlagsFrag'])
			flows[flowIdentifier]['tcpLen'].append(entry['tcpLen'])
			flows[flowIdentifier]['tcpAck'].append(entry['tcpAck'])
			flows[flowIdentifier]['tcpFlags'].append(entry['tcpFlags'])
			flows[flowIdentifier]['tcpWin'].append(entry['tcpWin'])
			flows[flowIdentifier]['udpSize'].append(entry['udpSize'])
			flows[flowIdentifier]['icmpType'].append(entry['icmpType'])
		else:
			flows[flowIdentifier] = {
				'seconds': 		[seconds],
				'nanoseconds':  [nanoseconds],
				'length':      	[entry['length']],
				'ipFlagsFrag':	[entry['ipFlagsFrag']],
				'tcpLen':		[entry['tcpLen']],
				'tcpAck':		[entry['tcpAck']],
				'tcpFlags':		[entry['tcpFlags']],
				'tcpWin':		[entry['tcpWin']],
				'udpSize':		[entry['udpSize']],
				'icmpType':		[entry['icmpType']]
			}

	'''
	NOW YOU HAVE `flows` THAT IS A DICTIONARY DATA STRUCTURE optimized for printing csv:
	{
		(src_ip_big_endian, ...) : {
			"seconds": [...],
			"nanoseconds": [...],
			...
		},
		...
	}
	WHERE EVERY ELEMENT OF THE ARRAYS CORRESPOND TO A SINGLE PACKET (IF YOU READ ALL THE COLUMS AT ONCE YOU GET THE PACKET FEATURES).
	'''

	for key, value in flows.items():
		parsed_key = (
			socket.inet_ntoa(key[0].to_bytes(4, 'little')),
			socket.ntohs(key[1]),
			socket.inet_ntoa(key[2].to_bytes(4, 'little')),
			socket.ntohs(key[3]),
			protocol_map[key[4]]
		)
		'''
		THE FOLLOWING CODE PRINTS THE VALUES TO FILE. REMOVE THEM AND INSERT YOUR INTERACTIONS IN THE FINAL VERSION.
		'''
		with open(f"{output_dir}/{parsed_key[0]}-{parsed_key[1]}___{parsed_key[2]}-{parsed_key[3]}___{parsed_key[4]}-iter{counter}.csv", 'w') as fp:
			fp.write(""
				f"Seconds     ,\t{', '.join(map(str,value['seconds']))}\n"
				f"Ns          ,\t{', '.join(map(str,value['nanoseconds']))}\n"
				f"Length      ,\t{', '.join(map(str,value['length']))}\n"
				f"IPv4 flags  ,\t{', '.join(map(str,value['ipFlagsFrag']))}\n"
				f"TCP len     ,\t{', '.join(map(str,value['tcpLen']))}\n"
				f"TCP ACK     ,\t{', '.join(map(str,value['tcpAck']))}\n"
				f"TCP flags   ,\t{', '.join(map(str,value['tcpFlags']))}\n"
				f"TCP Win     ,\t{', '.join(map(str,value['tcpWin']))}\n"
				f"UDP len     ,\t{', '.join(map(str,value['udpSize']))}\n"
				f"ICMP type   ,\t{', '.join(map(str,value['icmpType']))}")


def checkIfOutputDirExists(output_dir):
	try:
		os.mkdir(output_dir)
	except IOError:
		print(f"Directory {output_dir} already exists")
	except OSError:
		print (f"Creation of the directory {output_dir} failed")
	else:
		print (f"Successfully created the directory {output_dir}")


def getMetric(cube_name):
	try:
		response = requests.get(f'{polycubed_endpoint}/dynmon/{cube_name}/metrics/ingress-metrics/PACKET_BUFFER_DDOS/value', timeout=REQUESTS_TIMEOUT)
		if response.status_code == 500:
			print(response.content)
			exit(1)
		response.raise_for_status()
		return json.loads(response.content)
	except requests.exceptions.HTTPError:
		return False, None
	except requests.exceptions.ConnectionError:
		print('Connection error: unable to connect to polycube daemon.')
		exit(1)
	except requests.exceptions.Timeout:
		print('Timeout error: unable to connect to polycube daemon.')
		exit(1)
	except requests.exceptions.RequestException:
		print('Error: unable to connect to polycube daemon.')
		exit(1) 


def parseArguments():
	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('cube_name', help='indicates the name of the cube', type=str)
	parser.add_argument('-a', '--address', help='set the polycube daemon ip address', type=str, default=POLYCUBED_ADDR)
	parser.add_argument('-p', '--port', help='set the polycube daemon port', type=int, default=POLYCUBED_PORT)
	parser.add_argument('-o', '--output', help='set the output directory', type=str, default=OUTPUT_DIR)
	parser.add_argument('-j', '--json', help='set the output files format to json', action='store_true')
	parser.add_argument('-i', '--interval', help='set time interval for polycube query', type=float, default=INTERVAL)
	return parser.parse_args().__dict__


if __name__ == '__main__':
	main()