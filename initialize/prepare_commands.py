import os, csv, sys
import numpy as np
import pandas as pd

GLOBAL_NUM_COMPUTE_NODES = 5
GLOBAL_CHUNK_SIZE = 1500
GLOBAL_MAX_TRIALS = 10000
GLOBAL_PROJECT_DIR = '/home/robot/Documents/grasping'
GLOBAL_SAVE_DIR = os.path.join(GLOBAL_PROJECT_DIR, 'collect/commands')
GLOBAL_DATA_DIR = os.path.join(GLOBAL_PROJECT_DIR, 'collect/candidates')

GLOBAL_PROGRAM_NAME = '/scratch/mveres/grasping/grasping/collect/scene_v40_cameras.ttt'

def main():
    """Equally splits grasp candidates to check into equal number of chunks.

    # NOTE: The key is to make sure each chunk only contains a single object.
    # This allows us to avoid continuously loading /similar/different/ objects
    # from memory during the simulation
    """

    if not os.path.exists(GLOBAL_SAVE_DIR):
        os.makedirs(GLOBAL_SAVE_DIR)
    if not os.path.exists(GLOBAL_DATA_DIR):
        os.makedirs(GLOBAL_DATA_DIR)

    files = os.listdir(GLOBAL_DATA_DIR)
    files = [f for f in files if '.txt' in f and ['sample', 'poses' not in f]]

    data = [0]*len(files)
    for i, f in enumerate(files):

        fp = os.path.join(GLOBAL_DATA_DIR, f)
        df = pd.read_csv(fp, header=None, index_col=False).values

        # Append the name of the object and number of grasp candidates available
        data[i] = (fp.split('/')[-1], df.shape[0])


    # Calculate ranges to equally chunk the grasp candidates
    info = []
    for mesh_object in data:

        # Only going to process a certain number of candidates, but need to
        # make sure each file contains **at most** GLOBAL_MAX_TRIAL's worth
        num_elements= np.minimum(GLOBAL_MAX_TRIALS, mesh_object[1])
        n_chunks = int(num_elements / GLOBAL_CHUNK_SIZE)
        remainder = num_elements % GLOBAL_CHUNK_SIZE

        # This will tell the simulator a range of which lines to use
        indices = [i*GLOBAL_CHUNK_SIZE + 1 for i in xrange(n_chunks)]
        indices.append(n_chunks*GLOBAL_CHUNK_SIZE+remainder)

        # This will tel l the simulator where the lines can be found
        object_name = [mesh_object[0]]*len(indices)
        info += zip(object_name, indices[:-1], indices[1:])


    # Save the command for running the sim. The command is composed of
    # flags such as 'headless mode' (-h), 'quit when done' (-q), 'start'
    # (-s), 'input argument' (-g), and the simulation we will run.
    # Here, we give the input argument as the file contaianing grasp
    # candidates

    commands = [0]*len(info)
    for i, sub_cmd in enumerate(info):

        if len(info) % int(len(info)*0.1) == 0:
            print '%d/%d generated'%(i, len(info))
        commands[i] = \
            'ulimit -n 4096; export DISPLAY=:1; vrep.sh -h -q -s -g%s -g%s -g%s %s '\
            %(sub_cmd[0], sub_cmd[1], sub_cmd[2], GLOBAL_PROGRAM_NAME)


    # To parallelize our data collection routine across different compute nodes,
    # we chunk the commands again. Each compute node will be responsible for
    # running a certain number of commands.  NOTE: If we are performing
    # collection on a single compute node, then num_compute_nodes should be 1.
    file_length = int(len(commands)/GLOBAL_NUM_COMPUTE_NODES + 0.5)
    remainder = len(commands) % GLOBAL_NUM_COMPUTE_NODES

    for i in xrange(GLOBAL_NUM_COMPUTE_NODES):

        if i == GLOBAL_NUM_COMPUTE_NODES - 1:
            size = range(i*file_length, (i+1)*file_length + remainder)
        else:
            size = range(i*file_length, (i+1)*file_length)

        # Each 'main' file contains file_length number of chunks of commands
        # that the simulator will need to run.
        main_file = open(os.path.join(GLOBAL_SAVE_DIR, 'main%d.txt'%i), 'wb')
        writer = csv.writer(main_file, delimiter=',')

        for row in size:
            writer.writerow([commands[row]])

        main_file.close()


if __name__ == '__main__':
    main()