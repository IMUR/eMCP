import json
import glob
import subprocess
import os

CONFIG_DIR = "configs"
DOCKER_CMD = "docker exec emcp-server /mcpjungle"

def run_command(cmd):
    try:
        subprocess.run(cmd, shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {cmd}")
        return False

def get_server_names():
    servers = []
    for filepath in glob.glob(os.path.join(CONFIG_DIR, "*.json")):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                if 'name' in data:
                    servers.append((data['name'], filepath))
        except Exception as e:
            print(f"Failed to read {filepath}: {e}")
    return servers

def main():
    print("Starting re-registration of all tools...")
    servers = get_server_names()

    if not servers:
        print("No server configurations found.")
        return

    # Deregister All
    print(f"\nDeregistering {len(servers)} servers...")
    for name, _ in servers:
        print(f"  - Deregistering {name}...")
        # Ignore errors if server doesn't exist
        subprocess.run(f"{DOCKER_CMD} deregister {name}", shell=True)

    # Register All
    print(f"\nRegistering {len(servers)} servers...")
    for name, filepath in servers:
        # /mcpjungle expects path inside container, which is mounted at /configs
        container_path = f"/configs/{os.path.basename(filepath)}"
        print(f"  - Registering {name} from {container_path}...")
        if run_command(f"{DOCKER_CMD} register -c {container_path}"):
             print(f"    Successfully registered {name}.")
        else:
             print(f"    Failed to register {name}.")

    print("\nRe-registration complete.")
    # Verification step
    print("\nVerifying registered servers:")
    subprocess.run(f"{DOCKER_CMD} list servers", shell=True)

if __name__ == "__main__":
    main()
