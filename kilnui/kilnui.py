import json
import asyncio
from datetime import datetime
from inspect import getmembers, ismethod, signature
import os

import aiohttp
from deepdiff import DeepDiff
import justpy as jp

from groundplane import groundplane

from kilnui import instructions


gp = None
wp = None
instr_interface = None

label_classes = "m-2 p-2 w-128 text-right"
button_classes = "w-16 bg-blue-500 hover:bg-blue-700 text-white font-bold rounded-full"
input_classes = "m-2 bg-gray-200 border-2 border-gray-200 rounded w-64 py-2 px-4 text-gray-700 focus:outline-none focus:bg-white focus:border-purple-500"
p_classes = 'm-2 p-2 h-32 text-xl border-2'


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


class WPState:
    stage: int = 0
    enteredStageAt: datetime = None
    lastSave: datetime = None

    @classmethod
    def moveToNextStage(cls):
        cls.stage = 0 if cls.stage + 1 >= len(instructions) else cls.stage + 1
        cls.enteredStageAt = datetime.utcnow()
        cls.save()

    @classmethod
    def save(cls):
        if cls.lastSave is None or (datetime.utcnow() - cls.lastSave).total_seconds() > 300:
            cls.lastSave = datetime.utcnow()
            status = {
                "stage": cls.stage,
                "enteredStageAt": cls.enteredStageAt.isoformat(),
                "lastSave": cls.lastSave.isoformat()
            }
            with open("lastState.json", "w") as f:
                f.write(json.dumps(status, indent=2))

    @classmethod
    def restore(cls):
        try:
            print("Attempting to restore WP state")
            with open("lastState.json", "r") as f:
                lastState = json.loads(f.read())
                lastState['enteredStageAt'] = datetime.fromisoformat(lastState['enteredStageAt'])
                lastState['lastSave'] = datetime.fromisoformat(lastState['lastSave'])
            if (datetime.utcnow() - lastState['lastSave']).total_seconds() < 600:
                print("Restoring recovered state")
                cls.stage = lastState['stage']
                cls.enteredStageAt = lastState['enteredStageAt']
                cls.lastSave = lastState['lastSave']
            else:
                raise Exception("Last state too old!!!!")
        except Exception as e:
            print(f"EGADS!!! An exception with our memory, Brain! {e}")
            cls.stage = 0
            cls.enteredStageAt = datetime.utcnow()
            cls.lastSave = None


async def updateTextStatusMonitor():
    print("Starting Text Status Monitor")
    while True:
        await asyncio.sleep(5)
        print("Monitoring")
        WPState.save()
        gp.upload_state()
        if textStatusMonitor is not None:
            status = gp.KilnDrone.kilnDrone.controller.characterizeKiln()
            statusComment = jp.Div(classes=label_classes + " border-2", text=f"{status}")
            textStatusMonitor.add_component(statusComment, position=0)
            jp.run_task(wp.update())
    raise Exception("This shouldn't be reachable...")


updateTextStatusMonitor.statusComment = None


chart = None


async def renderChart(*args, **kwargs):
    while gp.KilnDrone.kilnDrone.controller.power.value:
        await asyncio.sleep(0.5)
        break
    fig = gp.KilnDrone.kilnDrone.renderKilnDrone()
    if chart is not None:
        chart.set_figure(fig)
    await wp.update()


def build_monitor_panel(host_div):
    monitor_div = jp.Div(a=host_div, classes="border-2 justify-center flex flex-wrap -mx-3")

    global textStatusMonitor, chart
    textStatusMonitor = jp.Div(a=monitor_div, classes="border-2 flex flex-wrap overflow-auto h-64 justify-center")
    chart = jp.Matplotlib(a=monitor_div)

    jp.Button(a=monitor_div, text="Refresh Chart", click=renderChart, classes=button_classes)


def atTargetState(targetState, currentState):
    stateDiff = DeepDiff(targetState, currentState)
    return 'values_changed' not in stateDiff and \
        'dictionary_item_removed' not in stateDiff


