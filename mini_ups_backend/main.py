import socket
import sys
import select
import time
import logging
import threading
import world_amazon_pb2, world_ups_pb2, au_pb2
import psycopg2
import smtplib

from email.mime.text import MIMEText
from notipyer.email_notify import set_email_config,send_email
from dbconnection import *
from protomsg import *

#---------------global variables
world_fd = None
amazon_fd = None
worldid=0
seq_num = 0
world_seq = [] #track sequence number world sent to us
amazon_seq = [] #track sequence number amazon sent to us
my_seq = [] #track ack that world and amazon sent back to us
truck_num = 3 #where to initialize truck number
finished_dict = {} #a dict for key-value pairs such as truckid:seqnum from UFinished
lock = threading.Lock()
lock1 = threading.Lock()
truck_in_use = set()

#---------------deal with world
def initialize_connection_with_world():
    client = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        client.connect(('vcm-26825.vm.duke.edu', 12345))
        print("connected with world successfully")
        return client
    except socket.error:
        print("connect failed")

#give truck number to world, world returns back UConnect msg
def initialize_world():
    global truck_num
    print("initialize truck num: ", truck_num)
    global world_fd
    uconnect_msg = world_ups_pb2.UConnect()
    conn = connectDB()
    cur = conn.cursor()
    sql = "INSERT INTO my_ups_truck(truckid, truckstatus) VALUES (%s, %s)"
    #--------------!!todo: empty tables
    for i in range(truck_num): #id start from 0
        print("initialize truck id: ", i)
        truck = uconnect_msg.trucks.add()
        truck.id = i
        truck.x = 0
        truck.y = 0
        cur.execute(sql, (i,1))
    conn.commit()
    cur.close()
    closeDB(conn)
    uconnect_msg.isAmazon = False

    #sendmsg
    sendMSG(world_fd, uconnect_msg.SerializeToString())
    print("Initilization msg sent to world")

    recv_msg = recvMSG(world_fd)
    uc = world_ups_pb2.UConnected()
    uc.ParseFromString(recv_msg)
    print("World connect result: "+ uc.result)
    print("World ID received: ")
    print(uc.worldid)
    return uc.worldid

def reconnect_to_world(): 
    global world_fd
    global worldid
    uconnect_msg = world_ups_pb2.UConnect()
    uconnect_msg.worldid = worldid
    uconnect_msg.isAmazon = False
    sendMSG(world_fd,uconnect_msg.SerializeToString())
    recv_msg = recvMSG(world_fd)
    uconnected = world_ups_pb2.UConnected()
    uconnected.ParseFromString(uconnected)
    print("World reconnect result: "+uconnected.result)

def handle_world_ufinished(comp): #!!check
    global world_seq
    global finished_dict
    global world_fd
    #not sure if need status
    print("[DEBUG]:handling ufinished")
    if comp.seqnum in world_seq:
        sendACK_to_world(world_fd,comp.seqnum)
        return
    '''
    temp = ""
    temp += str(comp.truckid)
    temp0 = temp+"seqnum"
    finished_dict[temp0] = int(comp.seqnum)
    temp1 = temp+"x"
    finished_dict[temp1] = int(comp.x)
    temp2 = temp+"y"
    finished_dict[temp2] = int(comp.y)
    '''
    temp = comp.status
    print("!!!!!!!!temp: ",temp)
    wareh = "WAREHOUSE"
    if wareh in temp:
        finished_dict[comp.truckid] = comp.seqnum
        print("warehouse")
    else:
        print("none")

def handle_world_udeliverymade(deliver):
    global world_seq
    global world_fd
    truck = deliver.truckid
    trackingnum = deliver.packageid
    wor_seq = deliver.seqnum
    if wor_seq in world_seq:
        sendACK_to_world(world_fd,wor_seq)
        return
    #update database
    conn = connectDB()
    cur = conn.cursor()
    sql = "UPDATE my_ups_package SET packagestatus = 4 WHERE trackingnum=%s"
    cur.execute(sql,(trackingnum,))
    conn.commit()
    cur.close()
    #send ack to world
    sendACK_to_world(world_fd,wor_seq)
    world_seq.append(wor_seq)
    #send delivered to Amazon
    print("handle world udeliverymade finished")
    send_delievered_to_amazon(trackingnum)

