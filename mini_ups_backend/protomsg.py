import socket
import sys
import world_amazon_pb2, world_ups_pb2, au_pb2

from google.protobuf.internal.decoder import _DecodeVarint32
from google.protobuf.internal.encoder import _EncodeVarint

def sendMSG(fd, msg):
    _EncodeVarint(fd.send, len(msg), None)
    fd.sendall(msg)

def recvMSG(clientfd):
    var_int_buff = []
    count = 0
    while True:
        try:
            buf = clientfd.recv(1)
            print("recvMSG:", buf)
            var_int_buff += buf
            msg_len, new_pos = _DecodeVarint32(var_int_buff, 0)
            if new_pos != 0:
                break
        except Exception as e:
            print(var_int_buff)
            print("[ERROR] in recvmsg")
            # raise e
            print(e)
    whole_message = clientfd.recv(msg_len)
    return whole_message

def sendACK(fd,seq_num):
    resp_send = au_pb2.UACommand()
    resp_send.acks.append(seq_num)
    sendMSG(fd,resp_send.SerializeToString())

def sendACK_to_world(fd,seq_num):
    comm = world_ups_pb2.UCommands()
    comm.acks.append(seq_num)
    sendMSG(fd,comm.SerializeToString())