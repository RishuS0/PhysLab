# PhysLab – Optical Trajectory Tracker & Rocket Simulator

PhysLab is a web-based physics experiment platform that includes:

1. **Optical Ball Trajectory Tracker**
2. **Rocket Trajectory Simulator**

The system is built using **Flask, OpenCV, NumPy, and Matplotlib**, and can be deployed publicly using **Render**.

---

# Features

## 1. Optical Ball Tracker

Tracks the motion of a ball in real-time using computer vision.

**Techniques used**

- HSV color segmentation
- Morphological filtering
- Contour detection
- Circularity filtering
- Kalman filtering for motion smoothing
- Trajectory reconstruction
- Real-time video streaming using Flask

**Capabilities**

- Live camera feed
- Adjustable HSV color calibration
- Start / stop trajectory tracking
- Automatic trajectory plotting

---

## 2. Rocket Trajectory Simulator

A physics-based simulator for visualizing rocket flight trajectories.

Users can change physical parameters using sliders and generate the trajectory instantly.

**Adjustable parameters**

- Rocket mass
- Fuel mass
- Burn rate
- Thrust
- Drag coefficient
- Air viscosity factor
- Launch angle

The simulation uses basic rocket physics including:

- Newton's second law
- Gravity
- Aerodynamic drag
- Variable rocket mass due to fuel burn

The resulting trajectory is generated dynamically and displayed as a plot.

---

# Project Structure
