#! /bin/bash
set -x

# Set online=1 in case the probe is directly involved in switching the packets (the interface receives both incoming and outgoing packets)
online=1
interface="wlp59s0"
firewall="fw"
dynmon_ddos="monitor_ddos"
dynmon_crypto="monitor_crypto"

if [ $online -eq 0 ]
then
	path_ddos_config="./src/offline/ddos_detection/dataplane.json"
	path_crypto_config="./src/offline/crypto_mining/dataplane.json"
else
	path_ddos_config="./src/online/ddos_detection/dataplane.json"
	path_crypto_config="./src/online/crypto_mining/dataplane.json"
fi


ret=$(docker container ls | grep "s41m0n/polycube:toshi")
if [ $? -eq 0 ]
then
	echo "Found Polycube daemon running"
else
	echo "Running Polycube daemon at http://localhost:9000"
	docker run -p 9000:9000 -d --rm --privileged --network host \
		-v /lib/modules:/lib/modules:ro -v /usr/src:/usr/src:ro -v /etc/localtime:/etc/localtime:ro \
		-it s41m0n/polycube:toshi /bin/bash -c 'polycubed'
	sleep 8
fi

echo "Creating Dynmon for DDos detection"
./tools/dynmon_injector.py $dynmon_ddos $interface $path_ddos_config

echo "Creating Dynmon for Crypto detection"
./tools/dynmon_injector.py $dynmon_crypto $interface $path_crypto_config

echo "Creating Firewall instance"
./tools/firewall_injector.py $firewall $interface

echo "Your environment is ready to be used :)"