def handle_world_msg():
    global my_seq
    global world_fd
    msg = recvMSG(world_fd)
    #check if disconnected
    if len(msg) ==0:
        print("World disconnected. Reconnecting...")
        world_fd = initialize_connection_with_world()
        reconnect_to_world()
        return 
    print(msg)
    comm = world_ups_pb2.UResponses()
    comm.ParseFromString(msg)
    print("received msg from world: ")
    print(comm)
    for err in comm.error:
        print("[ERROR]: err from world:", err.err)
    for ack in comm.acks:
        print("ack received ", ack)
        my_seq.append(ack)
    for comp in comm.completions:
        print("handling completions")
        t10 = threading.Thread(target = handle_world_ufinished, args=(comp,),daemon=True)
        t10.start()
        #handle_world_ufinished(comp)
    for deliver in comm.delivered:
        print("handling delivered")
        t20 = threading.Thread(target = handle_world_udeliverymade, args=(deliver,), daemon=True)
        t20.start()
        #handle_world_udeliverymade(deliver)
    for truckstu in comm.truckstatus:
        print("handling truckstatus")
        t30 = threading.Thread(target = handle_truck_status, args=(truckstu,), daemon=True)
        t30.start()
        #handle_truck_status(truckstu)

#---------------------------do for world
def send_pickup_to_world(truckid,whid): #no problem
    global my_seq
    global seq_num
    global world_fd
    global truck_in_use
    print("[DEBUG]:enter send pickup to world")
    print("truck id", truckid)
    print("whid", whid)
    ucomm = world_ups_pb2.UCommands()
    ucomm.simspeed = 10000
    pkup = ucomm.pickups.add()
    pkup.truckid = truckid
    pkup.whid = whid
    lock.acquire()
    temp_seq = seq_num
    seq_num+=1
    lock.release()
    pkup.seqnum = temp_seq
    sendMSG(world_fd,ucomm.SerializeToString())
    print("[DEBUG]:send pick up info to world")
    while temp_seq not in my_seq: #need ack, so wait until ack'ed, resend after some time
        print("[DEBUG]:waiting for ack from world")
        time.sleep(1)
        sendMSG(world_fd,ucomm.SerializeToString())
    print("check if truck arrived")
    truck_in_use.remove(truckid)
    check_truck_arrived_warehouse(truckid,whid)

def check_truck_arrived_warehouse(truckid,whid):
    global world_seq
    global finished_dict
    print("Entered check_truck_arrived_warehouse")
    print("finshed dict: ", finished_dict)
    '''
    temp = ""
    temp += str(truckid)
    temp0 = temp+"seqnum"
    temp1 = temp+"x"
    temp2 = temp+"y"
    while finished_dict.get(temp0) == None: #!!check: see if truck arrived, if not, wait for some time and try again
        print("[DEBUG]:waiting for truck arrival at warehouse")
        time.sleep(1)
    '''
    while finished_dict.get(truckid) == None: #!!check: see if truck arrived, if not, wait for some time and try again
        print("[DEBUG]:waiting for truck arrival at warehouse")
        time.sleep(1)
    '''
    #truck arrived, check if it arrived the warehouse (versus delivered)
    conn = connectDB()
    cur = conn.cursor()
    sql = "SELECT * FROM my_ups_warehouse WHERE warehouseid = %s"
    cur.execute(sql,(whid,))
    row = cur.fetchone()
    warehousex = 0
    warehousey = 0
    for item in row: #!!check: 只return一个东西，不确定是否需要for
        warehousex = item[1]
        warehousey = item[2]
    cur.close()
    closeDB(conn)
    print("[DEBUG]:1")
    if warehousex == finished_dict.get(temp1) and warehousey == finished_dict.get(temp2):
    '''
    #send ack to world
    sendACK_to_world(world_fd, finished_dict.get(truckid))
    world_seq.append(finished_dict.get(truckid))
    #change package status, put all available package tracking num in list
    packagelist = []
    conn = connectDB()
    cur = conn.cursor()
    sql = "SELECT trackingnum FROM my_ups_package WHERE packagestatus = 1 AND truckid = %s AND warehouseid = %s"
    cur.execute(sql,(truckid,whid))
    row = cur.fetchall()
    for item in row:
        packagelist.append(item[0])
    finished_dict.pop(truckid) #empty finished dict for future use
    print("finished matching truck and warehouse")
    print(finished_dict)
    print("packages: ",packagelist)
    send_truck_arrived_to_amazon(packagelist,truckid)
    '''
    else:
        check_truck_arrived_warehouse(truckid,whid) #repeatedly check until actually arrived warehouse
    '''

