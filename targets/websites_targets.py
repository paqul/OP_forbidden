import random

target_1 = "https://www.youtube.com/watch?v=ULjo6JaFTWg"
target_2 = "https://www.youtube.com/watch?v=xKZBc6i2mLg"
target_3 = "https://www.youtube.com/watch?v=P4BVmrahsDk"
target_4 = "https://www.youtube.com/watch?v=8bQWDdARrlU"
target_5 = "https://www.youtube.com/watch?v=_WvXe61Grgo"
target_6 = "https://www.youtube.com/watch?v=wNYFWO2WbRI"
# target_7
# target_8
# target_9
# target_10
# target_11
# target_13
# target_14
# target_15
# target_16

targets = [target_1, target_2, target_3, target_4, target_5, target_6]


def get_random_target() -> str:
    return random.choice(targets)