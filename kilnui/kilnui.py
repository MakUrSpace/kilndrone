import json
import asyncio
from datetime import datetime
from dataclasses import asdict
from inspect import getmembers, ismethod, signature

from deepdiff import DeepDiff
import justpy as jp

from groundplane import groundplane
from groundplane.things import thing

from kilndrone import KilnDrone
from kilnui.instructions import instructions


gp = None
wp = None
instr_interface = None

label_classes = "m-2 p-2 w-128 text-right"
button_classes = "w-16 bg-blue-500 hover:bg-blue-700 text-white font-bold rounded-full"
input_classes = "m-2 bg-gray-200 border-2 border-gray-200 rounded w-64 py-2 px-4 text-gray-700 focus:outline-none focus:bg-white focus:border-purple-500"
p_classes = 'm-2 p-2 h-32 text-xl border-2'


class kilndrone_thing(thing):
    def __init__(self, SORT, DEVICE_TYPE):
        super().__init__(SORT, DEVICE_TYPE)

        self.kilnDrone = KilnDrone()
        self.kilnDrone.setTargetTemperature(0)
        # self.kilnDrone.run()

    def state(self):
        return {"state": json.dumps(asdict(self.kilnDrone.controller.characterizeKiln())),
                "TIMESTAMP": datetime.utcnow().isoformat()}

    def request_state(self, requested_state):
        print(requested_state)
        requestedTemperature = requested_state.get("temperature", None)
        self.request_temperature(requestedTemperature)

    def request_temperature(self, targetTemperature):
        self.kilnDrone.setTargetTemperature(targetTemperature)

    def at_or_above_temperature(self):
        return self.kilnDrone.controller.temperature > self.kilnDrone.controller.targetTemp


def thing_administration_invocation(self, msg):
    method = getattr(self.thing, self.method_name)
    print(f"{self} Received {self.method_name} for {method}")
    args = []
    kwargs = {}
    if self.arg_field is not None:
        print(f"With args: {self.arg_field}")
        if self.arg_field.value[0] == "{" and self.arg_field.value[-1] == "}":
            kwargs = json.loads(self.arg_field.value)
        else:
            args = [self.arg_field.value]
    else:
        print("No argfields")

    try:
        result = f"{method(*args, **kwargs)}"
    except Exception as e:
        result = f"Failed invocation: {e}"
    self.result.text = result


def build_thing_panel(host_div, thing):
    global gp
    thing_div = jp.Div(a=host_div, classes="border-2")
    jp.Div(a=thing_div, classes="text-2xl text-center p-2", text=f"{thing.thing_name.replace('_', ' ').title()} panel")
    for method_name, method in getmembers(thing, ismethod):
        if '__' in method_name[2:]:
            continue
        ui_div = jp.Div(a=thing_div, classes="flex justify-center items-center")
        method_sig = signature(method)
        main_label_text = f"{method_name.replace('_', ' ').title()}"
        arg_field = None
        if method_sig.parameters:
            label_text = f" ({dict(method_sig.parameters)}) "
            jp.Div(a=ui_div, classes=label_classes, text=main_label_text + label_text)
            arg_field = jp.Input(a=ui_div, type="text", classes="w-256 m-4 text-right border-2")
        else:
            jp.Label(a=ui_div,
                     text=main_label_text,
                     classes=label_classes)
        invoke = jp.Button(a=ui_div, text="Invoke", click=thing_administration_invocation, classes=button_classes)
        invoke.method_name = method_name
        invoke.arg_field = arg_field
        invoke.thing = thing
        invoke.result = jp.Div(a=ui_div, text="", classes="w-256 m-4 p-4 text-left")


textStatusMonitor = None


async def updateTextStatusMonitor():
    while True:
        await asyncio.sleep(2)
        if textStatusMonitor is not None:
            textStatusMonitor.add_component(
                jp.Div(a=textStatusMonitor, classes=label_classes + " border-2", text=f"{gp.KilnDrone.kilnDrone.controller.characterizeKiln()}"),
                position=0
            )
            jp.run_task(wp.update())


