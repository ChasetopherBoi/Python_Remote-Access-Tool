# Remote PC Access Tool - Python
A simple Python tool used to allow your device to communicate and execute commands on another device. With Port Forwarding, it can be configured to work on different WIFI networks. I created this tool to learn more about sockets, sending/receiving commands accross devices, and gain a better understanding of how malware works and signs to detect when your device has become infected. This is one of my first Python projects, there may be many bugs, and some of the code may not be fully explained. Feel free to suggest any changes or features you would like to see added in the future.

# Table of Contents #

1. [Introduction](#introduction)
2. [Installation](#installation)
    - [Requirements](#1-requirements)
    - [Configure IP & Port](#2-configure-ip--port)
    - [Packaging](#3-packaging-client)
    - [Client Selection](#4-client-selection)
3. [Features](#features)
4. [Usage](#usage)
    - [Commands](#commands)
    - [CMD Mode](#cmd-mode-command-prompt-mode)
6. [Disclaimer](#disclaimer)


# **Introduction**
> ## ⚠️ **Warning** ## 
>
>This project is solely for educational and experimental purposes. I am not responsible nor do I condone any unethic or illegal activies this project may be used for.<br>
> <br>
> By using this software, you agree that you are solely responsible for ensuring that it is used in accordance with all applicable laws and regulations.
> <br>
> <br>
>#### * Please use with caution, preferably in a virutal environment. *
<br>

# **Project Demonstration**

[![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/EHQS0jTjSPw/0.jpg)](https://www.youtube.com/watch?v=EHQS0jTjSPw)

### Additional Information:
I created this remote management software to demostrate and educate users on the possibilities of remote access/remote desktop tools, while also learning more about network connections and Python sockets.

The Server accepts up to 5 clients, and is setup to allow you to easily swap between them whenever necessary.

>
>#### **HOST** : 
> Device where you will be hosting the connection and executing commands. (example: Your computer)
>#### **CLIENT** : 
> Virtual box or other computer you are authorized to be installing the script on, will be handling commands and receiving responses. 
><br><br>


# **Installation**
There are a few necessary steps needed prior to attempting to execute any of the scripts. After cloning the repository on your device, please follow the steps listed below.<br>

### 1. Requirements
Execute the following commands to install necessary Python libraries to use this project.<br>

        pip install psutil
        pip install pyautogui
        pip install getmac
        pip install validators
        pip install pillow
        pip install zlib
        pip install PyInstaller

        *** Optional ***
        pip install PyArmor
### 2. Configure IP & Port
Inside each of the files, locate the following lines of code and replace the **HOST** and **PORT** with your desired IP Address and Port number. 

Client.py

        HOST = "0.0.0.0"
        PORT = "3389"
StartServer.py

        HOST = "0.0.0.0"
        PORT = "3389"
Replace **'0.0.0.0'** with the IP address of the **HOST** machine.<br>
<br>
Replace **'3389'** with the port on the server you would like to use, or leave to the default.
<br>
<br>
**Port Forwarding** : Can be configured on your router or using a VPN to allow connections from clients on different WIFI networks.

### 3. Packaging Client
The client file can be packaged as an **.EXE** file by using a tool such as **PyInstaller**. Ensure you use the correct options so the executable can run without errors.<br>

Prior to packaging utilize PyArmor to obfuscate the **CLIENT** script to help prevent it from being flagged and removed.

### PyArmor
#### Obfuscate the **CLIENT** script. Helps prevent reverse engineering.
    PyArmor gen --entry Client.py --output <output_name>

### PyInstaller
#### Package the **CLIENT** script as an (.EXE) executable for deployment.
    PyInstaller --noconsole --onefile --hidden-import=psutil --hidden-import=shutil --hidden-import=webbrowers --hidden-import=pyautogui --hidden-import=getmac --hidden-import=base64 Client.py 
#### Ensure 'Client.py' is replaced with the name of the obfuscated client file.
<br>
See **PyInstaller** documentation for additional information.
<br>

### 4. Client Selection
After packaging **Client.py** as an executable, you can then import it to your virtual machine environment and execute.

Once both **StartServer.py** and **Client.py** are running the list of clients will be displayed in the command prompt window.<br> 

You can choose the IP address of the client you would like to interact with by inputting a number and pressing **ENTER**.<br>

    **************************************************
    [WAITING] (Connected client's IP addresses will be displayed here)
    **************************************************

    Select a client to use for this session or 'exit' to shutdown the server.

    Selection: 2



# **Usage**
### The 2 main scripts used in this project are:
* [StartServer.py](#startserverpy)
* [Client.py](#clientpy)

### **StartServer.py**
This is the main script used by the **HOST** to send commands to all clients connected. The file currently accepts up to 5 simultaneous connections.<br>

The server can send a variable of built-in commands as well as basic Windows Command Prompt commands to the CLIENT. Input a command (include arguments if required) and press **ENTER** to send commands from your machine to the **CLIENT**.

Exiting the program is very simple, and can be done by typing 'exit', which will close the server and handle **CLIENT** connection closing, then running in the background.

>### Note :
>Please use caution when closing the server, and make sure to always type **'exit'** to properly shutdown the server.<br>

### **Client.py**
This python script is responsible for interpreting commands sent from the **HOST** and sending back the appropriate response.<br>

The script is setup to continuously run in the background, even after closing the server. The code will attempt to connect after a short today, and continue to loop.<br>
This ensures the **HOST** can always connect back to the **CLIENT** even after they shutdown the server.

Some commands will respond with simple text and be executed, while others may respond back with the output data from the **CLIENT**.

## Commands
The template remote management tool has several built-in commands, as well as the functionality to run Windows Command Prompt commands.

* **CHECK_ADMIN** - Checks if the program was executed on the client machine with administrative permissions.

*  **CLIENT** - Disconnects from the current client, and returns the user to the initial screen displaying all connected clients.

* **CLS** - Clears the terminal screen completely.

* **CMD** - Toggles 'Command Prompt Mode' : When enabled allows the **HOST** to execute Command Prompt commands on the client machine, and receive the output. See **CMD Mode** section for additional information.

* **HELP** - Lists all available commands.

* **KILL_PROC <pid>** - Takes 1 argument (PID). Terminates a process running on the client machine. Useful to stop any unwanted/harmful apps on the client machine. (PID can be found using **'LIST_PROC'**)

* **LIST_PORTS <-E, -L>** - Takes 1 optional argument (-e | -l). Lists all ports on the client machine when no argument given. Filters by either 'Established' or 'Listening' states when given an argument.

* **LIST_PROC** - Lists all processes running on the client machine. Can be used to determine if the client is running any unwanted/harmful programs.

* **NETINFO** - Displays client IP and MAC address. Useful for determining if connections are working properly.

* **OPEN_URL <URL_ADDRESS>** - Takes 1 argument (https://www.example.com). Opens a URL on the client machine using the default browser.

* **RUN <FILE_PATH>** - Takes 1 argument <path/to/file.txt>. Executes a file or app on the client machine. If no direct file is provided, it will open File Explorer.

* **SCREENSHOT** - Captures a screenshot of the client desktop. Can be useful to periodically monitor and log activity.

* **STARTUP** - Adds the program to the startup list on Windows to automatically execute when booting up the device. Once manually disabled, the command will not enable it again.

* **SYS_INFO** - Lists system information of the client machine. A helpful command to determine what the device that you're connected to is, and if the specs are outdated.

* **UPLD <SOURCE_FILE> <DESTINATION_FILEPATH>** - Takes 2 arguments <path/to/file/on/server> and <path/to/download/on/client>. Allows the **HOST** to upload a file from their machine to the client machine. Can be text files or any other small files you may need to transfer.

## CMD Mode (Command Prompt)
Once the **HOST** enables CMD Mode they can execute any Command Prompt command and receive the response from the client machine. You can run any command that can be executed in Windows Command Prompt, such as 'ipconfig', 'dir', 'echo'. And the appropriate response will be printed on the server terminal.

Commands that don't provide a response such as 'echo' will print a *Successful* or *Error* response. 

### Change Directory  (cd)
When executing the 'cd' command to change the **CMD Mode** directory, you must use the command as shown for it to work properly.

#### Append a new directory to the current directory :
        'cd target\directory' # replace 'target\directory' with the new filepath in the current directory.
<br>
Adds the listed file path to the current directory, if available.
<br>

        [CMD Mode]  Type a Windows CMD command, or 'cmd' to exit.
        C:\>cd \Users\Public

        C:\Users\Public>'next command here'

#### Change the directory to a new drive (check for multiple harddrives)

        'cd C:\' # Replace 'C' with new drive letter.
### Entering 'C:' or 'D:' by itself will not change the directory.

<br>

# Disclaimer

#### By using any code in this project, you agree that you are solely responsible for ensuring that this software is used for educational purposes only and in accordance with all applicable laws and regulations.

#### This project is solely for educational and experimental purposes. I do not endorse or condone any illegal activities that may arise from the misuse of this software. I am not responsible for any damages, legal consequences, or any other liabilities resulting from the improper or unauthorized use of this software.

#### I am not affiliated with Flipper Devices in any way.

### * Use this software only in environments where you have explicit permission to do so, such as a Virtual Environment *

***
