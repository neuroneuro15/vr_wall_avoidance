
import os
import datetime
import numpy as np
from numpy import random
import ratcave
import ratcave.graphics as graphics
from psychopy import event, sound, gui
import sys

import natnetclient

# Note: Connect to Motive, and get rigid bodies to track
# NatNetClient code
tracker = natnetclient.NatClient()
arena_rb = tracker.rigid_bodies['Arena']
additional_rotation = ratcave.utils.correct_orientation_natnet(arena_rb)


# Script

# Note: Collect Metadata (subject, mainly, and Session Parameters) for the log
metadata = {'Experiment': 'VR_Wall_Avoidance',
            'nPhases': 2,
            'Phase Time':  5 * 60.,  # 5 minutes,
            'Wall Num1': [random.randint(1, 3), 1, 2], # Select which corner everything appears in.
            'Wall Length1': [random.choice(['Long', 'Short']), 'Long', 'Short'],
            'Wall Num2': [random.randint(1, 3), 1, 2], # Select which corner everything appears in.
            'Wall Length2': [random.choice(['Long', 'Short']), 'Long', 'Short'],
            'Experimenter': 'Nicholas A. Del Grosso',
            'Rat': ['Test', 'Nessie', 'FuzzPatch', 'FlatWhite', 'Bridger'],
            'Rat Rigid Body': ['Rat']+tracker.rigid_bodies.keys(),
            'Texture Size': 1024
            }

dlg = gui.DlgFromDict(metadata, 'Input Parameters:')
if not dlg.OK:
    sys.exit()

rat_rb = tracker.rigid_bodies[metadata['Rat Rigid Body']]

# Note: Load Arena, virtual arena, and walls
arena = ratcave.utils.get_arena_from(os.path.join('obj', 'VR_WallAvoidance.obj'), cubemap=True)

vir_reader = graphics.WavefrontReader(os.path.join('obj', 'VR_WallAvoidance.obj'))
vir_arena = vir_reader.get_mesh('Arena')
vir_arena.load_texture(graphics.resources.img_uvgrid)
vir_arena.material.spec_weight = 0.
vir_arena.material.diffuse.rgb = .3, .3, .3

walls = []
for wall_idx in '12':
    wall = vir_reader.get_mesh(metadata['Wall Length'+wall_idx] + 'Wall' + metadata['Wall Num'+wall_idx])
    wall.load_texture(graphics.resources.img_uvgrid)
    wall.visible = False
    wall.material.diffuse.rgb = 1., 1., 1.
    wall.material.spec_weight = 0.
    wall.local.y -= .01 
    walls.append(wall)


# Note: Build Scenes (1st half, 2nd half) and window
active_scene = graphics.Scene([arena], camera=graphics.projector, light=graphics.projector, bgColor=(0., 0., .2, 1.))
vir_scene = graphics.Scene(walls+[vir_arena], light=graphics.projector, bgColor=(0., .2, 0., 1.))

window = graphics.Window(active_scene, fullscr=True, screen=1, texture_size=metadata['Texture Size'])
window.virtual_scene = vir_scene

# Note: Wait for recording to start in Motive before starting the session.
tone = sound.Sound()
tone.play()  # Just to get the experimenter's attention
tracker.set_take_file_name('_'.join([metadata['Experiment'], metadata['Rat'], datetime.datetime.today().strftime('%Y-%m-%d_%H-%M-%S')]) + '.take')
tracker.wait_for_recording_start(debug_mode=metadata['Rat'] == 'Test')

# Note: Don't start recording/timing until rat has been placed in the arena.
print("Waiting for rat to enter trackable area before beginning the simulation...")
while not rat_rb.seen and metadata['Rat'] != 'Test':
    pass
print("...Rat Detected!")

# Note: Main Experiment Loop
with graphics.Logger(scenes=[active_scene, vir_scene], exp_name=metadata['Experiment'], log_directory=os.path.join('.', 'logs'),
                     metadata_dict=metadata) as logger:

    for wall in walls:

        # Assign new virtual scene, and make its (and only its) meshes visible.
        logger.write('New Phase')
        wall.visible = True
        ratcave.utils.update_world_position_natnet(window.virtual_scene.meshes + [arena], arena_rb, additional_rotation)

        for _ in ratcave.utils.timers.countdown_timer(metadata['Phase Time'], stop_iteration=True):

            # Note: Update Camera Position based on Rat's position
            window.virtual_scene.camera.position = rat_rb.position
            window.virtual_scene.camera.rotation = rat_rb.rotation

            # Draw and Flip
            window.draw()
            logger.write(':'.join(["Motive iFrame", str(tracker.iFrame)]))
            window.flip()

            # Give keyboard option to cleanly break out of the nested for-loop
            if 'escape' in event.getKeys():
                break
        else:
            wall.visible = False
            continue
        break

# Note: Clean-Up Section
window.close()
tone.play()
