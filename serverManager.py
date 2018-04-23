import os
import signal
import time
from subprocess import check_output

# ---------------------------------------
# A server management system for CIS 452.
#
# Manages a hierarchy of processes with
# the ability to create and abort each tier.
# Also will print a diagnostic message to
# show the state of the program.
#
# CIS 452 Fall 2017
# Charles Billingsley
# ----------------------------------------

# ------------------------------ Global Variables -----------------------------
server_processes = []
server_minimum_number = 0
server_maximum_number = 3


# ------------------------------ Worker Functions -----------------------------
def create_server(minimum_number_of_processes, maximum_number_of_processes,
                  server_name):
    """
        Creates a process to represent a server if the createServer
        command is found.

        :param minimum_number_of_processes: The minimum number of processes
                                            the server should maintain
        :param maximum_number_of_processes: The maximum number of processes
                                            the server should maintain
        :param server_name: The name of the server

        :return pid: The pid of the newly created server
    """
    print("[Manager] Starting server %s with maximum processes "
          "of %d and minimum processes of %d." % (server_name,
                                                  minimum_number_of_processes,
                                                  maximum_number_of_processes))
    global number_of_active_processes
    global server_processes
    global server_minimum_number
    global server_maximum_number

    try:
        # Creates a 'server' process
        pid = os.fork()
        server_minimum_number = minimum_number_of_processes
        server_maximum_number = maximum_number_of_processes


        if pid == 0:  # In Server
            print("[" + server_name + "] " + server_name +
                  " Started successfully. PID: " + str(os.getpid()))

            # Loop forever so that more processes can spawn automatically
            while True:
                # Registers a handler for when a child process is killed
                signal.signal(signal.SIGCHLD, abnormal_child_exit_handler)

                # Registers a handler for when
                # a child should be created
                signal.signal(signal.SIGUSR1,
                              increment_active_processes)

                # Registers a handler for when
                # a child should be aborted
                signal.signal(signal.SIGUSR2,
                              decrement_active_processes)

                # Registers a handler to terminate replicants when a SIGTERM is found
                signal.signal(signal.SIGTERM, terminate_replicants)

                # Loop creating processes until the expected number is reached
                while len(server_processes) <= number_of_active_processes:

                    # Loop until the number of processes
                    # differs from what we expect
                    while len(server_processes) == number_of_active_processes:

                        # Do nothing
                        time.sleep(10)

                    # Makes sure more processes are allowed to be created
                    if len(server_processes) < maximum_number_of_processes:
                        try:
                            # Creates a 'replicant' process
                            pid2 = os.fork()

                            # Save the pid to a global list for fault tracking
                            server_processes.append(pid2)

                        except OSError:
                            # If the fork fails, start the
                            # loop over and try again
                            continue

                        if pid2 == 0:  # In Server's Grandchild
                            print(
                                "\n[Replicant of " + server_name
                                + "] Replicant of " + server_name
                                + " Started successfully. PID: "
                                + str(os.getpid()))

                            # Sleep forever since this is just a mock-up
                            while True:
                                time.sleep(10)

                        elif pid2 > 0:  # In Server
                            # Continue looping if the process is the server
                            continue
                        else:
                            # If anything goes unexpected, loop and try again
                            continue
                    else:
                        break

                # If there are more processes than expected,
                # loop until they are taken care of.
                while len(server_processes) > number_of_active_processes:

                    # Remove a process from the list
                    process_to_remove = server_processes.pop()

                    # Kill the removed process
                    os.kill(process_to_remove, signal.SIGKILL)

                    # Wait for the child to be cleaned up before continuing
                    os.wait()
                    print("[" + server_name
                          + "] Child process terminated successfully.")
        elif pid > 0:  # In Manager

            # Registers a handler for when a child process is killed
            signal.signal(signal.SIGCHLD, child_exit_handler)

            # Sleep to allow prompt to print
            time.sleep(.2)
            return pid
        else:  # Child fork failed
            print("Error forking")
    except OSError as error:
        print("Server creation failed: " + error.strerror)


def child_exit_handler(signum, frame):
    """
        Waits for the current children to finish to avoid leaving zombies.
        WNOHANG prevents blocking so the servers can still continue

        :param signum: The first default value needed for a signal handler
        :param frame: The second default value needed for a signal handler
    """
    # Wait for a -1 without hanging up the rest of the program
    os.waitpid(-1, os.WNOHANG)


