import socket
import message_pb2
UDP_IP = "192.168.93.13"
UDP_PORT = 8898


print "UDP target IP:", UDP_IP
print "UDP target port", UDP_PORT

com =  message_pb2.Command()
com.PGAGainCommand.gain = int(raw_input("Enter gain (1,2,3,4,6,8,12,16,24,32,48,64,96,128)"))

print com

msg = com.SerializeToString()
print msg
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(msg,(UDP_IP,UDP_PORT))
