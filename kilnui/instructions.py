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


instructionSets = {
    "pyrex": [KilnUIInstruction(**instr) for instr in
        [
            {"text": "Starting Up!",
             "exit_condition": "user_input"},
            {"text": "Preheating to 400 for 2 hours",
             "during": {"KilnDrone": {"temperature": 400}},
             "exit_condition": {"time_passed": 60 * 60 * 2}},
            *[{"text": f"Ramping to 1500 over 5 hours (at {i})",
              "during": {"KilnDrone": {"temperature": i}},
               "exit_condition": {"time_passed": 60}
              } for i in range(400, 1505, int((1100 / (60 * 5)) + 1))],
            {"text": "Holding at 1500",
             "during": {"KilnDrone": {"temperature": 1500}},
             "exit_condition": {"time_passed": 60 * 60 * 3}},
            {"text": "Cooling!",
             "exit_condition": {"KilnDrone": {"temperature": 150}}},
            {"text": "All Done!",
             "exit_condition": "user_input"}
        ]
    ],
    "ceramic": [KilnUIInstruction(**instr) for instr in
        [
            {"text": "Starting Up!",
             "exit_condition": "user_input"},
            {"text": "Preheating to 400 for 2 hours",
             "during": {"KilnDrone": {"temperature": 400}},
             "exit_condition": {"time_passed": 60 * 60 * 2}},
            *[{"text": f"Ramping to 800 over 2 hours (at {i})",
              "during": {"KilnDrone": {"temperature": i}},
               "exit_condition": {"time_passed": 60}
              } for i in range(400, 805, int((400 / (60 * 2)) + 1))],
            {"text": "Holding at 800*F for 3 hours",
             "during": {"KilnDrone": {"temperature": 800}},
             "exit_condition": {"time_passed": 60 * 60 * 3}},
            *[{"text": f"Ramping to 1200*F over 4 hours (at {i})",
              "during": {"KilnDrone": {"temperature": i}},
               "exit_condition": {"time_passed": 60}
              } for i in range(800, 1205, int((400 / (60 * 4)) + 1))],
            *[{"text": f"Ramping to 2100*F over 5 hours (at {i})",
              "during": {"KilnDrone": {"temperature": i}},
               "exit_condition": {"time_passed": 60}
              } for i in range(1200, 2105, int(((2100 - 1200) / (60 * 5)) + 1))],
            {"text": "Holding at 2100*F for 4 hours",
             "during": {"KilnDrone": {"temperature": 2100}},
             "exit_condition": {"time_passed": 60 * 60 * 4}},
            {"text": "Cooling!",
             "exit_condition": {"KilnDrone": {"temperature": 150}}},
            {"text": "All Done!",
             "exit_condition": "user_input"}
        ]
    ]
}


instructions = instructionSets["ceramic"]
