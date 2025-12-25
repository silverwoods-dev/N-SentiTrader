
import socket
import logging

logger = logging.getLogger(__name__)

def restart_container(container_name: str):
    """
    Restarts a container using the Docker Engine API via Unix Socket.
    Target: POST /containers/{name}/restart
    """
    sock_path = "/var/run/docker.sock"
    
    request = (
        f"POST /containers/{container_name}/restart?t=5 HTTP/1.1\r\n"
        "Host: localhost\r\n"
        "Connection: close\r\n"
        "\r\n"
    )
    
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(sock_path)
            client.sendall(request.encode())
            
            response = b""
            while True:
                data = client.recv(4096)
                if not data:
                    break
                response += data
                
            response_str = response.decode()
            
            # Simple status check
            if "HTTP/1.1 204" in response_str:
                logger.info(f"Successfully restarted container: {container_name}")
                return True
            else:
                logger.error(f"Failed to restart {container_name}. Response: {response_str.splitlines()[0]}")
                return False
                
    except FileNotFoundError:
        logger.error(f"Docker socket not found at {sock_path}. Cannot restart container.")
        return False
    except Exception as e:
        logger.error(f"Error communicating with Docker socket: {e}")
        return False

def restart_all_workers():
    """
    Restarts all known worker containers to clear zombie states.
    """
    workers = [
        "n_senti_address_worker_1", 
        "n_senti_address_worker_2",
        "n_senti_daily_address_worker",
        "n-sentitrader-verification_worker-1",
        "n-sentitrader-body_worker-1",
        "n-sentitrader-body_worker-2"
    ]
    
    # Add body workers
    # workers.extend(["n_senti_body_worker_1", "n_senti_body_worker_2"])
    
    results = {}
    for w in workers:
        results[w] = restart_container(w)
        
    return results

def get_container_logs(container_name: str, tail: int = 100):
    """
    Fetches stdout/stderr logs from a container via Docker Engine API Unix Socket.
    Target: GET /containers/{name}/logs?stdout=1&stderr=1&tail={tail}
    """
    sock_path = "/var/run/docker.sock"
    
    # Docker API uses multiplexing for logs if tty is false (default).
    # But for simplicity, we'll try to get it as plain text if possible, 
    # or handle the header. Actually, ?stdout=1&stderr=1&timestamps=0
    request = (
        f"GET /containers/{container_name}/logs?stdout=1&stderr=1&tail={tail}&timestamps=0&follow=0 HTTP/1.1\r\n"
        "Host: localhost\r\n"
        "Connection: close\r\n"
        "\r\n"
    )
    
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(sock_path)
            client.sendall(request.encode())
            
            response = b""
            while True:
                data = client.recv(4096)
                if not data:
                    break
                response += data
            
            # Docker logs contain an 8-byte header for each chunk: [stream_type, 0, 0, 0, size1, size2, size3, size4]
            # We want to strip the HTTP header first, then parse characters.
            
            # Split HTTP Header
            header_end = response.find(b"\r\n\r\n")
            if header_end == -1:
                return "Error: Invalid response from Docker socket"
            
            body = response[header_end + 4:]
            
            # Parse Multiplexed Body
            # https://docs.docker.com/engine/api/v1.43/#tag/Container/operation/ContainerLogs
            # [1, 0, 0, 0, size_high, size_low]
            
            output = ""
            i = 0
            while i < len(body):
                if i + 8 > len(body):
                    break
                # stream_type = body[i] # 1: stdout, 2: stderr
                size = int.from_bytes(body[i+4:i+8], byteorder="big")
                chunk = body[i+8 : i+8+size].decode(errors="replace")
                output += chunk
                i += 8 + size
                
            return output if output else "No logs found or empty output."
                
    except FileNotFoundError:
        return f"Error: Docker socket not found at {sock_path}"
    except Exception as e:
        return f"Error communicating with Docker socket: {e}"