def send_world_to_deliver(truck,pack):
    global my_seq
    global world_fd
    global seq_num
    print("Entering send_world_to_deliver")
    ucomm = world_ups_pb2.UCommands()
    ucomm.simspeed = 10000
    delivery = ucomm.deliveries.add()
    delivery.truckid = truck
    newPack = delivery.packages.add()
    newPack.packageid = pack.trackingnum
    newPack.x = pack.loc.x
    newPack.y = pack.loc.y
    lock.acquire()
    temp_seq = seq_num
    delivery.seqnum = temp_seq
    seq_num+=1
    lock.release()
    sendMSG(world_fd,ucomm.SerializeToString())
    #wait for ack
    while temp_seq not in my_seq:
        time.sleep(1)
        sendMSG(world_fd,ucomm.SerializeToString())
    print("sent world deliver")
    
def handle_truck_status(truckstatus):
    conn = connectDB()
    cur = conn.cursor()
    sql = "UPDATE my_ups_truck SET truckstatus=%s WHERE truckid=%s"
    status = 0
    if truckstatus.status == "IDLE":
        status = 1
    elif truckstatus.status == "TRAVELLING":
        status = 2
    elif truckstatus.status == "ARRIVE WAREHOUSE":
        status = 3
    elif truckstatus.status == "LOADING":
        status = 4
    else:
        status = 5
    cur.execute(sql,(status,truckstatus.truckid))
    conn.commit()
    cur.close()
    closeDB(conn)

#---------------------------helper functions
def allocate_truck(): #更新数据库里的truck status
    global my_seq
    global truck_num
    global seq_num
    global world_fd
    global truck_in_use
    ucommd = world_ups_pb2.UCommands()
    ucommd.simspeed = 10000
    temp_seq = 0
    print("[DEBUG]: allocating truck")
    print(my_seq)
    for i in range(truck_num):
        print("Entering for..")
        q = ucommd.queries.add()
        q.truckid = i
        lock.acquire()
        q.seqnum = seq_num
        temp_seq = seq_num
        seq_num+=1
        lock.release()
        print("sending truck query to world, truckid:", i)
        sendMSG(world_fd,ucommd.SerializeToString())
        while temp_seq not in my_seq: #check if last seq num is ack'ed
            print("waiting for world to response truck query")
            time.sleep(1) 
            sendMSG(world_fd,ucommd.SerializeToString())
        print("world query response received")
    #outside while, meaning db has been updated
    conn = connectDB()
    cur = conn.cursor()
    sql = "SELECT * FROM my_ups_truck"
    cur.execute(sql)
    row = cur.fetchall()
    finalid = -1
    #while finalid != -1:
    #increment = 0
    for item in row:
        truckid = item[1]
        truckstatus = item[2]
        print("truckid queried: ",truckid)
        print("truckstatus: ", truckstatus)
        available = [1,5]
        if truckstatus in available and finalid not in truck_in_use:
            finalid = truckid
            break
        #increment +=1
    cur.close()
    closeDB(conn)
    if finalid == -1: #all trucks are not available, wait for some time and try again
        time.sleep(10) #
        return allocate_truck()
    else:
        print("get truck id success")
        return finalid


def truncate_table(sstr):
    conn = connectDB()
    cur = conn.cursor()
    sql = "TRUNCATE TABLE "+ sstr
    cur.execute(sql)
    conn.commit()
    cur.close()
    closeDB(conn)

def change_simspeed(speed):
    global world_fd
    commd = world_ups_pb2.UCommands()
    commd.simspeed = speed
    sendMSG(world_fd,commd.SerializeToString())

def send_email1(trackingnum,content):
    smtp_server = "smtp.gmail.com"
    sender_email = "wangyingxu99@gmail.com"
    username = "wangyingxu99"
    password = "053534123"
    conn = connectDB()
    cur = conn.cursor()
    sql0 = "SELECT userid from my_ups_package WHERE trackingnum=%s"
    cur.execute(sql0,(trackingnum,))
    row = cur.fetchone()
    if row == None:
        return
    uid = row[0]
    if uid == None:
        return
    sql = "SELECT email from auth_user WHERE id=%s"
    cur.execute(sql,(uid,))
    row2 = cur.fetchone()
    email = row2[0]
    msga = " Package tracking number: "
    email_content = "{}{}{}".format(content,msga,trackingnum)
    if email!=None:
        '''
        subject = "UPS Package Status Change"
        body = content
        receiver = [email]
        '''
        receiver = [email]
        msg = MIMEText(email_content)
        msg['Subject'] = "UPS Package Status Change"
        msg['From']  = sender_email
        msg['To'] = email[0]
        with smtplib.SMTP(smtp_server,587) as server:
            #try:
            #server.connect(smtp_server,465)
            #server.ehlo()
            server.starttls()
            #sever.ehlo()
            server.login(username,password)
            server.sendmail(sender_email,receiver,msg.as_string())
            server.quit()
            print("Successfully sent email")
            #except:
                #print("Unable to send email")
        '''
        set_email_config(sender_email, password)
        cc_recipients = None
        bcc_recipients = None
        send_email(subject, body, receiver, cc_recipients, bcc_recipients)
        '''

