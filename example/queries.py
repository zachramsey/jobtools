from jobtools.utils.patterns import AND, OR


LANG = OR(["C++", "Python"])

Q1 = AND([OR(["Computer Engineer", "Computer Engineering"]), LANG])
Q2 = AND([OR(["Research Engineer", "Research Scientist"]), LANG])
Q3 = AND([OR(["Software Engineer", "Software Developer"]), LANG])
Q4 = AND([OR(["Data Scientist", "Data Science"]), LANG])
Q5 = AND([OR(["Embedded Software", "Embedded Systems", "Embedded"]), LANG])
Q6 = AND([OR(["IoT", "MCU", "Microcontroller", "I2C"]), LANG])
Q7 = AND([OR(["Firmware Engineer", "Firmware Developer", "Firmware"]), LANG])
Q8 = AND([OR(["Robotics", "Robotic", "Robots", "Robot", "ROS2", "RTOS"]), LANG])
Q9 = AND([OR(["Autonomous Vehicle", "Self-Driving", "Autonomous", "Autonomy"]), LANG])
Q10 = AND([OR(["Reinforcement Learning", "Imitation Learning"]), LANG])
Q11 = AND([OR(["Machine Learning", "Deep Learning", "Neural Network"]), LANG])
Q12 = AND([OR(["Supervised Learning", "Unsupervised Learning",
               "Self-Supervised Learning"]), LANG])
Q13 = AND([OR(["Computer Vision", "Object Detection", "OpenCV",
               "Signal Processing", "Image Processing"]), LANG])
Q14 = AND([OR(["ONNX", "TensorRT", "Edge AI", "TinyML", "Edge Computing",
               "Embedded AI", "Edge Device"]), LANG])

# New Grad Group
NG1 = ["New Grad", "New Graduate", "New College", "New University",
       "Recent Grad", "Recent Graduate", "Recent College",
       "Recent University", "Entry Level", "Entry-Level"]
NG = AND([OR(NG1), LANG])

# Computer Engineer Group
CE1 = ["Computer Engineer", "Computer Engineering"]
CE = AND([OR(CE1), LANG])

# Embedded Systems Group
ES1 = ["Embedded Software", "Embedded System", "Embedded", "Firmware", "I2C"]
ES = AND([OR(ES1), LANG])

# Robotic Systems Group
RS1 = ["Robotics", "Robotic", "Robots", "Robot", "ROS2", "RTOS"]
RS = AND([OR(RS1), LANG])

# Computer Vision Group
CV1 = ["Computer Vision", "Object Detection", "OpenCV", "Signal Processing",
       "Image Processing"]
CV = AND([OR(CV1), "PyTorch", LANG])

# Reinforcement Learning Group
RL1 = ["Reinforcement Learning", "Imitation Learning", "Behavior", "Planning",
       "Trajectory", "Autonomous", "Autonomy", "Self-Driving"]
RL = AND([OR(RL1), "PyTorch", LANG])

# Machine Learning Group
ML1 = ["Machine Learning", "Supervised Learning", "Unsupervised Learning",
       "Self-Supervised Learning", "Deep Learning",  "Neural Network"]
ML = AND([OR(ML1), "PyTorch", LANG])


SEARCH_STRINGS = {
    # "Q1": Q1,
    # "Q2": Q2,
    # "Q3": Q3,
    # "Q4": Q4,
    # "Q5": Q5,
    # "Q6": Q6,
    # "Q7": Q7,
    # "Q8": Q8,
    # "Q9": Q9,
    # "Q10": Q10,
    # "Q11": Q11,
    # "Q12": Q12,
    # "Q13": Q13,
    # "Q14": Q14,
#     "NG": NG,
    "CE": CE,
    "ES": ES,
    "RS": RS,
    # "CV": CV,
    "RL": RL,
    "ML": ML,
}
