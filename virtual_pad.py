"""Turns a ControllerState into a virtual Xbox 360 controller via ViGEmBus,
so every PC game just sees a normal, fully-supported Xbox pad — regardless
of whether the real controller is a PS3/PS4/PS5 pad on USB or Bluetooth.

Requires the free ViGEmBus driver installed once (see install_vigembus.bat).
"""
import vgamepad as vg

_BUTTON_MAP = {
    "cross": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    "circle": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    "square": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    "triangle": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    "l1": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    "r1": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    "share": vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
    "options": vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
    "l3": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    "r3": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
    "ps": vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE,
}

# hat value (see controller_parsers.ControllerState.dpad) -> (up, down, left, right)
_DPAD_HAT = {
    0: (1, 0, 0, 0), 1: (1, 0, 0, 1), 2: (0, 0, 0, 1), 3: (0, 1, 0, 1),
    4: (0, 1, 0, 0), 5: (0, 1, 1, 0), 6: (0, 0, 1, 0), 7: (1, 0, 1, 0),
    8: (0, 0, 0, 0),
}


class VirtualPad:
    def __init__(self):
        self.gamepad = vg.VX360Gamepad()

    def update(self, state) -> None:
        g = self.gamepad
        g.reset()

        lx, ly = state.left_stick
        rx, ry = state.right_stick
        g.left_joystick_float(x_value_float=lx, y_value_float=-ly)
        g.right_joystick_float(x_value_float=rx, y_value_float=-ry)
        g.left_trigger_float(value_float=state.l2)
        g.right_trigger_float(value_float=state.r2)

        for name, xbox_button in _BUTTON_MAP.items():
            if state.buttons.get(name):
                g.press_button(button=xbox_button)

        up, down, left, right = _DPAD_HAT.get(state.dpad, (0, 0, 0, 0))
        if up:
            g.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
        if down:
            g.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
        if left:
            g.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
        if right:
            g.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)

        g.update()

    def close(self) -> None:
        try:
            self.gamepad.reset()
            self.gamepad.update()
        except Exception:
            pass
