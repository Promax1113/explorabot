import pygame



def get_input(j: pygame.joystick.JoystickType):
    return {
        "lx": round(j.get_axis(0), 3),
        "ly": round(j.get_axis(1), 3),
        "camera_horiz": j.get_hat(0)[0],
        "camera_vert": j.get_hat(0)[1]
    }