#---------------------------deal with amazon
def initialize_connection_with_amazon():
    client = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        client.connect(('vcm-26766.vm.duke.edu', 9999)) #ip and port modification
        print("connected with amazon successfully")
        return client
    except socket.error:
        print("Amazon connect failed")

def send_world_info_to_amazon(worldid): #seq_num=1
    global seq_num
    global amazon_fd
    global amazon_seq
    msg_send = au_pb2.UACommand()
    msg_send.sendid.worldid = worldid
    seq = seq_num
    msg_send.sendid.seqnum = seq
    seq_num += 1
    sendMSG(amazon_fd,msg_send.SerializeToString())
    print("Sent UASendWorldId")
    inputs = [world_fd, amazon_fd]
    flag = False
    while True:
        readable, writable, exceptional = select.select(inputs,[],[])
        for s in readable:
            if s is world_fd:
                handle_world_msg()
                print("msg from world while waiting ack from amazon")
            else:
                print("[DEBUG]: received ack from amazon")
                a_seq, err, ack = handle_amazon_response()
                ''' 默认amazon连不上world会一直连,所以不报错
                for e in err:
                    if e.seqnum == seq:
                        print("Err when receiving ack from amazon, seq = ", seq)
                        break
                '''
                for a in ack:
                    if a == seq:
                        flag = True
                        ret_resp = au_pb2.UACommand()
                        ret_resp.acks.append(a_seq)
                        print("[DEBUG]: seq num received from amazon", a_seq)
                        amazon_seq.append(a_seq)
                        sendMSG(amazon_fd,ret_resp.SerializeToString())
                        print("[DEBUG]: 3rd ack sent")
        if flag == True:
            break
        time.sleep(1) #!! time needs adjustment
        sendMSG(amazon_fd,msg_send.SerializeToString()) #resend
        
def handle_amazon_response(msg=None):
    global my_seq
    global amazon_fd
    if msg is None:
        msg = recvMSG(amazon_fd)
        print("[DEBUG]: msg received: ", msg)
        resp = au_pb2.AUCommand()
        try:
            resp.ParseFromString(msg)
        except:
            print("[DEBUG]: NOT able to parse response")
        for a in resp.acks:
            my_seq.append(a)
        for e in resp.errors:
            print("[ERROR]", str(resp.errors.err), "sequence number = ", str(resp.errors.seqnum))
        return resp.seqnum, resp.errors, resp.acks

def handle_amazon_msg():
    global my_seq
    global amazon_fd
    msg = recvMSG(amazon_fd)
    comm = au_pb2.AUCommand()
    try:
        comm.ParseFromString(msg)
    except Exception as e: #probably a response
        print("Parse error", e)
    print("msg received from amazon: ")
    print(comm)
    if comm.HasField("queryupsid"):
        t1 = threading.Thread(target=do_check_upsid,args=(comm,), daemon=True)
        t1.start()
        #do_check_upsid(comm)
    else:
        '''
        #t2 = threading.Thread(target=handle_amazon_response,args=(comm,),daemon=True)
        #t2.start()
        '''
        for a in comm.acks:
            my_seq.append(a)

        pickflag = False
        tracking = []
        for pick in comm.pickup:
            pickflag = True
            tracking.append(pick.trackingnum)
            t3 = threading.Thread(target=do_pickup,args=(pick,),daemon=True)
            t3.start()
            #do_pickup(pick)
        '''
        if pickflag:
            t5 = threading.Thread(target = allocate_truck,args=(tracking,),daemon=True)
            t5.start()
        '''
        for pack in comm.packloaded:
            t4 = threading.Thread(target=do_packloaded,args=(pack,),daemon=True)
            t4.start()
            #do_packloaded(pack)
        for e in comm.errors:
            print("[ERROR]", str(comm.errors.err), "sequence number = ", str(comm.errors.seqnum))
        ''' no changeaddr?
        for chang in comm.changeaddr:
            #!!todo do change address
        '''