def abnormal_child_exit_handler(signum, frame):
    """
        Removes the child from the processes list and waits for the current
        zombie child to finish. Used when a child has exited abnormally.

        :param signum: The first default value needed for a signal handler
        :param frame: The second default value needed for a signal handler
    """
    global server_processes

    # Registers a handler to ignore when a child process is killed
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)

    # Loops through the processes and searches for the zombie using ps
    for pid in server_processes:

        # Run the ps command to get the status of each pid, and convert to str
        status = str(
            check_output("ps -o stat -p" + str(pid),
                         shell=True), 'utf-8').split('\n')

        # If the pid is marked as a zombie
        if "Z+" in status[1]:
            print("\n[Server] Child process " + str(pid)
                  + " stopped unexpectedly.")

            # Remove the zombie from the list of active replicants
            server_processes.remove(pid)

    # Wait for a -1 without hanging up the rest of the program
    os.waitpid(-1, os.WNOHANG)


def increment_active_processes(signum, frame):
    """
        Increments the number of active processes by 1 to increase
        the number of child processes.

        :param signum: The first default value needed for a signal handler
        :param frame: The second default value needed for a signal handler
    """
    global number_of_active_processes
    global server_maximum_number

    # Make sure adding a new process wouldn't exceed the maximum limit
    if (number_of_active_processes + 1) > server_maximum_number:
        print("[Server] Maximum number of processes already reached.")
    else:
        # Increment the expected number of processes
        # to spawn a new one in the createServer method
        number_of_active_processes += 1


def decrement_active_processes(signum, frame):
    """
        Decrements the number of active processes by 1 to decrease
        the number of child processes.

        :param signum: The first default value needed for a signal handler
        :param frame: The second default value needed for a signal handler
    """
    global number_of_active_processes
    global server_minimum_number

    # Make sure deleting a process wouldn't exceed the minimum limit
    if number_of_active_processes - 1 < server_minimum_number:
        print("[Server] Minimum number of processes already reached.")
    else:
        # Decrement the expected number of processes
        # to trigger a deletion in the createServer method
        number_of_active_processes -= 1


def terminate_replicants(signum, frame):
    """
        Goes through the server's replicants one by one and terminates them.

        :param signum: The first default value needed for a signal handler
        :param frame: The second default value needed for a signal handler
    """
    global server_processes

    # Loop through each grand child process
    for replicant in server_processes:

        # Terminate the replicant
        os.kill(replicant, signal.SIGKILL)

        # Wait for replicant to be destroyed to continue on
        # os.wait()

    # Now that all replicants are gone, terminate the parent server
    os.kill(os.getpid(), signal.SIGKILL)

    # Wait for parent to be destroyed to continue
    # os.wait()


def abort_server(server_pid):
    """
        Gracefully terminates the given server name and all of its children.

        :param server_pid: The pid of the server to be terminated gracefully
    """

    # Send the terminate symbol to the server so it may exit gracefully
    os.kill(server_pid, signal.SIGTERM)

    # Sleep to allow prompt to show in correct order
    time.sleep(.5)
    print("[Manager] Server successfully terminated.")


def create_process(server_pid):
    """
        Goes to the given server and creates a new process if the
        maximum number of process has not been reached.

        :param server_pid: The pid of the server to be grown
    """

    # Send user defined signal 1 to the server alerting it to make a process
    os.kill(server_pid, signal.SIGUSR1)

    # Sleep to allow the prompt to show in the correct order
    time.sleep(.5)


def abort_process(server_pid):
    """
        Goes to the given server and removes a process if the
        minimum number of process has not been reached.

        :param server_pid: The pid of the server to be shrunk
    """

    # Send user defined signal 2 to the server alerting it to abort a process
    os.kill(server_pid, signal.SIGUSR2)

    # Sleep to allow the prompt to show in the correct order
    time.sleep(.5)


def display_status(current_server_pids, main_manager_pid):
    """
        Runs the ps command and returns a tree of the current
        processes renamed with their given names

        :param current_server_pids: A dictionary holding the server names
                                    and their pids
        :param main_manager_pid: The pid of the manager
    """

    # Run the ps command to obtain the hierarchy and pids, and convert to str
    status = str(check_output("ps -o uname,pid,ppid,comm -C python3 --forest",
                              shell=True), 'utf-8').split('\n')

    # Loop through each of the lines returned by the ps
    for line in status:

        # Split out the words of the line for parsing
        words = line.split()

        # If COMMAND is found then this is the first line/header
        if "COMMAND" in line:
            # Replace the command word process as it's more descriptive
            print(line.replace("COMMAND", "PROCESS"))

        # If no words are found then try the next line
        elif not words:
            continue

        # If the returned pid is the manager's, relabel it as Manager
        elif int(words[1]) == main_manager_pid:
            print(line.replace("python3", "Manager"))
        else:

            # Loop through all of the saved servers
            for name in current_server_pids:

                # If the returned pid is the server's, relabel it as it's name
                if int(words[1]) == current_server_pids[name]:
                    print(line.replace("python3", "Server: " + name))

                # If the returned ppid is in our list,
                # then label it as a replicant.
                # Only ignoring the manager because
                # their parent is not important
                elif int(words[2]) == current_server_pids[name] \
                        and int(words[2]) != main_manager_pid:
                    print(line.replace("python3",
                                       "Replicant of Server: " + name))

