unicode_forbidden_symbol = u"\U0001F6C7"
unicode_uparrow_symbol = u"\u2B61"
unicode_downarrow_symbol = u"\u2B63"


class KilnUIInstruction:
    def __init__(self, text, exit_condition, during=None, on_exit=None, tip=None):
        self.text = text
        self.exit_condition = exit_condition
        self.during = during
        self.on_exit = on_exit
        self.tip = tip


instructions = [
    KilnUIInstruction(**instr) for instr in
    [
        {"text": "Starting Up!",
         "exit_condition": "user_input"},
        {"text": "Preheating to 400",
         "during": {"KilnDrone": {"temperature": 400}},
         "exit_condition": {"time_passed": 60 * 60 * 1.4}},
        *[{"text": f"Ramping to 1500 (at {i})",
           "during": {"KilnDrone": {"temperature": i}},
           "exit_condition": {"time_passed": 60 * 5}
           } for i in range(415, 1505, 5)],
        {"text": "Holding at 1500",
         "during": {"KilnDrone": {"temperature": 1500}},
         "exit_condition": {"time_passed": 60 * 60 * 3}},
        {"text": "Cooling!",
         "exit_condition": {"KilnDrone": {"temperature": 150}}},
        {"text": "All Done!",
         "exit_condition": "user_input"}
    ]
]
