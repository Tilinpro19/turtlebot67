"""
Corre esto EN LA RASPBERRY PI (donde esta conectado el RPLIDAR A1M8 por USB).
Instalar dependencia en la Pi: pip install rplidar-roboticia
"""
import socket, struct, json
from rplidar import RPLidar

PORT = 5001
LIDAR_SERIAL_PORT = "/dev/ttyUSB0"  # ajustar si el lidar aparece en otro puerto


def main():
    lidar = RPLidar(LIDAR_SERIAL_PORT)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", PORT))
    server.listen(1)
    print(f"Esperando conexion en el puerto {PORT}...")

    conn, addr = server.accept()
    print(f"Cliente conectado: {addr}")

    try:
        for scan in lidar.iter_scans():
            points = [(angle, distance) for _, angle, distance in scan]
            data = json.dumps(points).encode("utf-8")
            conn.sendall(struct.pack(">I", len(data)) + data)
    except (KeyboardInterrupt, BrokenPipeError, ConnectionResetError):
        pass
    finally:
        lidar.stop()
        lidar.stop_motor()
        lidar.disconnect()
        conn.close()
        server.close()


if __name__ == "__main__":
    main()