#---------do for amazon
def send_truck_arrived_to_amazon(packagelist,truckid):
    global seq_num
    global my_seq
    global amazon_fd
    print("[DEBUG]:entering send_truck_arrived_to_amazon")
    print(packagelist)
    ucomm = au_pb2.UACommand()
    temp_seq = 0
    for p in packagelist:
        arrive = ucomm.arrived.add()
        arrive.truckid = truckid
        arrive.trackingnum = p
        lock.acquire()
        temp_seq = seq_num
        arrive.seqnum = temp_seq
        seq_num+=1
        lock.release()
    print(ucomm)
    sendMSG(amazon_fd, ucomm.SerializeToString())
    while temp_seq not in my_seq: #wait for ack
        print("..........................")
        print("amazon fd: ", amazon_fd)
        time.sleep(1)
        sendMSG(amazon_fd,ucomm.SerializeToString())
    #更改package在数据库里的status，变为loading
    print("[DEBUG]: sent truck arrived to amazon")
    conn = connectDB()
    cur = conn.cursor()
    sql = "UPDATE my_ups_package SET packagestatus=2 WHERE trackingnum=%s"
    for p in packagelist:
        cur.execute(sql,(p,))
    conn.commit()
    cur.close()
    closeDB(conn)

def send_delievered_to_amazon(trackingnum):
    global seq_num
    global my_seq
    global amazon_fd
    print("Sending delivered to amazon")
    uacomm = au_pb2.UACommand()
    deivo = uacomm.deliverover.add()
    deivo.trackingnum = trackingnum
    lock.acquire()
    temp_seq = seq_num
    deivo.seqnum = temp_seq
    seq_num += 1
    lock.release()
    sendMSG(amazon_fd,uacomm.SerializeToString())
    while temp_seq not in my_seq:
        time.sleep(1)
        sendMSG(amazon_fd,uacomm.SerializeToString())
    send_email1(trackingnum,"Package delivered!")
    print("deivery sent!!!!!!!!!!")

def do_packloaded(pack):
    global seq_num
    global amazon_fd
    global amazon_seq
    tracking = pack.trackingnum
    truck = pack.truckid
    ama_seq = pack.seqnum
    if ama_seq in amazon_seq: #meaning handled it already
        sendACK(amazon_fd,amazon_seq)
        return
    destx = pack.loc.x
    desty = pack.loc.y
    print("package destination x: ", destx)
    print("package destination y:", desty)
    #update database
    conn = connectDB()
    cur = conn.cursor()
    sql0 = "SELECT destinationx, destinationy FROM my_ups_package WHERE trackingnum=%s"
    cur.execute(sql0,(tracking,))
    row = cur.fetchone() #check if addr has changed
    if row[0] == None and row[1] == None: #!!check: return是null的话len(row)会不会等于0
        sql = "UPDATE my_ups_package SET packagestatus=3,destinationx=%s,destinationy=%s WHERE trackingnum=%s"
        cur.execute(sql,(destx,desty,tracking))
    else: #addr already changed on ups side, keep it
        sql = "UPDATE my_ups_package SET packagestatus=3 WHERE trackingnum=%s"
        cur.execute(sql,(tracking,))
    send_email1(tracking,"Your package is loaded") #///////////
    conn.commit()
    cur.close()
    closeDB(conn)
    #send ack to amazon
    sendACK(amazon_fd,ama_seq)
    amazon_seq.append(ama_seq)
    print("finished handling packloaded")
    send_world_to_deliver(truck,pack)

def do_check_upsid(comm): #check if upsid in database, send ack/err back to amazon
    global amazon_seq
    global amazon_fd
    global seq_num
    print("[DEBUG]: check upsid")
    a_seq = comm.queryupsid.seqnum
    amazon_seq.append(a_seq)
    id = comm.queryupsid.upsid
    conn = connectDB()
    cur = conn.cursor()
    sql = "SELECT id FROM auth_user WHERE id = %s"
    cur.execute(sql,(id,))
    row = cur.fetchone()
    print('fetchone res for seq: ' , a_seq)
    exist = True
    resp_send = au_pb2.UACommand()
    if row == None:
        print("Row = None. UPS user id does not exist", str(id))
        exist = False
    closeDB(conn)
    if exist:
        print("UPS user id exists", str(id))
        resp_send.acks.append(a_seq)
    else:
        print("UPS user id does not exist", str(id))
        resp_send.acks.append(a_seq)
        error = resp_send.errors.add()
        error.err = "UPS userid not found"
        error.originseqnum = a_seq
        lock.acquire()
        error.seqnum = seq_num
        seq_num+=1
        lock.release()
    sendMSG(amazon_fd, resp_send.SerializeToString())
    print("checked upsid")

