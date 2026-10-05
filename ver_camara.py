import socket, struct, cv2, numpy as np

PI_IP = "10.39.220.138"  # confirma la IP actual de la Pi
PORT = 5000

s = socket.socket()
s.connect((PI_IP, PORT))
print("Conectado, mostrando video... presiona 'q' para salir")

while True:
    size_data = s.recv(4)
    if len(size_data) < 4:
        break
    size = struct.unpack(">I", size_data)[0]
    data = b""
    while len(data) < size:
        chunk = s.recv(size - len(data))
        if not chunk:
            break
        data += chunk
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    cv2.imshow("OAK-D Live", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
s.close()
