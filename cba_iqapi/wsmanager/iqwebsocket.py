import json
import time
import logging
import websocket
import threading

logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    Manages WebSocket connections for real-time communication with IQ Option.
    
    This class handles the WebSocket lifecycle including connection establishment,
    message sending/receiving, error handling, and connection cleanup. It uses
    a separate thread for the WebSocket connection to avoid blocking the main thread.
    """
    def __init__(self, message_handler):
        """
        Initialize the WebSocket manager with message handler.
        
        Args:
            message_handler: Handler instance that processes incoming messages
        """
        self.websocket = None
        self.ws_is_active = False
        self.message_handler = message_handler
        self.send_message_count = 0
        
    def start_websocket(self):
        """
        Initialize and start the WebSocket connection in a separate daemon thread.
        
        Creates a WebSocketApp instance with event handlers and starts it in a
        daemon thread to prevent blocking. Waits for connection to be established
        before returning.
        """

        # Create WebSocket application with event handlers
        self.websocket = websocket.WebSocketApp(
            'wss://ws.iqoption.com/echo/websocket',
            on_message=self._on_message,  # Handle incoming messages
            on_open=self._on_open,        # Handle connection opened
            on_close=self._on_close,      # Handle connection closed
            on_error=self._on_error       # Handle connection errors
        )
        
        # Start WebSocket in a daemon thread (dies when main thread exits)
        wst = threading.Thread(target=self.websocket.run_forever)
        wst.daemon = True
        wst.start()
        
        # Wait for connection to be established before proceeding
        timeout = 10
        start = time.time()

        while not self.ws_is_active:
            if time.time() - start > timeout:
                raise TimeoutError("WebSocket connection timeout")

            time.sleep(0.1)
    
    def send_message(self, name, msg, request_id=None):
        """
        Send a message through the WebSocket connection.
        
        Constructs a JSON message with name, msg, and request_id fields.
        If no request_id is provided, generates one using current timestamp.
        
        Args:
            name (str): Message type/name identifier
            msg (dict): Message payload data
            request_id (str, optional): Unique request identifier. 
                                      Auto-generated if not provided.
        
        Returns:
            str: The request_id used for this message (useful for tracking responses)
        """

        # Generate request ID from timestamp microseconds if not provided
        if request_id is None:
            request_id = str(time.time()).split('.')[1]

        self.send_message_count += 1

        # Construct message data structure
        data = json.dumps(dict(name=name, msg=msg, request_id=request_id))
        
        self.websocket.send(data)
        return request_id
    
    def _on_message(self, ws, message, *args):
        """
        Handle incoming WebSocket messages.
        """
        try:
            # print(message)
            message = json.loads(message)
            self.message_handler.handle_message(message)
            self.ws_is_active = True
        except json.JSONDecodeError as e:
            print(f"Error parsing message: {e}")


    def _on_error(self, ws, error, *args):
        """
        Handle WebSocket connection errors.
        """
        print(f"### WebSocket Error: {error} ###")


    def _on_open(self, ws, *args):
        """
        Handle WebSocket connection opened event.
        """
        # print("### WebSocket opened ###")
        self.ws_is_active = True


    def _on_close(self, ws, close_status_code=None, close_msg=None, *args):
        """
        Handle WebSocket connection closed event.
        """
        # print("### WebSocket closed ###")
        self.ws_is_active = False
    
    def close(self):
        """
        Gracefully close the WebSocket connection.
        
        Closes the WebSocket connection if it exists and resets the connection status.
        Should be called when shutting down the application or switching connections.
        """
        if self.websocket:
            self.websocket.close()