async def condition_watcher(conditions):
    print("Starting Stage Exit Condition Watcher")
    while True:
        met = True
        for comp, condition in conditions.items():
            print("Checking Stage Exit Conditions...")
            if comp == "time_passed":
                timePassed = (datetime.utcnow() - WPState.enteredStageAt).total_seconds()
                if timePassed < condition:
                    timeMessage = f"{timePassed} of {condition} seconds of passed"
                    instr_interface.dynDiv.text = timeMessage
                    print(timeMessage)
                    met = False
                    break
                else:
                    continue

            print(f"Checking {comp} is set to {condition}")
            comp = getattr(gp, comp)
            compCurrentState = comp.state()['state']
            if not atTargetState(condition, compCurrentState):
                met = False
                conditionMsg = f"{comp} condition: ({condition}) not met"
                instr_interface.dynDiv.text = conditionMsg
                print(conditionMsg)
                break
        if met:
            print("CONDITIONS MET!")
            break
        await asyncio.sleep(1)
    await exit_instruction()


async def exit_instruction():
    # Perform exit tasks
    print(f"Performing exit instructions for {WPState.stage}")
    instruction = instructions[WPState.stage]
    print(f"{WPState.stage} instruction: {instruction.text}")
    if instruction.on_exit is not None:
        for comp, condition in instruction.on_exit.items():
            print(f"Setting {comp} to {condition}")
            if comp == "stage":
                WPState.stage = condition - 1
            else:
                getattr(gp, comp).request_state(condition)
                print(f"{getattr(gp, comp)}")
                print(gp.right_door_latch.state())
    WPState.moveToNextStage()
    await build_instr_interface()


def box_checked(self, msg):
    jp.run_task(exit_instruction())


async def build_instr_interface():
    global instr_interface
    global wp
    print(f"WP at stage {WPState.stage}")
    if instr_interface is not None:
        wp.instrContainer.remove_component(instr_interface)
        wp.instrContainer.remove_component(instr_interface.dynDiv)
        instr_interface.dynDiv.delete()
        instr_interface.delete()

    instruction = instructions[WPState.stage]

    if instruction.during is not None:
        print(f"Setting during conditions: {instruction.during}")
        for comp, condition in instruction.during.items():
            print(f"Setting {condition}")
            getattr(gp, comp).request_state(condition)

    instr_interface = jp.Div(a=wp.instrContainer, classes="container justify-center border-2")
    instr_interface.dynDiv = jp.Div(a=wp.instrContainer, classes="justify-center border-2")
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


def build_page(gp_cfg_path):
    global wp
    global gp

    gp = groundplane(gp_cfg_path)

    wp = jp.WebPage()

    jp.Div(a=wp, classes="text-6xl text-center p-2", text="KilnDrone Administration Console")
    panel_div = jp.Div(a=wp, classes="border-4")

    wp.instrContainer = jp.Div(a=panel_div, classes="border-2 flex justify-center")

    build_monitor_panel(panel_div)
    things = [getattr(gp, m['SORT']) for m in gp.mthings]
    for gThing in things:
        build_thing_panel(panel_div, gThing)

    WPState.restore()


async def startThings():
    for startUpFunc in [ 
            gp.KilnDrone.kilnDrone.asyncRun,
            updateTextStatusMonitor,
            build_instr_interface,
            renderChart,
            checkHealth]:
        jp.run_task(startUpFunc())


async def checkHealth():
    await asyncio.sleep(15)
    count = 0
    sleepTime = 5
    limit = 900  # 5 * 180 = 900 == 15 minutes between deaths
    try:
        while True:
            print("Checking health")
            count += 1
            if count > limit:
                raise Exception("Been alive way too long!")

            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8000") as resp:
                    if resp.status != 200:
                        raise Exception("Server done borked")
                    else:
                        print(f"Server looks healthy. Killing in {limit - count} cycles")

            await asyncio.sleep(sleepTime)
    except Exception as e:
        print(f"Killing Self because of {e}!")
        gp.KilnDrone.kilnDrone.controller.power.off()
        os.kill(os.getpid(), 9)


async def handle_request(request):
    return wp


def launch_server(gp_cfg_path):
    build_page(gp_cfg_path)
    jp.justpy(handle_request, host='0.0.0.0', startup=startThings)
