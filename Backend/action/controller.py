import logging
import re
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("furgal.action.controller")

PREFERRED_PORT_KEYWORDS = ("usb", "acm", "arduino", "ch340", "cp210", "ftdi", "serial")
SAFE_COMMAND_RE = re.compile(r"^[A-Za-z0-9_.+\- /\t]+$")
SAFE_COMMAND_PREFIXES = ("G0", "G1", "G28", "M114", "M119", "SERVO", "MOVE", "STOP")
BLOCKED_COMMAND_PREFIXES = ("M112", "M500", "M502", "M999")


def auto_detect_serial_port() -> Optional[str]:
    #Scan available serial ports and return the best candidate.
    try:
        from serial.tools import list_ports
    except ImportError:
        logger.warning("pyserial not installed; cannot auto-detect port")
        return None

    try:
        ports = list(list_ports.comports())
        if not ports:
            logger.warning("No serial ports detected on this system")
            return None

        scored = []
        for port_info in ports:
            description = f"{port_info.device} {port_info.description} {port_info.hwid}".lower()
            score = 0
            for keyword in PREFERRED_PORT_KEYWORDS:
                if keyword in description:
                    score += 1
            scored.append((score, port_info.device, description))

        scored.sort(reverse=True, key=lambda item: item[0])
        best = scored[0]
        logger.info("Auto-detected serial port: %s (%s)", best[1], best[2])
        return best[1]
    except Exception as exc:
        logger.error("Serial port auto-detection failed: %s", exc)
        return None


class RobotController:
    SUPPORTED_PROTOCOLS = ("serial", "gcode", "ros")

    def __init__(
        self,
        protocol: str = "serial",
        port: Optional[str] = None,
        baudrate: int = 115200,
        simulate: bool = True,
    ):
        protocol = (protocol or "serial").lower()
        if protocol not in self.SUPPORTED_PROTOCOLS:
            raise ValueError(f"Unsupported protocol: {protocol}")
        self.protocol = protocol
        self.port = port
        self.baudrate = baudrate
        self.simulate = simulate
        self._serial = None
        self._serial_available = False
        self._connected = False
        self._init_serial_library()

        if not self.port and not self.simulate:
            detected = auto_detect_serial_port()
            if detected:
                self.port = detected
            else:
                logger.warning("No serial port found; enabling simulation mode")
                self.simulate = True

    def _init_serial_library(self):
        try:
            import serial  # noqa: F401
            self._serial_available = True
        except ImportError:
            self._serial_available = False
            if not self.simulate:
                logger.warning("pyserial not installed; forcing simulation mode")
                self.simulate = True

    def _ensure_simulation(self, reason: str):
        if not self.simulate:
            logger.warning("%s — switching to simulation mode", reason)
            self.simulate = True

    def connect(self) -> Dict[str, Any]:
        if self.simulate:
            self._connected = True
            return {"success": True, "mode": "simulated", "protocol": self.protocol}

        if not self._serial_available:
            self._ensure_simulation("Serial library unavailable")
            self._connected = True
            return {"success": True, "mode": "simulated", "protocol": self.protocol}

        if not self.port:
            detected = auto_detect_serial_port()
            if detected:
                self.port = detected
            else:
                self._ensure_simulation("No serial port available")
                self._connected = True
                return {"success": True, "mode": "simulated", "protocol": self.protocol}

        try:
            import serial
            self._serial = serial.Serial(self.port, self.baudrate, timeout=2)
            self._connected = True
            logger.info("Robot controller connected on %s", self.port)
            return {
                "success": True,
                "mode": "hardware",
                "port": self.port,
                "protocol": self.protocol,
            }
        except Exception as exc:
            logger.error("Robot connect failed: %s", exc)
            self._ensure_simulation(f"Connection failed: {exc}")
            self._connected = True
            return {"success": True, "mode": "simulated", "protocol": self.protocol, "fallback_reason": str(exc)}

    def disconnect(self):
        try:
            if self._serial is not None:
                self._serial.close()
                self._serial = None
            self._connected = False
        except Exception as exc:
            logger.error("Robot disconnect failed: %s", exc)

    def _format_command(self, command: str) -> str:
        command = command.strip()
        if self.protocol == "gcode" and not command.startswith("G") and not command.startswith("M"):
            return f"G1 {command}"
        if self.protocol == "ros":
            return f"ros: {command}"
        return command

    def _validate_safe_command(self, command: str) -> Optional[str]:
        upper = command.strip().upper()
        if len(command) > 160:
            return "Robot command is too long"
        if any(char in command for char in ("\r", "\n", ";", "|", "&", "`")):
            return "Robot command contains unsafe control characters"
        if not SAFE_COMMAND_RE.fullmatch(command):
            return "Robot command contains unsupported characters"
        if upper.startswith(BLOCKED_COMMAND_PREFIXES):
            return "Robot command is blocked by safety policy"
        if not upper.startswith(SAFE_COMMAND_PREFIXES):
            return "Robot command prefix is not allowed"
        return None

    def send_command(self, command: str) -> Dict[str, Any]:
        if not command or not isinstance(command, str):
            return {"success": False, "error": "Robot command must be a non-empty string"}

        command_to_validate = command.strip() if self.protocol == "ros" else self._format_command(command)
        safety_error = self._validate_safe_command(command_to_validate)
        if safety_error:
            logger.warning("Blocked unsafe robot command: %s", command_to_validate)
            return {"success": False, "error": safety_error}
        formatted = self._format_command(command)

        if not self.simulate and not self._serial_available:
            self._ensure_simulation("Serial unavailable at send_command time")

        if not self._connected:
            connect_result = self.connect()
            if not connect_result.get("success"):
                return connect_result

        try:
            if self.simulate:
                logger.info("Simulated robot command: %s", formatted)
                return {
                    "success": True,
                    "mode": "simulated",
                    "command": formatted,
                    "timestamp": time.time(),
                }
            if self._serial is None:
                self._ensure_simulation("Serial connection is None")
                return {
                    "success": True,
                    "mode": "simulated",
                    "command": formatted,
                    "timestamp": time.time(),
                }
            payload = (formatted + "\n").encode("utf-8")
            self._serial.write(payload)
            response = self._serial.readline().decode("utf-8", errors="ignore").strip()
            return {
                "success": True,
                "mode": "hardware",
                "command": formatted,
                "response": response,
                "timestamp": time.time(),
            }
        except Exception as exc:
            logger.error("send_command failed: %s", exc)
            self._ensure_simulation(f"send_command error: {exc}")
            return {
                "success": True,
                "mode": "simulated",
                "command": formatted,
                "timestamp": time.time(),
                "fallback_reason": str(exc),
            }

    def move_servo(self, servo_id: int, angle: float) -> Dict[str, Any]:
        try:
            angle = float(angle)
            if not (0.0 <= angle <= 180.0):
                return {"success": False, "error": "Servo angle must be between 0 and 180"}
            command = f"SERVO {int(servo_id)} {angle:.1f}"
            return self.send_command(command)
        except (TypeError, ValueError) as exc:
            return {"success": False, "error": f"Invalid servo parameters: {exc}"}