def do_pickup(pick): #tell amazon wait for longer time
    global amazon_fd
    global amazon_seq
    global seq_num
    global truck_in_use
    global truck_num
    print("[DEBUG]: handling pick up request")
    a_seq = pick.seqnum
    if a_seq in amazon_seq: #avoid repeatedly create new pickup
        print("send ACK to amazon", a_seq)
        sendACK(amazon_fd, a_seq)
        return
    print("ACK not in amazon_seq")
    amazon_seq.append(a_seq)
    descp = '' #product description
    for ap in pick.things:
        temp_str = ap.description
        cur_count = ap.count
        descp += str(temp_str)
        descp += '*' + str(cur_count) + ' '
    trackingNum = int(pick.trackingnum)
    #add warehouse to db
    conn = connectDB()
    cur = conn.cursor()
    warehouseid = int(pick.wareinfo.id)
    warehousex = int(pick.wareinfo.x)
    warehousey = int(pick.wareinfo.y)
    print("warehouseid",warehouseid)
    print("warehousex",warehousex)
    print("warehousey",warehousey)
    '''
    sql_warehouse = "SELECT * FROM my_ups_warehouse WHERE warehouseid=%s"
    cur.execute(sql_warehouse,(warehouseid,))
    row = cur.fetchall()
    print("row:",row)
    print("row length:", len(row))
    if len(row)==0:
    '''
    sqlt = "INSERT INTO my_ups_warehouse(warehouseid,warehousex,warehousey) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING"
    cur.execute(sqlt,(warehouseid,warehousex,warehousey))
    '''
    while len(truck_in_use) == truck_num:
        print("looping...")
        time.sleep(1)
    '''
    print("Entering lock")
    lock1.acquire()
    truckid = allocate_truck()
    print("allocate truck %s to pick up %s", (truckid, trackingNum))
    truck_in_use.add(truckid)
    lock1.release()
    print("leaving lock")
    print("[DEBUG]: truckid",truckid)
    print(pick)
    if pick.upsid != 0 :
        uid = int(pick.upsid)
        sql = "INSERT INTO my_ups_package(trackingnum,userid,packagestatus,truckid, description,warehouseid) VALUES (%s,%s,%s,%s,%s,%s)"
        cur.execute(sql,(trackingNum,uid,1,truckid,descp,warehouseid))
        print("1")
    else:
        sql = "INSERT INTO my_ups_package(trackingnum,packagestatus,truckid,description,warehouseid) VALUES (%s,%s,%s,%s,%s)"
        cur.execute(sql,(trackingNum,1,truckid,descp,warehouseid))
        print("2")
    print("handle pick up in db success")
    send_email1(trackingNum,"Your package is waiting for pick up") #///////
    conn.commit()
    cur.close()
    closeDB(conn)
    #send ack
    sendACK(amazon_fd,a_seq)
    print("Package add successful")
    print("sending to world: ",pick.trackingnum)
    send_pickup_to_world(truckid,warehouseid)

#------start listening
def select_listen():
    global world_fd
    global amazon_fd
    inputs = [world_fd,amazon_fd]
    while True:
        try:
            readable, writable, exceptional = select.select(inputs,[],[])
        except select.error:
            print("World disconnected. Reconnecting...")
            reconnect_to_world()
            print("World reconnected")
            inputs = [world_fd,amazon_fd] #not sure if needed
            continue
        for s in readable:
            if s is world_fd:
                print("received msg from world")
                handle_world_msg()
                #time.sleep(1) #可删
            else:
                handle_amazon_msg()
                print("received msg from amazon")
                #time.sleep(1) #可删

def main():
    global seq_num
    global truck_num
    global world_fd
    global amazon_fd
    seq_num=0
    truncate_table("my_ups_truck")
    truncate_table("my_ups_warehouse")
    truncate_table("my_ups_package")
    world_fd = initialize_connection_with_world()
    worldid = initialize_world() #1,2
    change_simspeed(10000)
    amazon_fd  = initialize_connection_with_amazon()
    print("amazon_fd: ", amazon_fd)
    send_world_info_to_amazon(worldid)
    select_listen()

if __name__ == "__main__":
    main()


