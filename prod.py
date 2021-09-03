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
import smtplib
from email.message import EmailMessage

# GPIO.setmode(GPIO.BOARD)
# GPIO.setup(36,GPIO.OUT)
# GPIO.output(36,GPIO.HIGH)

# Get IP address (for getting location of kiosk)
hostname = socket.gethostname()
IPAddr = socket.gethostbyname(hostname)

url = "https://us-central1-dropsz.cloudfunctions.net/getUidfromArduino"
fl = False


def ValidateUserAndOperate(data, qrTrack, data_to_be_sent):
    curr_time = datetime.datetime.now()

    # Check if QR code is new and haven't been seen in last 3 seconds
    if (data not in qrTrack.keys()) or ((datetime.datetime.now() - qrTrack[data][1]).total_seconds() > 3):
        for k, v in list(qrTrack.items()):
            if k == data:
                continue
            # Remove all QR code data which has aged more than 6 mins
            if (datetime.datetime.now() - qrTrack[k][1]).total_seconds() > 360:
                del qrTrack[k]

        if data not in qrTrack.keys():
            qrTrack[data] = [None, datetime.datetime(2009, 10, 5, 18, 00)]
            try:
                # Send Post request to know the status of user
                res = requests.post(url, json=data_to_be_sent, headers={
                                    'Content-Type': 'application/json'})

            except requests.exceptions.RequestException as e:
                print("request error")

            print("data found: ", data)
            res_json = res.json()

            if res_json["received"] == "not subscribed":
                # Turn on kiosk
                qrTrack[data][0] = "unsubscribed"
                # GPIO.output(36,GPIO.LOW)
                # time.sleep(7)
                # GPIO.output(36,GPIO.HIGH)
                print('running  motor, unsubscribed user amount will be deducted')

                # Acknowledgement info.
                data_to_be_sent["type"] = "unsubscribed"
                data_to_be_sent["status"] = "success"
                ack_url = "https://us-central1-dropsz.cloudfunctions.net/deductBalanceAfterRunningMotor"
                try:
                    res = requests.post(ack_url, json=data_to_be_sent, headers={
                                        'Content-Type': 'application/json'})
                except requests.exceptions.RequestException as e:
                    print("request error")

                    # Update time it for future validations
                qrTrack[data][1] = datetime.datetime.now()

            elif res_json["received"] == "subscribed":
                # check if subscribed user is using kiosk again within 5 mins
                if qrTrack[data][1] == None or (datetime.datetime.now() - qrTrack[data][1]).total_seconds() > 300:
                    # Turn on Kiosk
                    # GPIO.output(36,GPIO.LOW)
                    # time.sleep(7)
                    # GPIO.output(36,GPIO.HIGH)
                    print('running motor, subscribed user no amount will be deducted')

                    # Acknowledgement info.
                    data_to_be_sent["type"] = "subscribed"
                    data_to_be_sent["status"] = "success"

                    ack_url = "https://us-central1-dropsz.cloudfunctions.net/deductBalanceAfterRunningMotor"
                    try:
                        res = requests.post(ack_url, json=data_to_be_sent, headers={
                                            'Content-Type': 'application/json'})
                    except requests.exceptions.RequestException as e:
                        print("request error")
                    # Update time it for future validations
                    qrTrack[data][1] = datetime.datetime.now()
                else:
                    # User is using Kiosk before 5 mins
                    data_to_be_sent["type"] = "subscribed"
                    data_to_be_sent["status"] = "5 mins"
                    ack_url = "https://us-central1-dropsz.cloudfunctions.net/deductBalanceAfterRunningMotor"
                    res = requests.post(ack_url, json=data_to_be_sent, headers={
                                        'Content-Type': 'application/json'})
                    print("wait for 5 minutes, as you are subscribed user")

                    # Store user type for faster response
                    qrTrack[data][0] = "subscribed"

            else:
                # If user is unscubscribed and also user doesn't have enough balance in wallet
                data_to_be_sent["type"] = "unsubscribed"
                data_to_be_sent["status"] = "less amount"
                ack_url = "https://us-central1-dropsz.cloudfunctions.net/deductBalanceAfterRunningMotor"
                try:
                    res = requests.post(ack_url, json=data_to_be_sent, headers={
                                        'Content-Type': 'application/json'})
                except requests.exceptions.RequestException as e:
                    print("request error")

                print("Cannot run motor, user doesn't have enough balance")
        else:
            # Detected in less than 3 seconds, Send Acknowledgement
            data_to_be_sent["status"] = "failed"
            data_to_be_sent["type"] = qrTrack[data][0]
            ack_url = "https://us-central1-dropsz.cloudfunctions.net/deductBalanceAfterRunningMotor"
            try:
                res = requests.post(ack_url, json=data_to_be_sent, headers={
                                    'Content-Type': 'application/json'})
            except requests.exceptions.RequestException as e:
                print("request error")

            # Print the remaining time user has to wait
            if(qrTrack[data][0] == "subscribed"):
                print("wait for {0} minutes".format(
                    (300 - (datetime.datetime.now() - qrTrack[data][1]).total_seconds())/60))

            elif(qrTrack[data][0] == "unsubscribed"):
                print("wait for {0} minutes".format(
                    (30 - (datetime.datetime.now() - qrTrack[data][1]).total_seconds())/60))


# Try to acquire camera
def setup():
    while True:
        try:
            # set up camera object
            cap = VideoStream(src=0).start()
            time.sleep(0.2)

            # QR code detection object
            detector = cv2.QRCodeDetector()
            qrTrack = {}
            while True:

                # get the image
                img = cap.read()
                img = imutils.resize(img, width=400)
                barcodes = pyzbar.decode(img)
                data = ""

                if len(barcodes) > 0:
                    data = barcodes[0].data.decode("utf-8")

                data_to_be_sent = {'uid': data, 'ip': IPAddr}
                if data:
                    ValidateUserAndOperate(data, qrTrack, data_to_be_sent)

                cv2.imshow("code detector", img)
                if(cv2.waitKey(1) == ord("q")):
                    fl = True
                    break
            # Release camera and destroy all the windows created by Program
            if(fl == True):
                cv2.destroyAllWindows()
                break

        # Send mail if camera is not working with IP
        except AttributeError:
            try:
                s = smtplib.SMTP('smtp.gmail.com', 587)
                s.starttls()
                s.login("email", "password")
                msg = EmailMessage(
                    "Kiosk with IP address {IpAddr} and name {hostname} is shutted down")
                msg.set_content()
                msg['Subject'] = "Found issue in Kiosk"
                msg['from'] = "email"
                msg['To'] = "email"
                s.send_message(msg)
                s.quit()

            except:
                print("Error Sending mail")


if __name__ == '__main__':
    setup()
