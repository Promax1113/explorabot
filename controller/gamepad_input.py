import pygame

BASE_INPUT_DICT = {"lx": 0, "ly": 0, "cam_horiz": 0, "cam_vert": 0}


def get_gamepad_input(j: pygame.joystick.JoystickType, round_amount: int = 3):
    return {
        "lx": round(j.get_axis(0), round_amount),
        "ly": round(j.get_axis(1), round_amount),
        "cam_horiz": j.get_hat(0)[0],
        "cam_vert": j.get_hat(0)[1],
    }


def get_keyboard_input():
    keys = pygame.key.get_pressed()
    return {
        "up": True if keys[pygame.K_UP] or keys[pygame.K_w] else False,
        "down": True if keys[pygame.K_DOWN] or keys[pygame.K_s] else False,
        "left": True if keys[pygame.K_LEFT] or keys[pygame.K_a] else False,
        "right": True if keys[pygame.K_RIGHT] or keys[pygame.K_d] else False,
        "c_up": True if keys[pygame.K_i] else False,
        "c_left": True if keys[pygame.K_j] else False,
        "c_down": True if keys[pygame.K_k] else False,
        "c_right": True if keys[pygame.K_l] else False,
    }
