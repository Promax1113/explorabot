import cv2
from mjpeg_streamer import MjpegServer, Stream

def setup_camera():


    capture = cv2.VideoCapture(0)
    

    capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

    # Optionally set resolution and FPS explicitly
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    capture.set(cv2.CAP_PROP_FPS, 30)

    # Optionally set resolution and FPS explicitly
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    capture.set(cv2.CAP_PROP_FPS, 30)


    server = MjpegServer("127.0.0.1", 8080)
    stream = Stream(name="onboard-camera", size=(1280, 720), quality=70, fps=30)

    server.add_stream(stream)
    server.start()

    try:
        while True:
            ret, frame = capture.read()
            if not ret:
                break

            stream.set_frame(frame)

    except KeyboardInterrupt:
        print("Stopping stream...")
    finally:
        server.stop()
        capture.release()

if __name__ == "__main__":
    setup_camera()
