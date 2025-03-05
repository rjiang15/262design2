# src/network.py

import socket
import threading
import json
import time

BASE_PORT = 5000

def start_server(vm, host="127.0.0.1"):
    """
    Start a server socket for the given VM.
    The VM's server socket listens on BASE_PORT + vm.vm_id.
    """
    port = BASE_PORT + vm.vm_id
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Allow the socket to reuse the address immediately.
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    vm.log_event(f"Network: Listening on {host}:{port}")
    
    def handle_client(client_socket):
        """
        Continuously receive messages from a connected client.
        Each message is expected to be a JSON-encoded string terminated by newline.
        """
        with client_socket:
            buffer = ""
            while True:
                try:
                    data = client_socket.recv(1024).decode("utf-8")
                    if not data:
                        break  # Connection closed
                    buffer += data
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        try:
                            message = json.loads(line)
                            vm.receive_message(message)
                        except json.JSONDecodeError:
                            vm.log_event("Network: Failed to decode message.")
                except ConnectionResetError:
                    break
                except Exception as e:
                    vm.log_event(f"Network: Exception in handle_client: {e}")
                    break

    def accept_connections():
        # Loop indefinitely; when server_socket is closed, accept() will raise an error.
        while True:
            try:
                server_socket.settimeout(1.0)
                client_socket, addr = server_socket.accept()
                vm.log_event(f"Network: Accepted connection from {addr}")
                t = threading.Thread(target=handle_client, args=(client_socket,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception as e:
                vm.log_event(f"Network: Exception in accept_connections: {e}")
                break
        try:
            server_socket.close()
        except Exception:
            pass
        vm.log_event("Network: Server socket closed.")
    
    t = threading.Thread(target=accept_connections, daemon=True)
    t.start()
    vm.server_socket = server_socket
    # Removed reference to vm.network_thread since it's no longer needed.

def connect_to_peer(vm, peer_vm_id, host="127.0.0.1", base_port=5000, max_retries=5, retry_delay=1):
    """
    Connect to a peer's server socket.
    Returns the connected client socket.
    Uses base_port (default 5000) plus the peer_vm_id to determine the port.
    Retries up to max_retries times.
    """
    port = int(base_port) + int(peer_vm_id)
    attempt = 0
    while attempt < max_retries:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((host, port))
            vm.log_event(f"Network: Connected to peer VM {peer_vm_id} at {host}:{port}")
            return client_socket
        except ConnectionRefusedError:
            attempt += 1
            client_socket.close()
            time.sleep(retry_delay)
            continue
        except Exception as e:
            vm.log_event(f"Network: Exception when connecting to peer VM {peer_vm_id}: {e}")
            client_socket.close()
            break
    return None
