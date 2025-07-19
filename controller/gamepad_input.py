import pygame

BASE_INPUT_DICT = {"lx": 0, "ly": 0, "camera_horiz": 0, "camera_vert": 0}


def get_input(j: pygame.joystick.JoystickType, round_amount: int = 3):
    return {
        "lx": round(j.get_axis(0), round_amount),
        "ly": round(j.get_axis(1), round_amount),
        "cam_horiz": j.get_hat(0)[0],
        "cam_vert": j.get_hat(0)[1],
    }
