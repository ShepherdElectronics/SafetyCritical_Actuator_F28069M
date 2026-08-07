import argparse
import serial
import threading
import time
from pathlib import Path
from datetime import datetime

DEFAULT_COMMANDS = [
    ("RST,0", 2.0, "Reset to READY / safe output"),

    ("EN,250,1", 2.0, "Run at 25 percent PWM; capture 25 percent duty"),
    ("DIS,2", 2.0, "Disable after 25 percent; capture safe-low PWM"),

    ("EN,500,3", 2.0, "Run at 50 percent PWM; capture 50 percent duty"),
    ("DIS,4", 2.0, "Disable after 50 percent; capture safe-low PWM"),

    ("EN,750,5", 2.0, "Run at 75 percent PWM; capture 75 percent duty"),
    ("DIS,6", 2.0, "Disable after 75 percent; capture safe-low PWM"),

    ("EN,500,7", 2.0, "Run at 50 percent PWM before fault"),
    ("FLT,8", 2.0, "Fault injection; capture fault safe-low"),

    ("RST,9", 2.0, "Reset after fault"),

    ("EN,1500,10", 2.0, "Invalid setpoint; capture latched fault / safe-low"),

    ("RST,11", 2.0, "Reset after invalid setpoint"),

    ("EN,500,12", 6.0, "Run at 50 percent, then wait for CPU Timer0 timeout"),
]

def reader_thread(ser: serial.Serial, log_file, stop_flag):
    while not stop_flag["stop"]:
        try:
            data = ser.readline()
        except serial.SerialException as exc:
            print(f"\\n[SERIAL ERROR] {exc}")
            stop_flag["stop"] = True
            break

        if not data:
            continue

        text = data.decode("utf-8", errors="replace").rstrip("\\r\\n")
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"[{timestamp}] {text}"

        print(line)
        log_file.write(line + "\\n")
        log_file.flush()

def send_command(ser: serial.Serial, log_file, command: str, note: str):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    print("\\n" + "=" * 72)
    print(f"[{timestamp}] TX: {command}")
    print(f"NOTE: {note}")
    print("=" * 72)

    log_file.write("\\n" + "=" * 72 + "\\n")
    log_file.write(f"[{timestamp}] TX: {command}\\n")
    log_file.write(f"NOTE: {note}\\n")
    log_file.write("=" * 72 + "\\n")
    log_file.flush()

    ser.write((command + "\\r\\n").encode("ascii"))
    ser.flush()

def main():
    parser = argparse.ArgumentParser(
        description="Automated serial command runner for C2000 safety-critical actuator demo."
    )
    parser.add_argument("port", help="COM port, e.g. COM6")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument(
        "--log",
        default=r"C:\\Users\\Jonathan\\Documents\\MATLAB\\Course Developement\\c2b\\DMD\\SafetyCritical_Actuator_F28069M\\evidence\\serial_logs\\final_verification_log.txt",
        help="Path to output log file.",
    )
    parser.add_argument(
        "--startup-wait",
        type=float,
        default=2.0,
        help="Seconds to wait before sending first command.",
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Wait for Enter before each command instead of using timed delays.",
    )

    args = parser.parse_args()

    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    stop_flag = {"stop": False}

    print(f"Opening {args.port} at {args.baud} baud...")
    print(f"Saving log to: {log_path}")
    print("Start CCS debug, click Resume, then run this script.")
    print("Use --manual if you want to press Enter before each scope event.")
    print("Press Ctrl+C to stop.\\n")

    with serial.Serial(
        port=args.port,
        baudrate=args.baud,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=0.1,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False,
    ) as ser, log_path.open("w", encoding="utf-8") as log_file:

        log_file.write("C2000 Safety-Critical Actuator Controller Final Verification Log\\n")
        log_file.write(f"Started: {datetime.now().isoformat(timespec='seconds')}\\n")
        log_file.write(f"Port: {args.port}\\n")
        log_file.write(f"Baud: {args.baud}\\n")
        log_file.write("\\n")

        reader = threading.Thread(
            target=reader_thread,
            args=(ser, log_file, stop_flag),
            daemon=True,
        )
        reader.start()

        print(f"Waiting {args.startup_wait} seconds for boot telemetry...\\n")
        time.sleep(args.startup_wait)

        try:
            for command, delay_s, note in DEFAULT_COMMANDS:
                if args.manual:
                    input(f"\\nPress Enter to send {command} ({note})...")
                    send_command(ser, log_file, command, note)
                else:
                    send_command(ser, log_file, command, note)

                print(f"Waiting {delay_s:.1f} seconds...")
                time.sleep(delay_s)

            print("\\nAutomated command sequence complete.")
            print("Keep recording if you want extra timeout/heartbeat evidence.")
            print("Press Ctrl+C to close, or wait 5 more seconds.")

            time.sleep(5.0)

        except KeyboardInterrupt:
            print("\\nStopped by user.")

        finally:
            stop_flag["stop"] = True
            log_file.write(f"\\nEnded: {datetime.now().isoformat(timespec='seconds')}\\n")
            log_file.flush()

if __name__ == "__main__":
    main()
