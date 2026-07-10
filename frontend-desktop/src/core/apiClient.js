/**
 * apiClient.js
 * Real Socket.IO client connecting to MSA Flask-SocketIO backend on port 5000.
 * Replaces the broken raw-WebSocket gateway client that targeted port 8080.
 */
import { io } from 'socket.io-client';

const BACKEND_URL = 'http://localhost:5000';

export class MSASocketClient {
  constructor() {
    this.socket = null;
    this.onMessageCallbacks = [];
    this.onConnectCallbacks = [];
    this.onDisconnectCallbacks = [];
    this.onTokenCallbacks = [];
    this.onStatusCallbacks = [];
    this.onChunkCallbacks = [];
    this._isConnected = false;
  }

  connect() {
    if (this.socket) return;

    this.socket = io(BACKEND_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
      timeout: 10000,
    });

    this.socket.on('connect', () => {
      this._isConnected = true;
      console.log('[MSA] Socket.IO connected to backend on port 5000');
      this.onConnectCallbacks.forEach(cb => cb());
    });

    this.socket.on('disconnect', (reason) => {
      this._isConnected = false;
      console.log('[MSA] Disconnected:', reason);
      this.onDisconnectCallbacks.forEach(cb => cb(reason));
    });

    // Token-by-token streaming (real-time response)
    this.socket.on('token', (data) => {
      this.onTokenCallbacks.forEach(cb => cb(data));
    });

    // Status updates (thinking, searching, etc.)
    this.socket.on('status', (data) => {
      this.onStatusCallbacks.forEach(cb => cb(data));
    });

    // Complete response event
    this.socket.on('response', (data) => {
      this.onMessageCallbacks.forEach(cb => cb(data));
    });

    // Agent thinking / tool use notifications
    this.socket.on('agent_event', (data) => {
      this.onMessageCallbacks.forEach(cb => cb({ agent_event: true, ...data }));
    });

    this.socket.on('connect_error', (err) => {
      console.error('[MSA] Connection error:', err.message);
    });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this._isConnected = false;
    }
  }

  sendCommand(text) {
    if (!this.socket || !this._isConnected) {
      console.error('[MSA] Cannot send — not connected to backend');
      return;
    }
    // Use the real event name from backend/server.py handle_text_command
    this.socket.emit('text_command', { command: text });
  }

  onConnect(cb)     { this.onConnectCallbacks.push(cb); }
  onDisconnect(cb)  { this.onDisconnectCallbacks.push(cb); }
  onMessage(cb)     { this.onMessageCallbacks.push(cb); }
  onToken(cb)       { this.onTokenCallbacks.push(cb); }
  onStatus(cb)      { this.onStatusCallbacks.push(cb); }

  get connected()   { return this._isConnected; }
}

// Singleton
let _client = null;
export function getMSAClient() {
  if (!_client) _client = new MSASocketClient();
  return _client;
}