# ---------------------------- Main Functionality -----------------------------
if __name__ == '__main__':
    '''
        The main method for the sever manager.
        It takes the input from the user and executes the given command
    '''
    global number_of_active_processes

    server_pids = {} # Dictionary Key: Name Value: pid

    # Get the current process's id
    manager_pid = os.getpid()
    manager_name = "Manager"

    # Save the manager into the dictionary
    server_pids[manager_name] = manager_pid
    print("[Manager] Manager Successfully started. PID: " + str(manager_pid))

    # Loop forever to simulate a server
    while True:
        command = input("\n[Manager] Please enter a command: ")

        # If the user entered the createServer command
        if "createServer" in command:

            # Parse all of the input into a list
            create_command_with_flags = command.split(" ")

            # Check for proper number of entries
            if len(create_command_with_flags) != 4:
                print("[Manager] Incorrect number of arguments.")
                continue

            # Convert and assign the user's entered values
            parsed_minimum_number_of_processes = int(
                create_command_with_flags[1])
            parsed_maximum_number_of_processes = int(
                create_command_with_flags[2])
            parsed_server_name = create_command_with_flags[3]

            # If no server name is entered alert the user
            if not parsed_server_name:
                print("[Manager] Invalid server name")
                continue

            # If a duplicate name is entered alert the user
            if parsed_server_name in server_pids:
                print("[Manager] Duplicate Server Name")
                continue

            # Make sure the number of processes is within the range 0 - 10
            if parsed_minimum_number_of_processes < 0 \
                    or parsed_maximum_number_of_processes > 10:
                print("Number of processes must be between 0 and 10")

            # Check if the given maximum is bigger than the minimum
            if parsed_maximum_number_of_processes >= \
                    parsed_minimum_number_of_processes:

                # Set the expected number of active processes to the minimum
                number_of_active_processes = parsed_minimum_number_of_processes

                # Run the create_server() function and save the parent's pid
                server_pids[parsed_server_name] = create_server(
                    parsed_minimum_number_of_processes,
                    parsed_maximum_number_of_processes,
                    parsed_server_name)
            else:
                print("[Manager] Minimum number must be smaller "
                      "than the maximum number")

        # If the user entered the abortServer command
        elif "abortServer" in command:
            # Parse all of the input into a list
            abort_command_with_flags = command.split(" ")

            # Check that the correct number of arguments was passed
            if len(abort_command_with_flags) != 2:
                print("[Manager] Incorrect number of arguments.")
                continue

            # Extract the given server name
            parsed_server_name = abort_command_with_flags[1]

            # Check if the name exists in the list of servers
            if parsed_server_name in server_pids:

                # Run the abort_server() function to delete the server
                abort_server(server_pids[parsed_server_name])

                # Remove the server from the list of servers
                del server_pids[parsed_server_name]
            else:
                print("Server does not exist.")
                continue

        # If the user entered the createProcess command
        elif "createProcess" in command:

            # Parse all of the input into a list
            create_process_command_with_flags = command.split(" ")

            # Check that the correct number of arguments was passed
            if len(create_process_command_with_flags) != 2:
                print("[Manager] Incorrect number of arguments.")
                continue

            # Extract the given server name
            parsed_server_name = create_process_command_with_flags[1]

            # Check if the name exists in the list of servers
            if parsed_server_name in server_pids:

                # Run the create_process() function to create the process
                create_process(server_pids[parsed_server_name])
            else:
                print("Server does not exist.")
                continue

        # If the user entered the abortProcess command
        elif "abortProcess" in command:

            # Parse all of the input into a list
            abort_process_command_with_flags = command.split(" ")

            # Check that the correct number of arguments was passed
            if len(abort_process_command_with_flags) != 2:
                print("[Manager] Incorrect number of arguments.")
                continue

            # Extract the given server name
            parsed_server_name = abort_process_command_with_flags[1]

            # Check if the name exists in the list of servers
            if parsed_server_name in server_pids:

                # Run the abort_process() function to abort a process
                abort_process(server_pids[parsed_server_name])
            else:
                print("Server does not exist.")
                continue

        # If the user entered the abortProcess command
        elif "displayStatus" in command:

            # Run the display_status() function to show the hierarchy
            display_status(server_pids, manager_pid)
        else:
            print("Unrecognized Command")
