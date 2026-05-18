import argparse
import serial
import time
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("port", help="COM port, e.g. COM6")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--log", default="startup_log.txt")
    args = parser.parse_args()

    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Opening {args.port} at {args.baud} baud...")
    print(f"Logging to {log_path.resolve()}")
    print("Press Ctrl+C to stop.\n")

    with serial.Serial(
        port=args.port,
        baudrate=args.baud,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False,
    ) as ser, log_path.open("w", encoding="utf-8") as log:
        time.sleep(0.5)

        while True:
            data = ser.readline()
            if not data:
                continue

            text = data.decode("utf-8", errors="replace").rstrip()
            print(text)
            log.write(text + "\n")
            log.flush()

if __name__ == "__main__":
    main()
