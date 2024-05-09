from fastapi import FastAPI, HTTPException, File, UploadFile, BackgroundTasks
import os
import subprocess
import shutil
import psutil
from utils import upload_model, generate_cards
app = FastAPI()

# Dictionary to store running processes and their PIDs
running_processes = {}

# Folder to save uploaded YAML files
UPLOAD_FOLDER = "YAML_FILES"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.post("/start/")
def start_process(command_params: dict):
    """
    Start a new process with provided command parameters.
    """
    global running_processes

    # Extract parameters from request
    copy_tokenizer = command_params.get("--copy-tokenizer", False)
    allow_crimes = command_params.get("--allow-crimes", False)
    out_shard_size = command_params.get("--out-shard-size", None)
    lazy_unpickle = command_params.get("--lazy-unpickle", False)
    yaml_file_path = command_params.get("yaml_file_path", None)
    merged_folder = command_params.get("merged_folder", None)

    # Check if YAML file path is provided
    if not yaml_file_path:
        raise HTTPException(status_code=400, detail="YAML file path not provided")

    # Check if YAML file exists
    if not os.path.exists(yaml_file_path):
        raise HTTPException(status_code=404, detail="YAML file not found")

    if not os.path.exists(merged_folder):
        os.makedirs(merged_folder, exist_ok=True)
    # Construct the command
    command = [
        "!mergekit-yaml",
        yaml_file_path,
        merged_folder,
        "--copy-tokenizer" if copy_tokenizer else "",
        "--allow-crimes" if allow_crimes else "",
        f"--out-shard-size {out_shard_size}" if out_shard_size else "",
        "--lazy-unpickle" if lazy_unpickle else "",
    ]

    # Execute the command and capture stdout and stderr
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    # Get the PID of the subprocess
    pid = process.pid

    # Store the process and its PID
    running_processes[pid] = {
        "command": " ".join(command),
        "process": process,
        "merged_folder": merged_folder,
        "yaml_file_path": yaml_file_path,
        "output": "",
        "status": "running",
    }

    return {"message": "Process started successfully", "pid": pid}


@app.get("/stop/{pid}/")
def stop(pid: int):
    """
    Stop a running process by PID.
    """
    global running_processes

    if pid not in running_processes:
        raise HTTPException(status_code=404, detail="Process not found")

    # Terminate the process
    running_processes[pid]["process"].terminate()
    del running_processes[pid]

    return {"message": "Process stopped successfully", "pid": pid}


@app.get("/get_pids/")
def get_pids():
    """
    Get all running process PIDs.
    """
    global running_processes

    return {"pids": running_processes.keys()}


@app.get("/check_progress/{pid}/")
def check_progress(pid: int):
    """
    Check the progress of a running process by PID.
    """
    global running_processes

    if pid not in running_processes:
        raise HTTPException(status_code=404, detail="Process not found")

    # Check if the process has terminated
    if running_processes[pid]["process"].poll() is not None:
        running_processes[pid]["status"] = "finished"

    # Get the output of the process
    stdout, stderr = running_processes[pid]["process"].communicate()
    running_processes[pid]["output"] += stdout.decode() + stderr.decode()

    return {
        "pid": pid,
        "status": running_processes[pid]["status"],
        "output": running_processes[pid]["output"],
        "merged_folder": running_processes[pid]["merged_folder"],
        "yaml_file_path": running_processes[pid]["yaml_file_path"],
    }


@app.post("/upload_yaml/")
async def upload_yaml(file: UploadFile = File(...)):
    """
    Upload a YAML file and save it to a specific folder.
    """
    # Create the upload folder if it doesn't exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    # Save the file to the upload folder
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"filename": file.filename, "path": file_path}

@app.post("/upload_model/")
async def upload_model_endpoint(background_tasks: BackgroundTasks, merge_dir: str = None, yaml_config: str = None):
    """
    Upload a model to Hugging Face Hub.
    """
    # Create the upload folder if it doesn't exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    # Save the YAML config file to the upload folder
    yaml_config_path = os.path.join(UPLOAD_FOLDER, yaml_config)
    with open(yaml_config_path, "wb") as buffer:
        shutil.copyfileobj(yaml_config.file, buffer)
    generate_cards(merge_dir, yaml_config_path)
    # Run the upload_model function in the background
    background_tasks.add_task(upload_model, merge_dir, yaml_config_path)

    return {"message": "Model upload started successfully"}

@app.get("/list_yaml_files/")
def list_yaml_files():
    """
    Get a list of YAML files in the upload folder.
    """
    yaml_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(".yaml")]
    return {"yaml_files": yaml_files}


@app.delete("/delete_yaml_file/")
def delete_yaml_file(filename: str):
    """
    Delete a YAML file from the upload folder.
    """
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"message": f"YAML file '{filename}' deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="File not found")

@app.get("/ram_usage/")
def get_ram_usage():
    """
    Get current RAM usage statistics.
    """
    ram_usage = psutil.virtual_memory()
    return {
        "total": ram_usage.total/1024/1024,
        "available": ram_usage.available/1024/1024,
        "percent": ram_usage.percent,
    }


@app.get("/hdd_usage/{path}")
def get_hdd_usage(path: str):
    """
    Get current HDD/SSD usage statistics.
    """
    hdd_usage = psutil.disk_usage(path)
    return {
        "total": hdd_usage.total/1024/1024/1024,
        "used": hdd_usage.used/1024/1024/1024,
        "free": hdd_usage.free/1024/1024/1024,
        "percent": hdd_usage.percent,
    }
    