def build_monitor_panel(host_div):
    monitor_div = jp.Div(a=host_div, classes="border-2 justify-center flex flex-wrap -mx-3")

    global textStatusMonitor
    textStatusMonitor = jp.Div(a=monitor_div, classes="border-2 flex flex-wrap overflow-auto h-64 justify-center")

    chart = jp.Matplotlib(a=monitor_div)

    async def renderChart(*args, **kwargs):
        fig = gp.KilnDrone.kilnDrone.renderKilnDrone()
        chart.set_figure(fig)

    jp.Button(a=monitor_div, text="Refresh Chart", click=renderChart, classes=button_classes)
    jp.run_task(renderChart())


def atTargetState(targetState, currentState):
    stateDiff = DeepDiff(targetState, currentState)
    return 'values_changed' not in stateDiff and \
        'dictionary_item_removed' not in stateDiff


async def condition_watcher(conditions):
    while True:
        met = True
        for comp, condition in conditions.items():
            if comp == "time_passed":
                timePassed = (datetime.utcnow() - wp.enteredStageAt).total_seconds()
                if timePassed < condition:
                    print(f"{timePassed} seconds of {condition} of passed")
                    met = False
                    break
                else:
                    continue

            print(f"Checking {comp} is set to {condition}")
            comp = getattr(gp, comp)
            compCurrentState = comp.state()['state']
            if not atTargetState(condition, compCurrentState):
                met = False
                print("Conditions not met")
                break
        if met:
            print("CONDITIONS MET!")
            break
        await asyncio.sleep(1)
    await exit_instruction()


async def exit_instruction():
    # Perform exit tasks
    print(f"Performing exit instructions for {wp.stage}")
    instruction = instructions[wp.stage]
    print(f"{wp.stage} instruction: {instruction.text}")
    if instruction.on_exit is not None:
        for comp, condition in instruction.on_exit.items():
            print(f"Setting {comp} to {condition}")
            if comp == "stage":
                wp.stage = condition - 1
            else:
                getattr(gp, comp).request_state(condition)
                print(f"{getattr(gp, comp)}")
                print(gp.right_door_latch.state())
    wp.stage += 1
    wp.enteredStageAt = datetime.utcnow()
    await build_instr_interface()


def box_checked(self, msg):
    jp.run_task(exit_instruction())


async def build_instr_interface():
    global instr_interface
    global wp
    print(f"WP at stage {wp.stage}")
    if instr_interface is not None:
        wp.instrContainer.remove_component(instr_interface)
        instr_interface.delete()

    instruction = instructions[wp.stage]

    if instruction.during is not None:
        print(f"Setting during conditions: {instruction.during}")
        for comp, condition in instruction.during.items():
            print(f"Setting {condition}")
            getattr(gp, comp).request_state(condition)

    instr_interface = jp.Div(a=wp.instrContainer, classes="container justify-center border-2")
    jp.Div(a=instr_interface, classes="text-2xl text-center p-2", text=instruction.text)
    if instruction.exit_condition == "user_input":
        print("Configuring for user input")
        div = jp.Div(a=instr_interface, classes="flex justify-center items-center align-center border-2")
        button_classes = 'w-32 mr-2 mb-2 bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-full'
        jp.Button(a=div, type='button', classes=button_classes, click=box_checked, text="Confirm Step Complete")
        await wp.update()
    else:
        print("Configuring for condition watcher")
        await wp.update()
        jp.run_task(condition_watcher(instruction.exit_condition))


def input_demo(request):
    global wp
    wp = jp.WebPage()
    wp.stage = 0
    jp.Div(a=wp, classes="text-6xl text-center p-2", text="KilnDrone Administration Console")
    panel_div = jp.Div(a=wp, classes="border-4")

    wp.instrContainer = jp.Div(a=panel_div, classes="border-2 flex justify-center")
    jp.run_task(build_instr_interface())

    build_monitor_panel(panel_div)
    things = [getattr(gp, m['SORT']) for m in gp.mthings]
    for gThing in things:
        build_thing_panel(panel_div, gThing)
    return wp


def launch_server(gp_cfg_path):
    global gp
    gp = groundplane(gp_cfg_path)
    jp.justpy(input_demo, host='0.0.0.0', startup=lambda: jp.run_task(updateTextStatusMonitor()))
