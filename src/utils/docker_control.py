
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
        "n_senti_verification_worker",
        "n_senti_address_worker_1", 
        "n_senti_address_worker_2",
        "n_senti_daily_address_worker",
        "n_senti_body_worker" # Note: body_worker might be body_worker_1, body_worker_2 due to replicas?
        # With replicas, names are usually project_service_index.
        # But we can query list? No, explicit names are safer if defined.
        # In docker-compose, body_worker has replicas: 2.
        # Compose names them: n_senti_body_worker_1, n_senti_body_worker_2.
        # I'll restart what I know.
    ]
    
    # Add body workers
    workers.extend(["n_senti_body_worker_1", "n_senti_body_worker_2"])
    
    results = {}
    for w in workers:
        results[w] = restart_container(w)
        
    return results
