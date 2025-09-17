import cv2
from mjpeg_streamer import MjpegServer, Stream


def setup_camera():

    capture = cv2.VideoCapture(0)

    capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    WIDTH = 854
    HEIGHT = 480
    # Optionally set resolution and FPS explicitly
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    capture.set(cv2.CAP_PROP_FPS, 20)

    # Optionally set resolution and FPS explicitly
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    capture.set(cv2.CAP_PROP_FPS, 20)

    server = MjpegServer("0.0.0.0", 8080)
    stream = Stream(name="onboard-camera", size=(WIDTH, HEIGHT), quality=40, fps=20)

    server.add_stream(stream)
    server.start()

    try:
        while True:
            ret, frame = capture.read()
            if not ret:
                break
            frame = cv2.rotate(frame, cv2.ROTATE_180)
            stream.set_frame(frame)

    except KeyboardInterrupt:
        print("Stopping stream...")
    finally:
        server.stop()
        capture.release()


if __name__ == "__main__":
    setup_camera()
