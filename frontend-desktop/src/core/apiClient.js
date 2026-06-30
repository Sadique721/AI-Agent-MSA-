/**
 * apiClient.js
 * WebSocket wrapper connecting to the V4.0 Enterprise API Gateway.
 */
export class GatewayWebSocketClient {
  constructor(url = "ws://localhost:8080/stream") {
    this.url = url;
    this.ws = null;
    this.onMessageCallbacks = [];
    this.onConnectCallbacks = [];
    this.onDisconnectCallbacks = [];
  }

  connect() {
    try {
      this.ws = new WebSocket(this.url);
      
      this.ws.onopen = () => {
        console.log("WebSocket connected to Gateway.");
        this.onConnectCallbacks.forEach(cb => cb());
      };
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.onMessageCallbacks.forEach(cb => cb(data));
        } catch (e) {
          console.warn("Received non-JSON message: ", event.data);
        }
      };
      
      this.ws.onclose = () => {
        console.log("WebSocket disconnected.");
        this.onDisconnectCallbacks.forEach(cb => cb());
        // Auto-reconnect after 3 seconds
        setTimeout(() => this.connect(), 3000);
      };
    } catch (err) {
      console.error("WebSocket connection failure:", err);
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn("WebSocket not open. Queueing or dropping message.");
    }
  }

  onMessage(callback) {
    this.onMessageCallbacks.push(callback);
  }

  onConnect(callback) {
    this.onConnectCallbacks.push(callback);
  }

  onDisconnect(callback) {
    this.onDisconnectCallbacks.push(callback);
  }
}
