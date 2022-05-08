#!/usr/bin/env python3
import argparse
import collections
import json
import struct

import flask
import serial

GasConcentrationResponse = collections.namedtuple(
    "GasConcentrationResponse",
    "start command concentration temperature status uh_ul checksum",
)

app = flask.Flask(__name__)

serial_device = None


def compute_checksum(payload):
    parts = struct.unpack(">9B", payload)
    return ((~sum(parts[1:-1])) & 0xFF) + 1


def read_concentation(device):
    while True:
        # Request status
        device.write(b"\xff\x01\x86\x00\x00\x00\x00\x00\x79")

        # Read response
        raw_response = device.read(9)
        if len(raw_response) == 9:
            break

    checksum = compute_checksum(raw_response)

    # Parse response
    response = GasConcentrationResponse._make(struct.unpack(">BBHBBHB", raw_response))

    # Validate payload
    if checksum != response.checksum:
        state = {"status": "error", "message": "invalid checksum"}
    elif response.start != 0xFF:
        state = {"status": "error", "message": "invalid start byte"}
    else:
        # Build response
        state = {"status": "success", "data": response._asdict()}

    return state


@app.route("/concentration")
def concentration():
    data = read_concentation(serial_device)
    response = app.response_class(
        response=json.dumps(data), status=200, mimetype="application/json"
    )
    return response


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial-device", default="/dev/serial0")
    parser.add_argument("--baud-rate", default=9600)
    parser.add_argument("--timeout", default=2.0)
    parser.add_argument("--ip", default="0.0.0.0")
    parser.add_argument("--port", default=8080)
    args = parser.parse_args()

    with serial.Serial(
        args.serial_device,
        args.baud_rate,
        timeout=args.timeout,
        stopbits=serial.STOPBITS_ONE,
        parity=serial.PARITY_NONE,
        bytesize=serial.EIGHTBITS,
    ) as serial_device:
        app.run(host=args.ip, port=args.port)
