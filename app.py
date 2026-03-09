from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from io import BytesIO
import base64

app = Flask(__name__)

trajectory = []

DEPTH_SCALE = 900
FPS = 30

# HSV calibration
lh,ls,lv = 0,100,100
uh,us,uv = 20,255,255

# smoothing
radius_smooth = None
depth_smooth = None

# -------------------------
# Kalman Filter
# -------------------------

kalman = cv2.KalmanFilter(4,2)

kalman.measurementMatrix = np.array([
[1,0,0,0],
[0,1,0,0]],np.float32)

kalman.transitionMatrix = np.array([
[1,0,1,0],
[0,1,0,1],
[0,0,1,0],
[0,0,0,1]],np.float32)

kalman.processNoiseCov = np.eye(4,dtype=np.float32)*0.02


# -------------------------
# Ball detection
# -------------------------

def detect_ball(img):

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
# Bounce segmentation
# -------------------------

def segment_bounces(Z):

    segments=[]
    start=0

    vel=np.gradient(Z)

    for i in range(1,len(vel)-1):

        if vel[i-1] < 0 and vel[i+1] > 0:
            segments.append((start,i))
            start=i

    segments.append((start,len(Z)))

    return segments


# -------------------------
# Plot trajectory
# -------------------------

def plot_trajectory():

    traj=np.array(trajectory)

    X=traj[:,0]
    Y=traj[:,2]
    Z=traj[:,1]

    Z -= Z.min()
    X -= np.mean(X)
    Y -= Y.min()

    t=np.arange(len(Z))/FPS

    segments = segment_bounces(Z)

    fig=plt.figure(figsize=(8,6))
    ax=fig.add_subplot(111,projection="3d")

    ax.scatter(X,Y,Z,s=12)

    for s,e in segments:

        if e-s < 6:
            continue

        t_seg=t[s:e]

        coeff=np.polyfit(t_seg,Z[s:e],2)

        Z_fit=np.polyval(coeff,t_seg)

        ax.plot(X[s:e],Y[s:e],Z_fit,color="red",linewidth=2)

    ax.set_xlabel("Sideways")
    ax.set_ylabel("Depth")
    ax.set_zlabel("Height")

    ax.set_title("Tracked Multi-Bounce Trajectory")

    buf=BytesIO()
    plt.savefig(buf,format="png")
    buf.seek(0)

    img=base64.b64encode(buf.read()).decode("utf-8")

    return img


# -------------------------
# Process uploaded video
# -------------------------

@app.route("/process_video",methods=["POST"])
def process_video():

    global trajectory

    trajectory=[]

    file=request.files["video"]

    temp_path="temp_video.mp4"

    file.save(temp_path)

    cap=cv2.VideoCapture(temp_path)

    while True:

        ret,frame=cap.read()

        if not ret:
            break

        ball=detect_ball(frame)

        if ball:

            x,y,r = ball

            measurement = np.array([[np.float32(x)],
                                    [np.float32(y)]])

            kalman.correct(measurement)
            prediction = kalman.predict()

            px=int(prediction[0])
            py=int(prediction[1])

            depth = DEPTH_SCALE / r

            trajectory.append([px,-py,depth])

    cap.release()

    img=plot_trajectory()

    return jsonify({"plot":img})


# -------------------------
# Rocket simulation
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


# -------------------------
# Run server
# -------------------------

if __name__=="__main__":

    app.run(host="0.0.0.0",port=10000)