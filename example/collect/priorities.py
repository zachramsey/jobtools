
high_priority = ["PyTorch", "Pandas", "Scikit-learn", "NumPy",
                 "Reinforcement Learning", "Embedded System",
                 "Embedded Software", "MCU", "Microcontroller",
                 "Robotic", "Autonomous", "Autonomy"]

mid_priority = ["Linux", "Shell", "Bash", "Algorithm", "Data Structure",
                "Statistic", "Matrix", "Imitation Learning", "Deep Learning",
                "Unsupervised Learning", "Self-Supervised Learning", "NumPy",
                "Machine Learning", "Microprocessor", "IoT", "Optimal Control",
                "DQN", "A3C", "TD3", "DDPG", "Q-Learning", "Policy Gradient",
                "Actor-Critic"]

low_priority = ["LaTeX", "Git", "OOP", "Object-Oriented", "Neural Network",
                "Supervised Learning", "Computer Vision", "Firmware", "UART",
                "I2C", "CMake", "TenserFlow", "Keras", "Jax", "RTOS"]

no_priority = [r"C\+\+", "Python", "PostgreSQL", "MySQL", "CI/CD", "DevOps",
               "Agile", "Scrum"]

deprioritize = ["Kubernetes", "Docker", "AWS", "Azure", "GCP", "Hadoop",
                "Spark", "Tableau", "PowerBI", "Scada", "Siemens", "FPGA",
                "PCB", "PLC", "LLM", "NLP", "VLM"]

# Mapping of priority levels to terms
KEYWORD_VALUE_MAP = {
    3: high_priority,
    2: mid_priority,
    1: low_priority,
    0: no_priority,
    -1: deprioritize
}

STATE_RANK_ORDER = ["WA", "OR", "CA", "MA", "TX", "MD", "VA", "NY"]
