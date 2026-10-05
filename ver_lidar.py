"""
Corre esto EN LA PC. Se conecta a lidar_stream.py, que ya esta corriendo en la Pi
en el puerto 5001 y envia cada escaneo como una linea JSON: [[quality, angle, distance], ...]
Instalar dependencia: pip install matplotlib numpy
"""
import socket, json
import numpy as np
import matplotlib.pyplot as plt

PI_IP = "10.39.220.138"  # misma IP de la Pi usada para la camara
PORT = 5001
MAX_DISTANCE_MM = 6000  # alcance maximo a mostrar en el grafico


def read_lines(sock):
    buf = b""
    while True:
        chunk = sock.recv(65536)
        if not chunk:
            return
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            if line:
                yield line


def main():
    s = socket.socket()
    s.connect((PI_IP, PORT))
    print("Conectado al lidar, mostrando escaneo... cierra la ventana para salir")

    fig = plt.figure()
    ax = fig.add_subplot(111, projection="polar")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_rmax(MAX_DISTANCE_MM)
    scatter = ax.scatter([], [], s=5)

    plt.ion()
    plt.show()

    for line in read_lines(s):
        if not plt.fignum_exists(fig.number):
            break

        scan = json.loads(line.decode("utf-8"))
        if scan:
            angles = np.radians([p[1] for p in scan])
            distances = [p[2] for p in scan]
            scatter.set_offsets(np.column_stack([angles, distances]))

        fig.canvas.draw_idle()
        plt.pause(0.001)

    s.close()


if __name__ == "__main__":
    main()
