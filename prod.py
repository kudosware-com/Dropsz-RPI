import cv2
from imutils.video import VideoStream
from pyzbar import pyzbar
import imutils
import requests
# import RPi.GPIO as GPIO
import time
import datetime
from datetime import timedelta
import socket
 
# GPIO.setmode(GPIO.BOARD)
# GPIO.setup(36,GPIO.OUT)
# GPIO.output(36,GPIO.HIGH)
 
hostname = socket.gethostname()   
IPAddr = socket.gethostbyname(hostname)
 
url = "https://us-central1-dropsz.cloudfunctions.net/getUidfromArduino"
# set up camera object
while True:
    try:
        cap = VideoStream(src=0).start()
        time.sleep(0.2)
        # QR code detection object
        detector = cv2.QRCodeDetector()
        qrTrack = {}
        while True:
            # get the image
            img = cap.read()
            img = imutils.resize(img,width=400)
            barcodes = pyzbar.decode(img)
            data = ""
    
            if len(barcodes) > 0:
                data = barcodes[0].data.decode("utf-8")

            data_to_be_sent = {'uid':data,'ip':IPAddr}
            if data:
                curr_time = datetime.datetime.now()
                if (data not in qrTrack.keys()) or ((datetime.datetime.now() - qrTrack[data][1]).total_seconds() > 3):
                    for k, v in list(qrTrack.items()):
                        if k == data:
                            continue
                        if (datetime.datetime.now() - qrTrack[k][1]).total_seconds() > 360:
                            del qrTrack[k]
                    if data not in qrTrack.keys():
                        qrTrack[data] = [None,datetime.datetime(2009, 10, 5, 18, 00)]

                    try:
                        res = requests.post(url,json=data_to_be_sent,headers={'Content-Type':'application/json'})
                    
                    except requests.exceptions.RequestException as e:
                        print("request error")

                    print("data found: ", data)
                    res_json = res.json()
                    if res_json["received"] == "not subscribed":

                        qrTrack[data][0] = "unsubscribed"
                        
                        # GPIO.output(36,GPIO.LOW)
                        time.sleep(7)
                        # GPIO.output(36,GPIO.HIGH)
                        print('running  motor, unsubscribed user amount will be deducted')
                        data_to_be_sent["type"] = "unsubscribed"
                        data_to_be_sent["status"] = "success"
                        ack_url = "https://us-central1-dropsz.cloudfunctions.net/deductBalanceAfterRunningMotor"
                        try:
                            res = requests.post(ack_url,json=data_to_be_sent,headers={'Content-Type':'application/json'})
                        except requests.exceptions.RequestException as e:
                            print("request error")

                        qrTrack[data][1] = datetime.datetime.now()                    

    
                    elif res_json["received"] == "subscribed":

                        if qrTrack[data][1] == None or (datetime.datetime.now() - qrTrack[data][1]).total_seconds() > 300:
                            
                            # GPIO.output(36,GPIO.LOW)
                            time.sleep(7)
                            # GPIO.output(36,GPIO.HIGH)
                            print('running motor, subscribed user no amount will be deducted')
                            data_to_be_sent["type"] = "subscribed"
                            data_to_be_sent["status"] = "success"
                            
                            ack_url = "https://us-central1-dropsz.cloudfunctions.net/deductBalanceAfterRunningMotor"
                            try:
                                res = requests.post(ack_url,json=data_to_be_sent,headers={'Content-Type':'application/json'}) 
                            except requests.exceptions.RequestException as e:
                                print("request error")

                            qrTrack[data][1] = datetime.datetime.now()
                        else:
                            data_to_be_sent["type"] = "subscribed"
                            data_to_be_sent["status"] = "5 mins"
                            ack_url = "https://us-central1-dropsz.cloudfunctions.net/deductBalanceAfterRunningMotor"
                            res = requests.post(ack_url,json=data_to_be_sent,headers={'Content-Type':'application/json'})
                            print("wait for 5 minutes, as you are subscribed user")

                        qrTrack[data][0] = "subscribed"    

                    else:
                        data_to_be_sent["type"] = "unsubscribed"
                        data_to_be_sent["status"] = "less amount"
                        ack_url = "https://us-central1-dropsz.cloudfunctions.net/deductBalanceAfterRunningMotor"
                        try:
                            res = requests.post(ack_url,json=data_to_be_sent,headers={'Content-Type':'application/json'})
                        except requests.exceptions.RequestException as e:
                            print("request error")

                        print("Cannot run motor, user doesn't have enough balance")
                else:

                    data_to_be_sent["status"] = "failed"
                    data_to_be_sent["type"] = qrTrack[data][0]
                    ack_url = "https://us-central1-dropsz.cloudfunctions.net/deductBalanceAfterRunningMotor"
                    try:
                        res = requests.post(ack_url,json=data_to_be_sent,headers={'Content-Type':'application/json'}) 
                    except requests.exceptions.RequestException as e:
                        print("request error")

                    if(qrTrack[data][0] == "subscribed"):
                        print("wait for {0} minutes".format((300 - (datetime.datetime.now() - qrTrack[data][1]).total_seconds())/60))

                    elif(qrTrack[data][0] == "unsubscribed"):
                        print("wait for {0} minutes".format((30 - (datetime.datetime.now() - qrTrack[data][1]).total_seconds())/60))

                    
            cv2.imshow("code detector", img)
            if(cv2.waitKey(1) == ord("q")):
                break
        cap.release()
        cv2.destroyAllWindows()
    
    except AttributeError:
        try:
            s = smtplib.SMTP('smtp.gmail.com',587)
            s.starttls()
            s.login("enquiry.infabrands@gmail.com","Pa$$@Enquiry")
            msg = EmailMessage("Kiosk with IP address {IpAddr} and name {hostname} is shutted down")
            msg.set_content()
            msg['Subject'] = "Found issue in Kiosk"
            msg['from'] = "enquiry.infabrands@gmail.com"
            msg['To'] = "mohit.joshi@kudosware.com"
            s.send_message(msg)
            s.quit()

        except:
            print("Error Sending mail")