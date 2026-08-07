from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src" / "command_parser.c").read_text(encoding="utf-8")
MAIN = (ROOT / "src" / "main.c").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")

def require(condition, message):
    if not condition:
        raise AssertionError(message)

def main():
    require("parse_unsigned_token" in SOURCE, "unsigned parser missing")
    require("parse_signed_token" in SOURCE, "signed parser missing")
    require("sequence_value > 65535UL" in SOURCE, "sequence overflow guard missing")
    require("Controller_SetpointToPwmPercent" in MAIN, "setpoint conversion is not explicit in controller")
    require("COMMS_TIMEOUT_MS     100UL" in MAIN, "final timeout is not 100 ms")
    require("EN,500" in README and "EN,500,14" in README, "documented command examples are incomplete")
    for malformed in ("EN,", "EN,500", "EN,500,1,extra", "DISASTER,1"):
        require(malformed in README, "malformed test vector missing: " + malformed)
    print("static parser contract checks passed")

if __name__ == "__main__":
    main()
