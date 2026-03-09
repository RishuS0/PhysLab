from flask import Flask, render_template, Response, jsonify, request
import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import threading
import os

app = Flask(__name__)

PHONE_IP = "192.168.1.4"
VIDEO_URL = f"http://{PHONE_IP}:8080/video"

frame = None
cap = None
lock = threading.Lock()

tracking = False
trajectory = []

DEPTH_SCALE = 900
FPS = 30

lh,ls,lv = 0,100,100
uh,us,uv = 20,255,255

radius_smooth = None
depth_smooth = None

last_position = None
MAX_JUMP = 120


# -------------------------
# Kalman Filter
# -------------------------

kalman = cv2.KalmanFilter(4,2)

kalman.measurementMatrix = np.array([[1,0,0,0],[0,1,0,0]],np.float32)

kalman.transitionMatrix = np.array([
[1,0,1,0],
[0,1,0,1],
[0,0,1,0],
[0,0,0,1]],np.float32)

kalman.processNoiseCov = np.eye(4,dtype=np.float32)*0.02


# -------------------------
# Camera Thread
# -------------------------

def camera_loop():

    global frame,cap

    cap = cv2.VideoCapture(VIDEO_URL)

    while True:

        ret,img = cap.read()

        if not ret:
            continue

        with lock:
            frame = img.copy()


# -------------------------
# Ball detection
# -------------------------

def detect_ball(img):

    global last_position

    hsv = cv2.cvtColor(img,cv2.COLOR_BGR2HSV)

    lower = np.array([lh,ls,lv])
    upper = np.array([uh,us,uv])

    mask = cv2.inRange(hsv,lower,upper)

    kernel = np.ones((5,5),np.uint8)

    mask = cv2.morphologyEx(mask,cv2.MORPH_OPEN,kernel)
    mask = cv2.morphologyEx(mask,cv2.MORPH_CLOSE,kernel)

    contours,_ = cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

    best=None
    best_score=0

    for c in contours:

        area = cv2.contourArea(c)

        if area < 150:
            continue

        (x,y),r = cv2.minEnclosingCircle(c)

        peri = cv2.arcLength(c,True)

        if peri == 0:
            continue

        circularity = 4*np.pi*area/(peri*peri)

        if circularity < 0.6:
            continue

        score = area * circularity

        if score > best_score:

            best_score = score
            best = (int(x),int(y),int(r))

    return best


# -------------------------
# Video Stream
# -------------------------

def video_stream():

    global frame,tracking,trajectory

    while True:

        with lock:

            if frame is None:
                continue

            img = frame.copy()

        ball = detect_ball(img)

        if ball:

            x,y,r = ball

            measurement = np.array([[np.float32(x)],[np.float32(y)]])

            kalman.correct(measurement)
            prediction = kalman.predict()

            px=int(prediction[0])
            py=int(prediction[1])

            cv2.circle(img,(px,py),5,(0,255,0),-1)

            if tracking:

                trajectory.append([px,-py,r])

        ret,buffer=cv2.imencode(".jpg",img)

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n'+buffer.tobytes()+b'\r\n')


# -------------------------
# Plot trajectory
# -------------------------

def plot_trajectory():

    traj=np.array(trajectory)

    X=traj[:,0]
    Z=traj[:,1]

    fig=plt.figure()

    ax=fig.add_subplot(111)

    ax.plot(X,Z)

    ax.set_xlabel("Horizontal")
    ax.set_ylabel("Vertical")

    buf=BytesIO()

    plt.savefig(buf,format="png")

    buf.seek(0)

    img=base64.b64encode(buf.read()).decode("utf-8")

    return img


# -------------------------
# Rocket Simulation
# -------------------------

@app.route("/simulate",methods=["POST"])
def simulate():

    data=request.json

    thrust=float(data["thrust"])
    mass=float(data["mass"])
    fuel=float(data["fuel"])
    burn=float(data["burn"])
    drag=float(data["drag"])
    viscosity=float(data["viscosity"])
    angle=float(data["angle"])

    g=9.81
    rho=1.225
    area=0.3
    dt=0.05

    x=y=0
    vx=vy=0

    X=[]
    Y=[]

    while y>=0:

        total_mass=mass+fuel

        if fuel>0:
            fuel-=burn*dt

        v=np.sqrt(vx**2+vy**2)

        drag_force=0.5*rho*drag*area*v**2

        thrust_x=thrust*np.cos(np.radians(angle))
        thrust_y=thrust*np.sin(np.radians(angle))

        ax=(thrust_x)/total_mass
        ay=(thrust_y)/total_mass - g

        vx+=ax*dt
        vy+=ay*dt

        x+=vx*dt
        y+=vy*dt

        X.append(x)
        Y.append(y)

        if len(X)>10000:
            break

    fig,ax=plt.subplots()

    ax.plot(X,Y)

    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("Altitude (m)")
    ax.set_title("Rocket Trajectory")

    buf=BytesIO()
    plt.savefig(buf,format="png")
    buf.seek(0)

    img=base64.b64encode(buf.read()).decode("utf-8")

    return jsonify({"plot":img})


# -------------------------
# Routes
# -------------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/simulator")
def simulator():
    return render_template("simulator.html")


@app.route("/video")
def video():
    return Response(video_stream(),
    mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/start_camera")
def start_camera():

    threading.Thread(target=camera_loop,daemon=True).start()

    return "ok"


@app.route("/start_tracking")
def start_tracking():

    global tracking,trajectory

    trajectory=[]
    tracking=True

    return "ok"


@app.route("/stop_tracking")
def stop_tracking():

    global tracking

    tracking=False

    img=plot_trajectory()

    return jsonify({"plot":img})


if __name__=="__main__":

    port=int(os.environ.get("PORT",10000))

    app.run(host="0.0.0.0",port=port)