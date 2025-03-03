# src/network.py

import socket
import threading
import json

def start_server(vm, host="127.0.0.1", base_port=5000):
    """
    Starts a server socket for a given virtual machine.
    The VM listens on (host, base_port + vm.vm_id).
    """
    port = base_port + vm.vm_id
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    vm.log_event(f"Network: Listening on {host}:{port}")
    
    def handle_client(client_socket):
        buffer = ""
        while True:
            try:
                data = client_socket.recv(1024).decode("utf-8")
                if not data:
                    break  # connection closed
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    try:
                        message = json.loads(line)
                        vm.receive_message(message)
                    except Exception as e:
                        vm.log_event(f"Error decoding message: {e}")
            except Exception as e:
                vm.log_event(f"Error in client handler: {e}")
                break
        client_socket.close()
    
    def accept_connections():
        while not vm.network_stop_event.is_set():
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
        server_socket.close()
        vm.log_event("Network: Server socket closed.")
    
    t = threading.Thread(target=accept_connections, daemon=True)
    t.start()
    vm.server_socket = server_socket
    vm.network_thread = t

def connect_to_peer(vm, peer_vm_id, host="127.0.0.1", base_port=5000):
    """
    Connects to a peer VM's server socket.
    The peer is assumed to be listening on (host, base_port + peer_vm_id).
    """
    port = base_port + peer_vm_id
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while not vm.network_stop_event.is_set():
        try:
            client_socket.connect((host, port))
            vm.log_event(f"Network: Connected to peer VM {peer_vm_id} at {host}:{port}")
            return client_socket
        except ConnectionRefusedError:
            continue
        except Exception as e:
            vm.log_event(f"Network: Exception when connecting to peer VM {peer_vm_id}: {e}")
            break
    return None
